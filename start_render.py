"""
Render.com startup script.
Spusti MCP server cez mcp.run() s FASTMCP env variables pre port/host.
"""
import os
import sys
from pathlib import Path

# Render.com PORT
port = os.environ.get("PORT", "10000")

# FastMCP interne pouziva tieto env variables pre uvicorn
os.environ["FASTMCP_PORT"] = port
os.environ["FASTMCP_HOST"] = "0.0.0.0"
os.environ["MCP_TRANSPORT"] = "streamable-http"

# Cesty
project_root = Path(__file__).resolve().parent
mcp_server_dir = project_root / "mcp_server"
sys.path.insert(0, str(mcp_server_dir))
os.chdir(str(mcp_server_dir))

# Spusti server.py priamo (on ma if __name__ == "__main__" s mcp.run())
# Nastavime __name__ aby sa spustil main blok
import runpy
runpy.run_path(str(mcp_server_dir / "server.py"), run_name="__main__")