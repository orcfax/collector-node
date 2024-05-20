"""App version.

Provides a bunch of boilerplate to enable source control based
versioning based on tags/commit information.
"""

from importlib.metadata import PackageNotFoundError, version


def get_version():
    """Return package version to the calling code.

    Version is set to a default value if it isn't picked up by importlib
    as anticipated, i.e. if the code hasn't been installed or isn't
    being run as a package correctly.

    NB. the value "0.0.0-dev" simply indicates that this is not a
    packaged version and so shouldn't be used in production. It will
    be overwritten if deployed correctly.
    """
    __version__ = "1.0.0-dev"
    try:
        __version__ = version("validator-node-api")
    except PackageNotFoundError:
        # package is not installed
        pass
    return __version__
