import time
import uuid
from typing import Dict, Any, List
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope
from security.ast_scanner import ASTScanner
from security.cve_db import CVEDB
from security.malware_patterns import MalwarePatterns
from security.typosquatting import Typosquatting

class Sentinel(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)
        self.scanner = ASTScanner()
        self.cve_db = CVEDB()
        self.malware_patterns = MalwarePatterns()
        self.typosquatting = Typosquatting()

    async def initialize(self):
        self.logger.info("Sentinel initialized.")

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "SCAN_DEPENDENCY":
            result = await self.scan_dependency(envelope.payload)
            response = MessageEnvelope(
                msg_id=str(uuid.uuid4()),
                sender_id=self.subsystem_id,
                receiver_id=envelope.sender_id,
                msg_type="SCAN_RESULT",
                payload=result,
                timestamp=time.time(),
                priority=envelope.priority,
                correlation_id=envelope.msg_id
            )
            await self.message_bus.send(response)
        elif envelope.msg_type == "SCAN_CODE":
            violations = self.scanner.scan(envelope.payload.get("code", ""), envelope.payload.get("budget"))
            response = MessageEnvelope(
                msg_id=str(uuid.uuid4()),
                sender_id=self.subsystem_id,
                receiver_id=envelope.sender_id,
                msg_type="CODE_SCAN_RESULT",
                payload={"violations": violations},
                timestamp=time.time(),
                priority=envelope.priority,
                correlation_id=envelope.msg_id
            )
            await self.message_bus.send(response)

    async def scan_dependency(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # 3.7.1 Dependency Scanning Pipeline
        name = payload.get("name")
        version = payload.get("version", "latest")

        report = []
        status = "CLEAN"

        # 1. Malware check
        if self.malware_patterns.is_malicious(name):
            status = "QUARANTINED"
            report.append(f"Malware detected: {name}")

        # 2. CVE check
        cves = self.cve_db.check_package(name, version)
        if cves:
            status = "QUARANTINED"
            report.append(f"CVEs found: {cves}")

        # 3. Typosquatting check
        if self.typosquatting.check(name):
            status = "QUARANTINED"
            report.append(f"Potential typosquatting detected: {name}")

        # 4. AST scanning (of package if available, simulated here)

        return {
            "name": name,
            "version": version,
            "status": status,
            "report": report
        }
