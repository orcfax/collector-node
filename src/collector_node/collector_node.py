"""Run Chronicle Labs collector code and forward to validator.

Example crontab to collect data every minute:

    ```sh
        crontab: */1 * * * * /home/orcfax/collector/venv/bin/python /home/orcfax/collector/collector.py 2>&1 | logger -t orcfax_collector
    ```

To monitor logging:

    ```sh
        sudo tail -f /var/log/syslog | grep orcfax_collector
    ```

"""

import asyncio
import json
import logging
import os
import random
import sqlite3
import ssl
import subprocess
import sys
import time
from typing import Final

import certifi
import websocket
import websockets
from simple_sign.sign import sign_with_key

CNT_ENABLED: Final[bool] = True


# Import config.
try:
    import config
    import flock
    from version import get_version
except ModuleNotFoundError:
    try:
        from collector_node import config, flock
        from collector_node.version import get_version
    except ModuleNotFoundError:
        from src.collector_node import config, flock
        from src.collector_node.version import get_version

try:
    # Import CNT related config.
    from cnt_collector_node.helper_functions import check_tokens_pair
    from cnt_collector_node.pairs import DEX_PAIRS
except ModuleNotFoundError:
    CNT_ENABLED = False

sys.dont_write_bytecode = True

logger = logging.getLogger(__name__)

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s :: %(filename)s:%(lineno)s:%(funcName)s() :: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level="INFO",
)

# Default to UTC time.
logging.Formatter.converter = time.gmtime

# pylint: disable=E1121


async def read_identity() -> dict:
    """Read the node identity file.

    Return a simplified version of the identity file and the location
    of the validator websocket.
    """
    identity = None
    try:
        with open(config.NODE_IDENTITY_LOC, "r", encoding="utf-8") as identity_json:
            identity = json.loads(identity_json.read())
    except FileNotFoundError as err:
        raise FileNotFoundError(f"Node identity not found: {err}") from err
    except json.decoder.JSONDecodeError as err:
        raise RuntimeWarning(
            f"Problem parsing JSON consider re-running node-init: {err}"
        ) from err
    return identity


async def retrieve_cnt(requested: list, identity: dict) -> list:
    """Retrieve CNT pairs"""

    logger.info("connecting to the database")
    conn = sqlite3.connect(config.CNT_DB_NAME)
    cur = conn.cursor()
    database_context = {
        "conn": conn,
        "cur": cur,
    }

    res = []
    logger.info("connecting to ogmios")
    ogmios_ver = config.OGMIOS_VERSION
    ogmios_ws: websocket.WebSocket = websocket.create_connection(config.OGMIOS_URL)
    ogmios_context = {
        "ogmios_ws": ogmios_ws,
        "ogmios_ver": ogmios_ver,
        "logger": logger,
    }
    for tokens_pair in requested:
        message, timestamp = await check_tokens_pair(
            database_context,
            ogmios_context,
            identity,
            tokens_pair,
        )
        message = {
            "message": message,
            "node_id": identity["node_id"],
            "validation_timestamp": timestamp,
        }
        if not message:
            logger.error("no message returned for: '%s'", tokens_pair["name"])
            continue
        res.append(message)

    return res


async def fetch_dex_feeds(feeds: list, identity: dict) -> list:
    """Retrieve dex data from the CNT indexer."""
    pairs = []
    for dex_pair in DEX_PAIRS:
        if dex_pair["name"] not in feeds:
            continue
        pairs.append(dex_pair)
    logger.info(
        "retrieving: '%s' pairs, from '%s' original pairs", len(pairs), len(DEX_PAIRS)
    )
    return await retrieve_cnt(pairs, identity)


async def fetch_cex_data(feed: str) -> dict:
    """Fetch data from the collector app using the subprocess command."""
    try:
        ps_out = subprocess.run(
            [
                config.GOFER,
                "data",
                feed,
                "-o",
                "orcfax",
            ],
            capture_output=True,
            check=True,
        )
        stdout = json.loads(ps_out.stdout.decode())
        stderr = ps_out.stderr.decode()
    except subprocess.CalledProcessError as err:
        logger.error("call failed with: %s stderr: %s", err, err.stderr)
        feed = {}
    except json.decoder.JSONDecodeError as err:
        logger.error("json decode failed: %s", err)
        feed = {}
    logger.info("stderr: %s", stderr)
    return stdout.get(feed)


async def fetch_cex_feeds(feeds: list[str]) -> list:
    """Fetch results from the collector software and send them to the
    validator.
    """
    for feed in random.sample(feeds, len(feeds)):
        logger.info("feed: %s", feed)
        res = await fetch_cex_data(feed=feed)
        if not res:
            logger.error("cannot retrieve data for: '%s'", feed)
            continue
        yield res


