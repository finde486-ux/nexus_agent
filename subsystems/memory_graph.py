import sqlite3
import chromadb
import ast
import json
import hashlib
import time
import uuid
from typing import List, Dict, Any, Optional, Set
from core.subsystem_base import SubsystemBase
from core.message_bus import MessageBus, MessageEnvelope
from config import Config

class CodeDNA:
    @staticmethod
    def compute_hash(source_code: str) -> str:
        # 3.2.3 DNA hash computation algorithm
        try:
            tree = ast.parse(source_code)
            # 1. Normalize the AST
            normalized_tree = CodeDNA._normalize_ast(tree)
            # 2. Serialize to canonical representation
            # ast.unparse is available in Python 3.9+ and provides a cleaner normalization
            ast_str = ast.unparse(normalized_tree)
            # 3. Compute SHA-256
            return hashlib.sha256(ast_str.encode()).hexdigest()
        except Exception:
            # Fallback if parsing fails
            return hashlib.sha256(source_code.encode()).hexdigest()

    @staticmethod
    def _normalize_ast(tree: ast.AST) -> ast.AST:
        # Rename all local variables and function names to canonical names
        var_map = {}
        var_count = [0] # Use list for closure mutability

        def get_var_name(old_name):
            if old_name not in var_map:
                var_map[old_name] = f"var_{var_count[0]}"
                var_count[0] += 1
            return var_map[old_name]

        class Normalizer(ast.NodeTransformer):
            def visit_Name(self, node):
                node.id = get_var_name(node.id)
                return node

            def visit_arg(self, node):
                node.arg = get_var_name(node.arg)
                return node

            def visit_FunctionDef(self, node):
                # Normalize function name as well for DNA match across renames
                node.name = "func_normalized"
                self.generic_visit(node)
                return node

        return Normalizer().visit(tree)

    @staticmethod
    def jaccard_similarity(hash1: str, hash2: str) -> float:
        s1 = set(hash1)
        s2 = set(hash2)
        intersection = s1.intersection(s2)
        union = s1.union(s2)
        return len(intersection) / len(union) if union else 0.0

class MemoryGraph(SubsystemBase):
    def __init__(self, subsystem_id: str, message_bus: MessageBus):
        super().__init__(subsystem_id, message_bus)
        self.db_path = Config.NEXUS_DB_PATH
        self.vector_dir = Config.CHROMA_DB_DIR
        self.conn = None
        self.chroma_client = None
        self.collection = None

    async def initialize(self):
        # Initialize SQLite
        self.conn = sqlite3.connect(self.db_path)
        self._init_sqlite()

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.vector_dir)
        self.collection = self.chroma_client.get_or_create_collection(name="nexus_vectors")

        self.logger.info("MemoryGraph initialized.")

    def _init_sqlite(self):
        cursor = self.conn.cursor()
        # 3.2.2 SQLite Schema
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS files (
          file_id     TEXT PRIMARY KEY,
          abs_path    TEXT NOT NULL,
          language    TEXT,
          dna_hash    TEXT,
          last_modified REAL,
          size_bytes  INTEGER
        );

        CREATE TABLE IF NOT EXISTS functions (
          func_id     TEXT PRIMARY KEY,
          file_id     TEXT REFERENCES files(file_id),
          func_name   TEXT NOT NULL,
          line_start  INTEGER,
          line_end    INTEGER,
          dna_hash    TEXT,
          complexity  INTEGER
        );

        CREATE TABLE IF NOT EXISTS decisions (
          decision_id TEXT PRIMARY KEY,
          task_id     TEXT,
          timestamp   REAL,
          description TEXT,
          rationale   TEXT,
          files_affected TEXT
        );

        CREATE TABLE IF NOT EXISTS bugs (
          bug_id      TEXT PRIMARY KEY,
          task_id     TEXT,
          file_id     TEXT REFERENCES files(file_id),
          line_no     INTEGER,
          error_type  TEXT,
          description TEXT,
          root_cause  TEXT,
          fix_applied TEXT,
          test_added  TEXT,
          timestamp   REAL
        );

        CREATE TABLE IF NOT EXISTS dependencies (
          dep_id      TEXT PRIMARY KEY,
          name        TEXT NOT NULL,
          version     TEXT,
          ecosystem   TEXT,
          scan_status TEXT,
          scan_report TEXT,
          install_ts  REAL
        );
        """)
        self.conn.commit()

    async def process_message(self, envelope: MessageEnvelope):
        if envelope.msg_type == "STORE_DATA":
            await self.store_data(envelope)
        elif envelope.msg_type == "QUERY_DATA":
            await self.query_data(envelope)

    async def store_data(self, envelope: MessageEnvelope):
        table = envelope.payload.get("table")
        data = envelope.payload.get("data").copy()

        if not table or not data:
            return

        # Handle 'content' field for vectors but not for SQL if not in schema
        content = data.pop("content", None)

        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})"

        cursor = self.conn.cursor()
        cursor.execute(sql, list(data.values()))
        self.conn.commit()

        # If storing a file, also update vectors
        if table == "files":
            self.collection.add(
                ids=[data["file_id"]],
                documents=[content if content else data["abs_path"]],
                metadatas=[{"abs_path": data["abs_path"]}]
            )

    async def query_data(self, envelope: MessageEnvelope):
        query_type = envelope.payload.get("type")

        result = None
        if query_type == "SQL":
            sql = envelope.payload.get("query")
            params = envelope.payload.get("params", [])
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            result = cursor.fetchall()
        elif query_type == "VECTOR":
            query_text = envelope.payload.get("text")
            n_results = envelope.payload.get("n_results", 5)
            result = self.collection.query(query_texts=[query_text], n_results=n_results)

        response = MessageEnvelope(
            msg_id=str(uuid.uuid4()),
            sender_id=self.subsystem_id,
            receiver_id=envelope.sender_id,
            msg_type="QUERY_RESULT",
            payload={"result": result},
            timestamp=time.time(),
            priority=envelope.priority,
            correlation_id=envelope.msg_id
        )
        await self.message_bus.send(response)
