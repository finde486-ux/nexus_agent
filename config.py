import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    NEXUS_DB_PATH = os.getenv("NEXUS_DB_PATH", "nexus_memory.db")
    CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "nexus_vectors")
    SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "nexus-sandbox:latest")

    # LLM API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Memory Limits (Section 8)
    HARD_MEMORY_LIMIT_GB = 2.5
    THROTTLE_MEMORY_LIMIT_GB = 2.0
