"""Helper functions for configuring the runner script.

Config options should fail fast and so a number of different patterns
are used here to check and then fail if a key component isn't available
to the script.
"""

import json
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
load_dotenv("validator.env", override=False)

RANDOM_WAIT_MAX: Final[int] = int(os.getenv("RANDOM_WAIT_MAX", "15"))

try:
    validator_uri = os.environ["ORCFAX_VALIDATOR"]
    if "[" in validator_uri:
        VALIDATOR_URI: Final[list] = json.loads(validator_uri)
    else:
        VALIDATOR_URI: Final[str] = validator_uri
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

# CNT configuration.
#
# Within the app CNT_ENABLED controls whether we go to the dexes. Ogmios
# needs configuring at a minimum. Kupo can be set to improve performance
# on database startup.

OGMIOS_URL = None
try:
    OGMIOS_URL = os.environ["OGMIOS_URL"]
    logger.info("ogmios websocket: %s", OGMIOS_URL)
except KeyError:
    logger.error(
        "ogmios websocket url needs to be set, e.g. `export OGMIOS_URL=ws://<ip-address>`"
    )
    sys.exit(1)

KUPO_URL = None
try:
    KUPO_URL = os.environ["KUPO_URL"]
    logger.info("kupo url: %s", KUPO_URL)
except KeyError:
    KUPO_URL = None
    logger.info(
        "kupo url can optionally be set, e.g. `export KUPO_URL=http://<ip-address>`"
    )
