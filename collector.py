"""Project level runner for the collector node."""

from src.collector_node.collector_node import main as collector_node_main


def main():
    """Primary entry point of this script."""
    collector_node_main()


if __name__ == "__main__":
    main()
