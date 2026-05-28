"""
Render.com startup script.
Spusti MCP server v streamable-http mode.
FastMCP automaticky cita PORT z env variable.
"""
import os
import sys
import importlib.util
from pathlib import Path

# Nastav environment PRED importom
os.environ["MCP_TRANSPORT"] = "streamable-http"

# FastMCP pouziva HOST a PORT env variables automaticky
# Render.com nastavi PORT, my nastavime HOST
os.environ.setdefault("HOST", "0.0.0.0")

# Cesty
project_root = Path(__file__).resolve().parent
mcp_server_dir = project_root / "mcp_server"

# Pridaj mcp_server dir do path (pre airlines import v server.py)
sys.path.insert(0, str(mcp_server_dir))

# Zmen working directory (server.py cita config.json cez Path(__file__).parent)
os.chdir(str(mcp_server_dir))

# Importuj server.py
spec = importlib.util.spec_from_file_location("server", str(mcp_server_dir / "server.py"))
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)

# Spusti MCP server - FastMCP cita PORT z env automaticky
server_module.mcp.run(transport="streamable-http")