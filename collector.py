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
import ssl
import subprocess
import sys
import time
from typing import Final

import certifi
import websockets
from dotenv import load_dotenv

sys.dont_write_bytecode = True

logger = logging.getLogger(__name__)

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s :: %(filename)s:%(lineno)s:%(funcName)s() :: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level="INFO",
)

# Default to UTC time.
logging.Formatter.converter = time.gmtime

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


def fetch_data(feed: str) -> dict:
    """Fetch data from the collector app using the subprocess command."""
    res = {}
    try:
        ps_out = subprocess.run(
            [
                "/home/orcfax/collector/gofer",
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
        return res
    except json.decoder.JSONDecodeError as err:
        logger.error("json decode failed: %s", err)
        return res
    logger.warning("stderr: %s", stderr)
    return stdout.get(feed)


def _return_ca_ssl_context():
    """Return an ssl context for testing a connection to a validator
    signed by a certificate authority.
    """
    return ssl.create_default_context(cafile=certifi.where())


async def fetch_and_store(feed: str):
    """Fetch results from the collector software and send them to the
    validator.
    """

    # Stagger the collection of the data in this script so that the
    # validator node isn't flooded.
    await asyncio.sleep(random.randint(1, 20))

    # Fetch the data to send.
    data_to_send = fetch_data(feed=feed)
    try:
        id_ = data_to_send["message"]["identity"]["node_id"]
        timestamp = data_to_send["message"]["timestamp"]
        logger.info("sending message from id: %s with timestamp: %s", id_, timestamp)
        validator_connection = f"{VALIDATOR_URI}/{id_}/"

        # Default to lhe default root certificates location.
        ssl_context = None
        if validator_connection.startswith("wss://"):
            ssl_context = _return_ca_ssl_context()

        logger.info("validator connection: %s", validator_connection)
        async with websockets.connect(
            validator_connection,
            ssl=ssl_context,
            user_agent_header="chronicle-labs/oracle-suite-collector-WebSocket",
        ) as websocket:
            await websocket.send(json.dumps(data_to_send))
            msg = await websocket.recv()
            logger.info("websocket response: %s", msg)
            await asyncio.sleep(2)
    except KeyError as err:
        logger.error("keyerror: %s", err)
    except websockets.exceptions.InvalidStatusCode as err:
        logger.error(
            "unexpected response status code from validator: %s (url: %s) (%s)",
            err,
            validator_connection,
            feed,
        )


async def main():
    """Primary entry point of this script."""
    feeds = [
        "ADA/USD"
    ]  # others can be added to the array as required, "ADA/EUR", "USDT/USD"
    for feed in random.sample(feeds, len(feeds)):
        logger.info("feed: %s", feed)
        await fetch_and_store(feed=feed)


if __name__ == "__main__":
    asyncio.run(main())