def _return_ca_ssl_context():
    """Return an ssl context for testing a connection to a validator
    signed by a certificate authority.
    """
    return ssl.create_default_context(cafile=certifi.where())


async def sign_message(data_to_send: dict):
    """Sign the node message before sending."""
    return sign_with_key(data_to_send, config.SIGNING_KEY)


async def send_to_ws(validator_websocket, data_to_send: dict):
    """Send data to a websocket."""
    id_ = data_to_send["message"]["identity"]["node_id"]
    timestamp = data_to_send["message"]["timestamp"]
    feed = data_to_send["message"]["feed"]
    logger.info(
        "sending message '%s' from id: %s with timestamp: %s", feed, id_, timestamp
    )
    data_to_send = await sign_message(json.dumps(data_to_send))
    await validator_websocket.send(data_to_send)
    try:
        # `wait_for` exits early if necessary to avoid the validator
        # swallowing this message without return so we can continue onto the next.
        msg = await asyncio.wait_for(validator_websocket.recv(), 10)
        if "ERROR" in msg:
            logger.error("websocket response: %s (%s)", msg, feed)
            return
        logger.error("websocket response: %s (%s)", msg, feed)
    except asyncio.exceptions.TimeoutError:
        logger.error("websocket wait_for resp timeout for feed '%s'", feed)
    return


async def fetch_and_send(identity: dict) -> None:
    """Fetch feed data and send it to a validator websocket."""

    # CEX feeds. Others can be added to the array as required,
    # e,g, [ "ADA/USD", "ADA/EUR", "USDT/USD" ]
    cex_feeds = [
        "ADA/USD",
        "ADA/EUR",
    ]

    # DEX feeds. Others can be added as per cex_feeds as long as they
    # are in DEX_PAIRS.
    dex_feeds = [
        "FACT-ADA",
        "NEWM-ADA",
        "WMT-ADA",
        # Sponsored.
        "ADA-DJED",
        "ADA-iUSD",
        "ADA-USDM",
        "HUNT-ADA",
        "iBTC-ADA",
        "iETH-ADA",
        "LENFI-ADA",
        "LQ-ADA",
        "MIN-ADA",
        "SHEN-ADA",
        "SNEK-ADA",
    ]

    data_cex = fetch_cex_feeds(cex_feeds)
    data_dex = []
    if CNT_ENABLED:
        data_dex = await fetch_dex_feeds(dex_feeds, identity)

    id_ = identity["node_id"]
    validator_connection = f"{config.VALIDATOR_URI}/{id_}/"

    try:
        ssl_context = None
        if validator_connection.startswith("wss://"):
            ssl_context = _return_ca_ssl_context()
        logger.info("validator connection: %s", validator_connection)
        async with websockets.connect(
            validator_connection,
            ssl=ssl_context,
            user_agent_header=f"orcfax/collector-WebSocket ({get_version()})",
            timeout=120,
        ) as validator_websocket:
            try:
                async for data_to_send in data_cex:
                    await send_to_ws(validator_websocket, data_to_send)
                    time.sleep(0.1)
                if not CNT_ENABLED:
                    logging.info("cnt collection is not enabled")
                    return
                for data_to_send in data_dex:
                    if not data_to_send:
                        continue
                    await send_to_ws(validator_websocket, data_to_send)
                    time.sleep(0.1)
            except websockets.exceptions.ConnectionClosedError as err:
                logger.error("connection closed unexpectedly: %s", err)
    except websockets.exceptions.InvalidStatusCode as err:
        logger.error(
            "unexpected response status code from validator: %s (url: %s)",
            err,
            validator_connection,
        )


async def collector_main():
    """Collector node main.

    The script is designed so that it is staggered between 1 and 20 seconds
    so that that validator nodes are not overloaded.

    Data is then collected from central exchanges (CEXes) and then decentralized
    exchanges (DEXes) (the latter via an indexing service) and then
    forwarded onto a validator node.
    """

    # Stagger the collection of the data in this script so that the
    # validator node isn't flooded each round.
    logging.info("collector-node version: '%s'", get_version())
    await asyncio.sleep(random.randint(1, 15))
    identity = await read_identity()
    await fetch_and_send(identity)


def main():
    """Primary entry point of this script."""
    pid = os.getpid()
    start_time = time.time()
    logger.info("----- node runner (%s) -----", pid)
    try:
        with flock.FlockContext(flock_name_base="cnode_runner"):
            try:
                asyncio.run(collector_main())
            # pylint: disable=W0718   # global catch, if this doesn't run, nothing does.
            except Exception as err:
                logger.error("collector node runner not running: %s", err)
    except BlockingIOError as err:
        logger.info("collector node runner already in use: %s", err)
        sys.exit(1)
    end_time = time.time() - start_time
    logger.info(
        "----- node runner (%s) completed after: '%s' seconds -----", pid, end_time
    )


if __name__ == "__main__":
    main()
