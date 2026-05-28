"""
Render.com startup script.
Spusti MCP server v streamable-http mode na Render.com PORT.
"""
import os
import sys
import importlib.util
from pathlib import Path

# Render.com nastavi PORT env variable
port = int(os.environ.get("PORT", "10000"))

# Nastav MCP env
os.environ["MCP_TRANSPORT"] = "streamable-http"
os.environ["UVICORN_HOST"] = "0.0.0.0"
os.environ["UVICORN_PORT"] = str(port)

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

# Spusti MCP server s explicitnym portom
server_module.mcp.run(transport="streamable-http", port=port)