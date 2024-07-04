"""Flock (file lock) management.

via. https://seds.nl/notes/locking-python-scripts-with-flock/
"""

# pylint: disable=R1732

import fcntl
import io
import logging
import os
import pathlib

logger = logging.getLogger(__name__)


class FlockContext:
    lock_name: str = ""
    lock_file: io.TextIOWrapper = None

    def __init__(self):
        pass

    def __enter__(self):
        self.flock_acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.flock_release()

    def flock_acquire(self, operation: int = fcntl.LOCK_EX | fcntl.LOCK_NB):
        """Acquire the flock lockfile

        will raise `BlockingIOError` if the lock has already been acquired.
        """
        self.lock_name = pathlib.Path().joinpath(
            f"/tmp/{pathlib.Path(__file__).name.strip('.py')}.flock"
        )
        logger.info("acquiring collector node lock file: '%s'", self.lock_name)
        lock_file = open(self.lock_name, "wb")
        fcntl.flock(lock_file, operation)
        self.lock_file = lock_file

    def flock_release(self):
        """Release the flock lockfile."""
        logger.info("releasing: '%s'", self.lock_name)
        fcntl.flock(self.lock_file, fcntl.LOCK_UN)
        os.close(self.lock_file.fileno())
