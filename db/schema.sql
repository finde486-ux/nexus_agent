-- memory_schema.sql
CREATE TABLE IF NOT EXISTS files (
  file_id     TEXT PRIMARY KEY,  -- SHA-256 of absolute path
  abs_path    TEXT NOT NULL,
  language    TEXT,
  dna_hash    TEXT,              -- semantic fingerprint (see 3.2.3)
  last_modified REAL,            -- unix timestamp
  size_bytes  INTEGER
);

CREATE TABLE IF NOT EXISTS functions (
  func_id     TEXT PRIMARY KEY,  -- SHA-256 of file_id + func_name + line_no
  file_id     TEXT REFERENCES files(file_id),
  func_name   TEXT NOT NULL,
  line_start  INTEGER,
  line_end    INTEGER,
  dna_hash    TEXT,
  complexity  INTEGER            -- cyclomatic complexity
);

CREATE TABLE IF NOT EXISTS decisions (
  decision_id TEXT PRIMARY KEY,
  task_id     TEXT,
  timestamp   REAL,
  description TEXT,              -- why this decision was made
  rationale   TEXT,
  files_affected TEXT            -- JSON array of file_ids
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
  test_added  TEXT,              -- test code that would have caught it
  timestamp   REAL
);

CREATE TABLE IF NOT EXISTS dependencies (
  dep_id      TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  version     TEXT,
  ecosystem   TEXT,              -- 'pip' | 'npm' | 'cargo' | etc.
  scan_status TEXT,              -- 'CLEAN' | 'QUARANTINED' | 'PENDING'
  scan_report TEXT,
  install_ts  REAL
);
