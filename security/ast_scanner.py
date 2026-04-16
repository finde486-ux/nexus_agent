import ast
import os
from typing import List, Dict, Any

class ASTScanner:
    def __init__(self):
        self.violations = []

    def scan(self, source_code: str, resource_budget: Dict[str, Any] = None) -> List[Dict[str, str]]:
        self.violations = []
        try:
            tree = ast.parse(source_code)
            self._check_node(tree, resource_budget)
        except Exception as e:
            self.violations.append({"type": "PARSE_ERROR", "message": str(e)})
        return self.violations

    def _check_node(self, node, budget):
        workspace = "/workspace"
        for child in ast.walk(node):
            # 3.7.2 Custom AST Security Checks

            # Network socket creation
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute) and child.func.attr == 'socket':
                    if not budget or not budget.get("network_allowed", False):
                        self.violations.append({"type": "SECURITY_VIOLATION", "message": "Unauthorized network socket creation."})

                # FS access outside workspace
                if isinstance(child.func, ast.Name) and child.func.id == 'open':
                    if child.args:
                        arg = child.args[0]
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            path = arg.value
                            if not (path.startswith(workspace) or path.startswith("./") or "/" not in path):
                                self.violations.append({"type": "SECURITY_VIOLATION", "message": f"Unauthorized filesystem access: {path}"})
                        else:
                            self.violations.append({"type": "SECURITY_VIOLATION", "message": "Dynamic path in open() call."})

                # subprocess.call(), os.system(), or eval()
                if isinstance(child.func, ast.Name) and child.func.id in ['eval', 'exec']:
                    self.violations.append({"type": "SECURITY_VIOLATION", "message": f"Dangerous function call: {child.func.id}"})

                if isinstance(child.func, ast.Attribute):
                    if child.func.attr in ['system', 'popen', 'call', 'run']:
                        self.violations.append({"type": "SECURITY_VIOLATION", "message": f"Dangerous subprocess call: {child.func.attr}"})

            # Encoded/obfuscated strings
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                if len(child.value) > 100 and child.value.isalnum():
                    self.violations.append({"type": "SECURITY_VIOLATION", "message": "Potential obfuscated string detected."})

            # Hardcoded credentials
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        if any(key in target.id.lower() for key in ['api_key', 'password', 'secret', 'token']):
                            self.violations.append({"type": "SECURITY_VIOLATION", "message": f"Potential hardcoded credential: {target.id}"})
