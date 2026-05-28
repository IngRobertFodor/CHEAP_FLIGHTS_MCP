"""
Render.com startup script.
Spusti MCP server v streamable-http mode.
FastMCP.run() prijima LEN transport parameter.
Port sa nastavi cez uvicorn konfiguraciu.
"""
import os
import sys
import importlib.util
import uvicorn
from pathlib import Path

# Render.com nastavi PORT env variable
port = int(os.environ.get("PORT", "10000"))

# Nastav MCP env
os.environ["MCP_TRANSPORT"] = "streamable-http"

# Cesty
project_root = Path(__file__).resolve().parent
mcp_server_dir = project_root / "mcp_server"

# Pridaj mcp_server dir do path
sys.path.insert(0, str(mcp_server_dir))

# Zmen working directory
os.chdir(str(mcp_server_dir))

# Importuj server.py - toto vytvori mcp instanciu a zaregistruje tools
spec = importlib.util.spec_from_file_location("server", str(mcp_server_dir / "server.py"))
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)

# Ziskaj ASGI app z FastMCP pre streamable-http
# FastMCP.run() interne spusta uvicorn s vlastnym portom (8000)
# My musime spustit uvicorn priamo s Render portom
app = server_module.mcp.streamable_http_app()

# Spusti uvicorn s Render.com PORT
uvicorn.run(app, host="0.0.0.0", port=port)