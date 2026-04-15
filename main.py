import asyncio
import logging
from core.message_bus import MessageBus
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NEXUS-MAIN")

async def main():
    logger.info("Starting NEXUS Agent...")

    # Initialize Message Bus
    message_bus = MessageBus()

    # In Phase 1, we just set up the core infrastructure.
    # Future phases will initialize and run subsystems here.

    logger.info("Core infrastructure initialized.")

    # Keep main alive for now or exit if just a skeleton
    # await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("NEXUS Agent stopped by user.")
