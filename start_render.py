"""
Render.com startup script.
Spusti MCP server v streamable-http mode s /.well-known/mcp/server-card.json endpointom.
"""
import os
import sys
import importlib.util
import uvicorn
from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse

# Render.com nastavi PORT env variable
port = int(os.environ.get("PORT", "10000"))

# Cesty
project_root = Path(__file__).resolve().parent
mcp_server_dir = project_root / "mcp_server"

# Pridaj mcp_server dir do path
sys.path.insert(0, str(mcp_server_dir))

# Zmen working directory
os.chdir(str(mcp_server_dir))

# Importuj server.py
spec = importlib.util.spec_from_file_location("server", str(mcp_server_dir / "server.py"))
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)

# Server card data pre Smithery discovery
SERVER_CARD = {
    "name": "CHEAP_FLIGHTS_MCP",
    "description": "MCP server for searching cheap flights in real-time via RyanAir, WizzAir and Google Flights.",
    "version": "1.0.0",
    "author": "Robert Fodor",
    "homepage": "https://github.com/IngRobertFodor/CHEAP_FLIGHTS_MCP",
    "license": "MIT",
    "transport": "streamable-http",
    "tools": [
        {"name": "search_flights", "description": "Search flights between airports sorted by price."},
        {"name": "list_active_airlines", "description": "Show active airlines."},
        {"name": "add_airline", "description": "Add airline to active list."},
        {"name": "remove_airline", "description": "Remove airline from active list."},
        {"name": "get_destinations", "description": "Get available destinations from airport."},
    ]
}


async def server_card_endpoint(request):
    """Smithery discovery endpoint."""
    return JSONResponse(SERVER_CARD)


async def health(request):
    """Health check."""
    return JSONResponse({"status": "ok"})


# Ziskaj MCP ASGI app
mcp_app = server_module.mcp.streamable_http_app()

# Kombinuj: server-card.json + health + MCP app
app = Starlette(
    routes=[
        Route("/.well-known/mcp/server-card.json", server_card_endpoint),
        Route("/health", health),
        Mount("/", mcp_app),
    ]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)