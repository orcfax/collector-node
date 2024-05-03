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
import websockets
from dotenv import load_dotenv
from pycardano import OgmiosChainContext
from simple_sign.sign import sign_with_key

CNT_ENABLED: Final[bool] = True

try:
    from cnt_collector_node.config import OGMIOS_URL, network
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

SIGNING_KEY = None

# Load the validator websocket URI from the environment.
load_dotenv("validator.env", override=True)
try:
    VALIDATOR_URI: Final[str] = os.environ["ORCFAX_VALIDATOR"]
    logger.info("websocket: %s", VALIDATOR_URI)
except KeyError:
    logger.error(
        "validator websocket needs setting, e.g. `export ORCFAX_VALIDATOR=wss://<node-ws-endpoint>`"
    )
    sys.exit(1)
try:
    NODE_IDENTITY_LOC: Final[str] = os.environ["NODE_IDENTITY_LOC"]
    logger.info("node identity: %s", NODE_IDENTITY_LOC)
except KeyError:
    logger.error(
        "node identity needs setting, e.g. `export NODE_IDENTITY_LOC=/tmp/.node-identity.json`"
    )
    sys.exit(1)
try:
    NODE_SIGNING_KEY: Final[str] = os.environ["NODE_SIGNING_KEY"]
    logger.info("signing key loc: %s", NODE_SIGNING_KEY)
    with open(NODE_SIGNING_KEY, "r", encoding="utf-8") as key:
        SIGNING_KEY = key.read()
except KeyError:
    logger.error(
        "signing key loc needs setting, e.g. `export NODE_SIGNING_KEY=/path/to/signing-key`"
    )
    sys.exit(1)
try:
    CNT_DB_NAME: Final[str] = os.environ["CNT_DB_NAME"]
    if not os.path.exists(CNT_DB_NAME):
        raise RuntimeError(f"database file does not exist: {CNT_DB_NAME}")
    logger.info("db loc: %s", CNT_DB_NAME)
except KeyError:
    logger.error(
        "cnt index database loc needs setting, e.g. `export CNT_DB_NAME=/path/to/cnt/database.db`"
    )
    sys.exit(1)


async def read_identity() -> dict:
    """Read the node identity file.

    Return a simplified version of the identity file and the location
    of the validator websocket.
    """
    identity = None
    try:
        with open(NODE_IDENTITY_LOC, "r", encoding="utf-8") as identity_json:
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
    conn = sqlite3.connect(CNT_DB_NAME)
    cur = conn.cursor()
    logger.info("connecting to ogmios")
    ogmios_context: OgmiosChainContext = OgmiosChainContext(
        ws_url=OGMIOS_URL, network=network
    )
    logger.info("current epoch: %s", ogmios_context.epoch)
    logger.info("latest block slot: %s", ogmios_context.last_block_slot)
    # create the "database" dict to use as a parameter for functions
    database = {
        "conn": conn,
        "cur": cur,
    }
    res = []
    for tokens_pair in requested:
        message, timestamp = await check_tokens_pair(
            database,
            ogmios_context,
            identity,
            tokens_pair,
            logger,
        )
        message = {
            "message": message,
            "node_id": identity["node_id"],
            "validation_timestamp": timestamp,
        }
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
                # "/home/orcfax/collector/gofer",
                "gofer",
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
    return sign_with_key(data_to_send, SIGNING_KEY)


async def send_to_ws(websocket, data_to_send: dict):
    """Send data to a websocket."""
    print(data_to_send)
    id_ = data_to_send["message"]["identity"]["node_id"]
    timestamp = data_to_send["message"]["timestamp"]
    logger.info("sending message from id: %s with timestamp: %s", id_, timestamp)
    data_to_send = await sign_message(json.dumps(data_to_send))
    await websocket.send(data_to_send)
    msg = await websocket.recv()
    logger.info("websocket response: %s", msg)


async def fetch_and_send(identity: dict) -> None:
    """Fetch feed data and send it to a validator websocket."""

    # CEX feeds. Others can be added to the array as required,
    # e,g, [ "ADA/USD", "ADA/EUR", "USDT/USD" ]
    cex_feeds = ["ADA/USD"]

    # DEX feeds. Others can be added as per cex_feeds as long as they
    # are in DEX_PAIRS.
    dex_feeds = [
        "FACT-ADA",
        "ADA-DJED",
        "LENFI-ADA",
        "LQ-ADA",
        "WMT-ADA",
        "NEWM-ADA",
    ]

    data_cex = fetch_cex_feeds(cex_feeds)
    if CNT_ENABLED:
        data_dex = await fetch_dex_feeds(dex_feeds, identity)

    id_ = identity["node_id"]
    validator_connection = f"{VALIDATOR_URI}/{id_}/"

    try:
        ssl_context = None
        if validator_connection.startswith("wss://"):
            ssl_context = _return_ca_ssl_context()
        logger.info("validator connection: %s", validator_connection)
        async with websockets.connect(
            validator_connection,
            ssl=ssl_context,
            user_agent_header="orcfax/collector-WebSocket",
            timeout=120,
        ) as websocket:
            try:
                async for data_to_send in data_cex:
                    await send_to_ws(websocket, data_to_send)
                    time.sleep(0.1)
                if not CNT_ENABLED:
                    logging.info("cnt collection is not enabled")
                    return
                for data_to_send in data_dex:
                    if not data_to_send:
                        continue
                    await send_to_ws(websocket, data_to_send)
                    time.sleep(0.1)
            except websockets.exceptions.ConnectionClosedError as err:
                logger.error("connection closed unexpectedly: %s", err)
    except websockets.exceptions.InvalidStatusCode as err:
        logger.error(
            "unexpected response status code from validator: %s (url: %s)",
            err,
            validator_connection,
        )


async def main():
    """Primary entry point of this script.

    The script is designed so that it is staggered between 1 and 20 seconds
    so that that validator nodes are not overloaded.

    Data is then collected from central exchanges (CEXes) and then decentralized
    exchanges (DEXes) (the latter via an indexing service) and then
    forwarded onto a validator node.
    """

    # Stagger the collection of the data in this script so that the
    # validator node isn't flooded each round.
    await asyncio.sleep(random.randint(1, 20))
    identity = await read_identity()
    await fetch_and_send(identity)


if __name__ == "__main__":
    asyncio.run(main())
