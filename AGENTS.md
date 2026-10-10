# Development conventions

- Use Python 3.11+ and the src package layout. Run `python -m pytest` after changes.
- Keep data acquisition in providers, ranking in scoring, narrative generation in llm.
- All behavior parameters belong in Settings or validated request models.
- Never present mock scenarios, scores, travel times, or imagined friction as measured commute facts.
- Unknown cities use explicit placeholder entities; do not invent real stations or transit connections.
- Do not silently replace a failed real data or LLM call with mock output.
- No live external calls in tests; use injected providers and HTTPX transports.
- Keep credentials in environment variables; do not commit .env or log API keys.
