# CHEAP_FLIGHTS_MCP

[![smithery badge](https://smithery.ai/badge/ingrobertfodor/CHEAP_FLIGHTS_MCP)](https://smithery.ai/servers/ingrobertfodor/CHEAP_FLIGHTS_MCP)

**MCP server for searching cheap flights in real-time via RyanAir, WizzAir, and Google Flights.**

Built with FastMCP (Anthropic's Model Context Protocol), featuring parallel airline queries via `asyncio.gather`, exponential backoff retry, and verified booking deep links.

## Features

- **Real-time prices** directly from airline systems (not cached/aggregated)
- **Parallel search** across multiple airlines simultaneously
- **FastMCP** - modern declarative MCP pattern (2025 standard)
- **Web UI** - browser-based interface with dark theme
- **AI Agent** - conversational flight search via Claude (SAP Hyperspace)
- **Deep booking links** - click to buy directly on airline website
- **Email results** - send search results via email (mailto: protocol)
- **Configurable airlines** - add/remove airlines dynamically
- **USD/EUR conversion** - live exchange rate for Google Flights results
- **Retry mechanism** - exponential backoff + jitter for rate-limited APIs
- **Security** - input validation, generic errors, no credentials in code

## Supported Airlines

| Airline | Data Source | Destinations | Reliability |
|---------|-------------|-------------|-------------|
| RyanAir | ryanair-py library | Routes API (all, incl. seasonal) | Excellent |
| WizzAir | Unofficial JSON API | Route map | Good (429 retry) |
| Google Flights | fast-flights library | N/A | Good (verification source) |

## Installation

```bash
git clone https://github.com/IngRobertFodor/CHEAP_FLIGHTS_MCP.git
cd CHEAP_FLIGHTS_MCP
pip install -r requirements.txt
```

Or via Smithery:
```bash
npx @smithery/cli install @ingrobertfodor/CHEAP_FLIGHTS_MCP
```

## Quick Start

### Option A: Web UI (no AI required)

```bash
python web/app.py
```
Open browser: http://localhost:5000

### Option B: CLI AI Agent (requires AI Proxy)

```bash
python agent/flight_agent.py
```

### Option C: MCP Server only (for integration)

```bash
python mcp_server/server.py
```

## Configuration

Create a `.env` file:
```
AI_PROXY_BASE_URL=http://localhost:6655
AI_PROXY_API_KEY=your-api-key-here
```

> **Note:** The `.env` file is gitignored and never committed. Each user provides their own API key.

Edit `mcp_server/config.json` to configure active airlines:
```json
{
    "active_airlines": ["ryanair", "wizzair"],
    "available_airlines": ["ryanair", "wizzair", "google_flights"]
}
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_flights` | Search flights between airports (origin, destination, date, return_date, adults) |
| `list_active_airlines` | Show currently active airlines |
| `add_airline` | Add an airline to active list |
| `remove_airline` | Remove an airline from active list |
| `get_destinations` | Get all available routes from an airport |

## Usage Example

### Web UI
1. Enter IATA codes (BTS, STN, BCN...)
2. Select dates and passengers
3. Click "Search flights"
4. Optionally: check "Send email" to email results with booking links

### AI Agent
```
You: Find the cheapest flight from Bratislava to London on July 15, 2026
Agent: [calls search_flights] Found RyanAir BTS->STN for 19.99 EUR...
```

## Architecture

```
Browser → Flask (app.py) → MCP Server (server.py) → RyanAir/WizzAir API
                                                  → Google Flights
                        → Claude AI (optional, via SAP Hyperspace)
```

The web form searches **without AI** - directly calling MCP tools.
The AI chat requires Claude (via SAP AI Proxy).

## Testing

```bash
# Quick test (no AI needed):
python test_search.py

# Full agent test (8 use cases, requires AI Proxy):
python test_agent_prompts.py
```

## Adding a New Airline

1. Create `mcp_server/airlines/new_airline.py` (inherit from `BaseAirline`)
2. Implement `search_flights()` and `get_destinations()`
3. Add import to `mcp_server/airlines/__init__.py`
4. Add to `config.json` → `available_airlines`
5. Add to `server.py` → `get_airline_adapters()`

## Security

- API keys stored in `.env` (gitignored, never committed)
- Flask runs with `debug=False`
- CORS restricted to localhost
- Input validation and sanitization (IATA codes, dates, adults)
- Generic error messages (no internal info leaked)
- All logging to stderr (stdout reserved for MCP communication)

## Tech Stack

- Python 3.12+
- MCP SDK 1.27+ (FastMCP)
- httpx (async HTTP)
- tenacity (retry with backoff)
- ryanair-py (RyanAir API)
- fast-flights (Google Flights)
- Flask + flask-cors (Web server)
- SAP Hyperspace AI Proxy (Claude)

## License

MIT License - see [LICENSE](LICENSE)

## Author

Robert Fodor - 2026