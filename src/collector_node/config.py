"""Helper functions for configuring the runner script.

Config options should fail fast and so a number of different patterns
are used here to check and then fail if a key component isn't available
to the script.
"""

import logging
import os
import sys
import time
from typing import Final

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
    logger.info("db loc: %s", CNT_DB_NAME)
    if not os.path.exists(CNT_DB_NAME):
        raise RuntimeError(f"database file does not exist: {CNT_DB_NAME}")
except KeyError:
    logger.error(
        "cnt index database loc needs setting, e.g. `export CNT_DB_NAME=/path/to/cnt/database.db`"
    )
    sys.exit(1)
try:
    GOFER: Final[str] = os.environ["GOFER"]
    logger.info("gofer loc: %s", GOFER)
    if not os.path.exists(GOFER):
        raise RuntimeError(f"gofer cannot be found: {GOFER}")
except KeyError:
    logger.error(
        "gofer location needs to be configured, e.g. `export GOFER=/path/to/gofer`"
    )
    sys.exit(1)
try:
    OGMIOS_URL: Final[str] = os.environ["OGMIOS_URL"]
    logger.info("ogmios websocket: %s", OGMIOS_URL)
except KeyError:
    logger.error(
        "oogmios websocket url needs to be set, e.g. `export OGMIOS_URL=ws://<ip-address>`"
    )
    sys.exit(1)

OGMIOS_VERSION: Final[str] = os.environ.get("OGMIOS_VERSION", "v6")
logger.info("ogmios version: %s", OGMIOS_VERSION)
