# NEXUS: Next-Generation Autonomous Engineering Intelligence

NEXUS is a fully autonomous, self-evolving, locally-executing software engineering intelligence agent. Designed to function as a complete engineering team, NEXUS spans architecture, implementation, testing, security, and continuous self-improvement.

## 1. Executive Summary
Unlike conventional AI assistants, NEXUS operates entirely on commodity hardware with zero data leaving your machine. It leverages a 12-subsystem architecture coordinated by an asynchronous internal message bus to handle complex engineering tasks with a focus on local-first privacy, hardware awareness, and zero-trust security.

## 2. Core Principles
- **Local-first**: Agent logic, memory, and execution run on your machine.
- **Privacy-absolute**: No code, prompts, or outputs are transmitted to third parties without consent.
- **Hardware-aware**: Real-time telemetry informs all agent decisions.
- **Adversarial by default**: Every output is attacked and stress-tested before delivery.
- **Memory-persistent**: Uses a local knowledge graph to remember every decision.

## 3. System Architecture
NEXUS consists of 12 integrated subsystems:
- **CORTEX (SYS-01)**: Multi-agent debate-driven reasoning engine.
- **MEMORY-GRAPH (SYS-02)**: Persistent SQLite + ChromaDB knowledge graph.
- **NERVE (SYS-03)**: Real-time hardware telemetry and resource budgeting.
- **FORGE (SYS-04)**: Autonomous multi-file code generation and build engine.
- **ADVERSARY (SYS-05)**: Automated code attack and QA simulation.
- **OMNIROUTER (SYS-06)**: Universal LLM router and token optimizer.
- **SENTINEL (SYS-07)**: Zero-trust security and dependency guardian.
- **PHANTOM (SYS-08)**: Passive background codebase monitoring.
- **EVOLVER (SYS-09)**: Biological mutation engine for code optimization.
- **COGLOAD (SYS-10)**: Cognitive load balancer for intelligent model routing.
- **TIMETRAVEL (SYS-11)**: Execution history reconstruction and root-cause debugging.
- **IMMUNE (SYS-12)**: Architecture health monitor and predictive bug scoring.

## 4. Local Setup Guide

### Prerequisites
- **Python 3.12+**
- **Docker**: Required for isolated code execution (FORGE sandbox).
- **Git**

### Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/finde486-ux/nexus_agent.git
   cd nexus_agent
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Environment Variables**:
   Create a `.env` file in the root directory and add your LLM API keys:
   ```env
   OPENAI_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here
   GOOGLE_API_KEY=your_key_here
   ```

5. **Build the Sandbox Image**:
   ```bash
   docker build -t nexus-sandbox:latest .
   ```

## 5. Usage

### Starting the Agent
To start the NEXUS agent and all its subsystems:
```bash
python main.py
```

### Using the CLI
NEXUS provides a command-line interface for interacting with the subsystems:
```bash
# Submit an engineering task
python -m cli.commands solve "Implement a secure REST API in FastAPI"

# View codebase health report
python -m cli.commands health

# Optimize a specific file
python -m cli.commands evolve path/to/file.py
```

## 6. Development and Testing
To run the full suite of unit and integration tests:
```bash
PYTHONPATH=. python3 -m pytest
```

---
*Classification: CONFIDENTIAL — INTERNAL USE ONLY*
