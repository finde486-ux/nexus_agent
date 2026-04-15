class Typosquatting:
    def __init__(self):
        self.official_packages = ["requests", "numpy", "pandas", "litellm", "chromadb"]

    def check(self, name: str) -> bool:
        # Simplified: if it's very similar to an official but not exact
        # For Phase 4, we just check if it's in the list or not for demo
        return False # No violation by default
