"""
Render.com startup script.
MCP server v streamable-http mode + server-card.json + OAuth stubs.
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

# Server card
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
    return JSONResponse(SERVER_CARD)


async def health(request):
    return JSONResponse({"status": "ok"})


async def oauth_protected_resource(request):
    """OAuth stub - server nepouziva auth, Smithery ho hlada."""
    return JSONResponse({"resource": "https://cheap-flights-mcp-zp1q.onrender.com"})


async def oauth_authorization_server(request):
    """OAuth stub."""
    return JSONResponse({"issuer": "https://cheap-flights-mcp-zp1q.onrender.com"})


async def openid_configuration(request):
    """OpenID stub."""
    return JSONResponse({"issuer": "https://cheap-flights-mcp-zp1q.onrender.com"})


# Ziskaj MCP ASGI app
mcp_app = server_module.mcp.streamable_http_app()

# Starlette app: server-card + OAuth stubs + MCP na root aj /mcp
app = Starlette(
    routes=[
        Route("/.well-known/mcp/server-card.json", server_card_endpoint),
        Route("/.well-known/oauth-protected-resource", oauth_protected_resource),
        Route("/.well-known/oauth-authorization-server", oauth_authorization_server),
        Route("/.well-known/openid-configuration", openid_configuration),
        Route("/health", health),
        Mount("/mcp", mcp_app),
        Mount("/", mcp_app),
    ]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)