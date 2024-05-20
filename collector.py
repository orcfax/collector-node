"""Project level runner for the collector node."""
import asyncio

from src.collector_node.collector_node import main as collector_node_main


async def main():
    """Primary entry point of this script."""
    await collector_node_main()


if __name__ == "__main__":
    asyncio.run(main())
