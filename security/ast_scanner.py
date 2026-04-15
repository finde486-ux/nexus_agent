import ast
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
        for child in ast.walk(node):
            # 3.7.2 Custom AST Security Checks

            # Network socket creation
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute) and child.func.attr == 'socket':
                    if not budget or not budget.get("network_allowed", False):
                        self.violations.append({"type": "SECURITY_VIOLATION", "message": "Unauthorized network socket creation."})

                # FS access outside workspace (simplified check)
                if isinstance(child.func, ast.Name) and child.func.id == 'open':
                    # In a real impl, we'd check the path argument
                    pass

                # subprocess.call(), os.system(), or eval()
                if isinstance(child.func, ast.Name) and child.func.id in ['eval', 'exec']:
                    self.violations.append({"type": "SECURITY_VIOLATION", "message": f"Dangerous function call: {child.func.id}"})

                if isinstance(child.func, ast.Attribute):
                    if child.func.attr in ['system', 'popen', 'call', 'run']:
                        self.violations.append({"type": "SECURITY_VIOLATION", "message": f"Dangerous subprocess call: {child.func.attr}"})

            # Encoded/obfuscated strings (simplified)
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                if len(child.value) > 100 and child.value.isalnum(): # Simple heuristic
                    # Could be base64
                    pass

            # Hardcoded credentials
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        if any(key in target.id.lower() for key in ['api_key', 'password', 'secret', 'token']):
                            self.violations.append({"type": "SECURITY_VIOLATION", "message": f"Potential hardcoded credential: {target.id}"})
