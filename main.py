import asyncio
import logging
from core.message_bus import MessageBus
from config import Config
from subsystems.omnirouter import OmniRouter
from subsystems.cogload import CogLoad
from subsystems.memory_graph import MemoryGraph
from subsystems.nerve import Nerve
from subsystems.sentinel import Sentinel
from subsystems.forge import Forge
from subsystems.adversary import Adversary
from subsystems.cortex import Cortex
from subsystems.phantom import Phantom
from subsystems.immune import Immune
from subsystems.evolver import Evolver
from subsystems.timetravel import TimeTravel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NEXUS-MAIN")

async def main():
    logger.info("Starting NEXUS Agent (Phases 1-8)...")

    # Initialize Message Bus
    message_bus = MessageBus()

    # Initialize all 12 subsystems
    subsystems = [
        Cortex("SYS-01", message_bus),
        MemoryGraph("SYS-02", message_bus),
        Nerve("SYS-03", message_bus),
        Forge("SYS-04", message_bus),
        Adversary("SYS-05", message_bus),
        OmniRouter("SYS-06", message_bus),
        Sentinel("SYS-07", message_bus),
        Phantom("SYS-08", message_bus),
        Evolver("SYS-09", message_bus),
        CogLoad("SYS-10", message_bus),
        TimeTravel("SYS-11", message_bus),
        Immune("SYS-12", message_bus)
    ]

    # Initialize all subsystems
    for sub in subsystems:
        await sub.initialize()

    # Run all subsystems concurrently
    tasks = [asyncio.create_task(sub.run()) for sub in subsystems]

    # Also run background loops
    for sub in subsystems:
        if isinstance(sub, Nerve):
            tasks.append(asyncio.create_task(sub.run_telemetry_loop()))

    logger.info("All 12 NEXUS subsystems initialized and running.")

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
