import pytest
import os
import sqlite3
import chromadb
from subsystems.memory_graph import MemoryGraph, CodeDNA
from core.message_bus import MessageBus, MessageEnvelope
from config import Config

@pytest.fixture
def mock_config(tmp_path):
    Config.NEXUS_DB_PATH = str(tmp_path / "test_nexus.db")
    Config.CHROMA_DB_DIR = str(tmp_path / "test_vectors")
    return Config

@pytest.mark.asyncio
async def test_memory_graph_initialization(mock_config):
    bus = MessageBus()
    mg = MemoryGraph("SYS-02", bus)
    await mg.initialize()
    assert os.path.exists(Config.NEXUS_DB_PATH)
    assert os.path.exists(Config.CHROMA_DB_DIR)

@pytest.mark.asyncio
async def test_memory_graph_store_and_query_sql(mock_config):
    bus = MessageBus()
    mg = MemoryGraph("SYS-02", bus)
    await mg.initialize()

    # Store a file record
    payload = {
        "table": "files",
        "data": {
            "file_id": "F1",
            "abs_path": "/app/test.py",
            "language": "python",
            "dna_hash": "HASH1",
            "last_modified": 123.456,
            "size_bytes": 100,
            "content": "print('hello')"
        }
    }
    env = MessageEnvelope("M1", "SYS-01", "SYS-02", "STORE_DATA", payload, 0, 3, "C1")
    await mg.process_message(env)

    # Query it back
    query_payload = {
        "type": "SQL",
        "query": "SELECT * FROM files WHERE file_id = ?",
        "params": ["F1"]
    }
    q_env = MessageEnvelope("M2", "SYS-01", "SYS-02", "QUERY_DATA", query_payload, 0, 3, "C2")

    # We need to register SYS-01 to receive the response
    bus.register_subsystem("SYS-01")
    await mg.process_message(q_env)

    response = await bus.receive("SYS-01")
    assert response.msg_type == "QUERY_RESULT"
    assert response.payload["result"][0][0] == "F1"

@pytest.mark.asyncio
async def test_memory_graph_vector_search(mock_config):
    bus = MessageBus()
    mg = MemoryGraph("SYS-02", bus)
    await mg.initialize()

    # Store data with vector
    payload = {
        "table": "files",
        "data": {
            "file_id": "F2",
            "abs_path": "/app/vec.py",
            "content": "important logic about neural networks"
        }
    }
    await mg.process_message(MessageEnvelope("M3", "SYS-01", "SYS-02", "STORE_DATA", payload, 0, 3, "C3"))

    # Vector query
    query_payload = {
        "type": "VECTOR",
        "text": "neural networks"
    }
    bus.register_subsystem("SYS-01")
    await mg.process_message(MessageEnvelope("M4", "SYS-01", "SYS-02", "QUERY_DATA", query_payload, 0, 3, "C4"))

    response = await bus.receive("SYS-01")
    assert "F2" in response.payload["result"]["ids"][0]

def test_code_dna_hashing():
    code1 = "def foo(a, b):\n    x = a + b\n    return x"
    code2 = "def bar(val1, val2):\n    # renamed vars and changed func name\n    y = val1 + val2\n    return y"

    hash1 = CodeDNA.compute_hash(code1)
    hash2 = CodeDNA.compute_hash(code2)

    # They should match because names and comments are normalized
    assert hash1 == hash2

@pytest.mark.asyncio
async def test_memory_graph_1000_entries(mock_config):
    bus = MessageBus()
    mg = MemoryGraph("SYS-02", bus)
    await mg.initialize()

    for i in range(1000):
        payload = {
            "table": "decisions",
            "data": {
                "decision_id": f"D{i}",
                "task_id": "T1",
                "timestamp": i,
                "description": f"Decision {i}"
            }
        }
        await mg.process_message(MessageEnvelope(f"M{i}", "SYS-01", "SYS-02", "STORE_DATA", payload, 0, 3, f"C{i}"))

    # Verify count
    cursor = mg.conn.cursor()
    cursor.execute("SELECT count(*) FROM decisions")
    count = cursor.fetchone()[0]
    assert count == 1000
