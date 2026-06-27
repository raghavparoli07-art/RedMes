# Redmes

Redmes ("ready message") is an AI agent system that acts as an emotional buffer for your communications. It reads your raw, emotionally charged, or unclear drafts and rewrites them into polished, well-toned versions that still sound like you. By keeping track of your history with each contact, it learns your communication patterns and warns you if you're repeating past mistakes, all while keeping your data strictly local.

## Architecture

```text
User Input (Text, Recipient, Platform)
        │
        ▼
   [ FastAPI Backend ]
        │
        ▼ (Google ADK Orchestrator)
  ┌────────────────────────────────────────────────────────────┐
  │ 1. Context Risk Agent: Assesses tone and escalation risk   │
  │                           │                                │
  │ 2. Memory Outcome Agent: Fetches past outcomes via MCP     │
  │                           │                                │
  │ 3. Voice Rewriter Agent: Drafts 3 tone versions anchored   │
  │    to your personal voice samples                          │
  └───────────────────────────┬────────────────────────────────┘
        │                     │
        ▼                     ▼
[ MCP Server (fastmcp) ] <--> [ SQLite Local DB ]
        │
        ▼
User selects version
        │
        ▼
  4. Channel Formatter Agent: Formats for Email, Slack, or Text
```

## Setup Instructions

1. Install Ollama and pull the Gemma 2 9B model:
   ```bash
   ollama run gemma2:9b
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
4. Open your browser to `http://localhost:8000`.

## Hackathon Concept Map

This project demonstrates the required hackathon concepts in the following ways:
- **Multi-agent system (Google ADK)**: The `orchestrator.py` script chains the four specialized agents in `agents/`.
- **MCP Server**: The `mcp_server/redmes_server.py` implements a `fastmcp` server, launched as a background subprocess, handling DB queries, sanitization, and sample fetching.
- **Security features**: Implemented across the stack. Input is sanitized via the MCP tool `sanitize_input()` before processing. The database uses strictly parameterized queries. `CONTEXT.md` outlines further guardrails.
- **Deployability**: Runs entirely offline with a single startup command (`python main.py`). No cloud API keys required.

## Privacy Guarantee

Your communications are private. No data leaves your local machine. All LLM processing happens locally via Ollama, and conversation history is stored in a local SQLite file. No external API keys are required or used.
