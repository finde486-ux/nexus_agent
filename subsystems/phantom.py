import time
import uuid
import os
import ast
from typing import Dict, Any, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope
from subsystems.memory_graph import CodeDNA

class PhantomHandler(FileSystemEventHandler):
    def __init__(self, phantom_subsystem):
        self.phantom = phantom_subsystem

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            self.phantom.on_file_modified(event.src_path)

class Phantom(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)
        self.observer = Observer()
        self.findings = []

    async def initialize(self):
        # 3.8.1 What PHANTOM Watches
        self.observer.schedule(PhantomHandler(self), path=".", recursive=True)
        self.observer.start()
        self.logger.info("Phantom monitor started.")

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "GET_FINDINGS":
            await self.message_bus.send(MessageEnvelope(
                str(uuid.uuid4()), self.subsystem_id, envelope.sender_id, "PHANTOM_FINDINGS",
                {"findings": self.findings}, time.time(), 3, envelope.msg_id
            ))

    def on_file_modified(self, filepath: str):
        self.logger.info(f"Phantom detected change in {filepath}")
        try:
            with open(filepath, 'r') as f:
                code = f.read()

            # 1. Growing complexity
            complexity = self._calculate_complexity(code)
            if complexity > 10:
                self.findings.append({"type": "COMPLEXITY", "file": filepath, "value": complexity})

            # 2. Duplicate code patterns (Logic would use MEMORY-GRAPH)
            dna_hash = CodeDNA.compute_hash(code)
            # In real impl, query MEMORY-GRAPH for similarity > 0.75

            # 3. Test coverage gaps (Logic would check for corresponding test file)
            test_file = filepath.replace(".py", "_test.py") # Simplified
            if not os.path.exists(test_file):
                self.findings.append({"type": "TEST_GAP", "file": filepath, "issue": "No corresponding test file."})

        except Exception as e:
            self.logger.error(f"Phantom failed to analyze {filepath}: {e}")

    def _calculate_complexity(self, code: str) -> int:
        # Simplified cyclomatic complexity (count branches)
        try:
            tree = ast.parse(code)
            count = 1
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler)):
                    count += 1
            return count
        except Exception:
            return 1

    def stop(self):
        self.observer.stop()
        self.observer.join()
        super().stop()
