"""Flock (file lock) management.

via. https://seds.nl/notes/locking-python-scripts-with-flock/
"""

# pylint: disable=R1732

import fcntl
import io
import logging
import os
import pathlib
import tempfile

logger = logging.getLogger(__name__)


class FlockContext:
    lock_name: str = ""  # lock filename.
    lock_file: io.TextIOWrapper = None  # lock file handle.

    def __init__(self, flock_name_base: str = ""):
        self.flock_name_base = flock_name_base

    def __enter__(self):
        self.flock_acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.flock_release()

    def flock_acquire(self, operation: int = fcntl.LOCK_EX | fcntl.LOCK_NB):
        """Acquire the flock lockfile

        will raise `BlockingIOError` if the lock has already been acquired.
        """
        if not self.flock_name_base:
            self.flock_name_base = "flock"
        self.lock_name = pathlib.Path().joinpath(
            tempfile.gettempdir(), f"{self.flock_name_base}.flock"
        )
        logger.info("acquiring collector node lock file: '%s'", self.lock_name)
        lock_file = open(self.lock_name, "wb")
        fcntl.flock(lock_file, operation)
        self.lock_file = lock_file

    def flock_release(self):
        """Release the flock lockfile."""
        logger.info("releasing and unlinking: '%s'", self.lock_name)
        fcntl.flock(self.lock_file, fcntl.LOCK_UN)
        os.close(self.lock_file.fileno())
        os.unlink(self.lock_name)
