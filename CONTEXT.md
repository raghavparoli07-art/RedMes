# Security Rules and Constraints

1. **No secrets in code.** Ollama runs on `localhost` only. No external API calls by default. If the Gemini fallback is configured, ensure no keys are hardcoded in the repository (use environment variables).
2. **Sanitize everything.** Every piece of user input passes through `sanitize_input()` (an MCP tool) before reaching any agent or being stored in the database.
3. **Parameterized queries only.** No string-concatenated SQL anywhere. All database interactions in `db/database.py` use SQLite parameterized inputs `?`.
4. **Input limits.** Raw message capped at 2000 characters. Empty submissions rejected with a clear 400 error.
5. **Rate limiting.** Maximum 1 `/analyze` call per 2 seconds per session. Implemented in-memory in `main.py`.
6. **Data stays local.** No personal data leaves the user's machine unless explicitly opted-in (which is not supported by default).
