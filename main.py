import asyncio
import logging
from core.message_bus import MessageBus
from config import Config
from subsystems.omnirouter import OmniRouter
from subsystems.cogload import CogLoad
from subsystems.memory_graph import MemoryGraph
from subsystems.nerve import Nerve
from subsystems.sentinel import Sentinel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NEXUS-MAIN")

async def main():
    logger.info("Starting NEXUS Agent...")

    # Initialize Message Bus
    message_bus = MessageBus()

    # Initialize implemented subsystems (Phases 1-4)
    subsystems = [
        OmniRouter("SYS-06", message_bus),
        CogLoad("SYS-10", message_bus),
        MemoryGraph("SYS-02", message_bus),
        Nerve("SYS-03", message_bus),
        Sentinel("SYS-07", message_bus)
    ]

    # Initialize all subsystems
    for sub in subsystems:
        await sub.initialize()

    # Run all subsystems concurrently
    tasks = [asyncio.create_task(sub.run()) for sub in subsystems]

    # Also run Nerve's telemetry loop if it exists
    for sub in subsystems:
        if isinstance(sub, Nerve):
            tasks.append(asyncio.create_task(sub.run_telemetry_loop()))

    logger.info("NEXUS subsystems (Phases 1-4) initialized and running.")

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Fatal error in subsystem: {e}")
    finally:
        for sub in subsystems:
            sub.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("NEXUS Agent stopped by user.")
