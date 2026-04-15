class CVEDB:
    def __init__(self):
        self.cve_data = {} # Map of package_name -> list of CVEs

    def check_package(self, name: str, version: str) -> list:
        # Mock CVE check for Phase 4
        if name == "vulnerable-pkg":
            return [{"id": "CVE-2025-0001", "severity": "HIGH"}]
        return []
