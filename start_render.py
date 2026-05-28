"""
Render.com startup script.
Spusti MCP server s host/port z env + server-card.json endpoint.
FastMCP konstruktor prijima host a port priamo.
"""
import os
import sys
from pathlib import Path

# Render.com PORT
port = os.environ.get("PORT", "10000")

# Nastav env pre MCP transport
os.environ["MCP_TRANSPORT"] = "streamable-http"
os.environ["FASTMCP_HOST"] = "0.0.0.0"
os.environ["FASTMCP_PORT"] = port

# Cesty
project_root = Path(__file__).resolve().parent
mcp_server_dir = project_root / "mcp_server"
sys.path.insert(0, str(mcp_server_dir))
os.chdir(str(mcp_server_dir))

# Importuj a spusti server.py ako __main__
import runpy
runpy.run_path(str(mcp_server_dir / "server.py"), run_name="__main__")