"""
AI Agent pre hladanie lacnych leteniek.
Pouziva MCP server + SAP Hyperspace AI Proxy (Anthropic-compatible endpoint).
Endpoint: http://localhost:6655/anthropic/v1/messages
Model: anthropic--claude-sonnet-latest
Podporuje parallel tool calling (asyncio.gather).
Sliding window: max 20 sprav v historii (prevencia token limitu).
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from agent.prompts import FLIGHT_AGENT_SYSTEM_PROMPT

# Konstanty
MAX_HISTORY_MESSAGES = 20  # Sliding window - max sprav v historii
MAX_CLI_INPUT_LENGTH = 1000  # Max dlzka vstupu od pouzivatela
MAX_TOOL_ITERATIONS = 5  # Max pocet tool-calling iteracii


class FlightAgent:
    """AI Agent pre hladanie lacnych leteniek s MCP tools."""

    def __init__(self):
        self.session = None
        self.base_url = os.environ.get("AI_PROXY_BASE_URL", "http://localhost:6655")
        self.api_key = os.environ.get("AI_PROXY_API_KEY", "")
        self.model = "anthropic--claude-sonnet-latest"
        self.tools = []
        self.conversation_history = []

    async def connect_to_mcp(self):
        """Pripoj sa k MCP serveru."""
        server_path = str(Path(__file__).parent.parent / "mcp_server" / "server.py")
        server_params = StdioServerParameters(
            command="python",
            args=[server_path],
        )

        self._transport = stdio_client(server_params)
        self._read, self._write = await self._transport.__aenter__()
        self.session = ClientSession(self._read, self._write)
        await self.session.__aenter__()
        await self.session.initialize()

        tools_response = await self.session.list_tools()
        self.tools = tools_response.tools
        print(f"[Agent] Pripojeny k MCP serveru. Dostupne tools: {[t.name for t in self.tools]}")

    async def disconnect(self):
        """Odpoj sa od MCP servera."""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._transport:
            await self._transport.__aexit__(None, None, None)

    def _get_tools_for_api(self) -> list[dict]:
        """Konvertuj MCP tools na Anthropic tool format."""
        api_tools = []
        for tool in self.tools:
            api_tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema or {"type": "object", "properties": {}},
            })
        return api_tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Zavolaj MCP tool."""
        result = await self.session.call_tool(tool_name, arguments)
        if result.content:
            return result.content[0].text
        return "No result"

    def _trim_history(self):
        """Sliding window - orez historiu ak prekroci limit."""
        if len(self.conversation_history) > MAX_HISTORY_MESSAGES:
            # Zachovaj poslednych N sprav
            self.conversation_history = self.conversation_history[-MAX_HISTORY_MESSAGES:]

    async def _call_api(self, messages: list) -> dict:
        """Zavolaj SAP Hyperspace Anthropic API."""
        api_url = f"{self.base_url}/anthropic/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": FLIGHT_AGENT_SYSTEM_PROMPT,
            "tools": self._get_tools_for_api(),
            "messages": messages,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)

            if response.status_code != 200:
                raise Exception(f"API chyba ({response.status_code}): {response.text[:500]}")

            return response.json()

    async def chat(self, user_message: str) -> str:
        """Spracuj spravu s podporou parallel tool calling + sliding window."""
        # Orez vstup
        user_message = user_message[:MAX_CLI_INPUT_LENGTH]

        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Trim history pred volanim API
        self._trim_history()

        try:
            for _ in range(MAX_TOOL_ITERATIONS):
                data = await self._call_api(self.conversation_history)

                content_blocks = data.get("content", [])
                self.conversation_history.append({
                    "role": "assistant",
                    "content": content_blocks
                })

                tool_use_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]

                if not tool_use_blocks:
                    final_text = ""
                    for block in content_blocks:
                        if block.get("type") == "text":
                            final_text += block.get("text", "")
                    return final_text

                # Parallel tool execution
                async def execute_tool(block):
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})
                    tool_id = block.get("id", "")
                    print(f"[Agent] Volam tool: {tool_name}({json.dumps(tool_input, ensure_ascii=False)})")
                    result = await self.call_tool(tool_name, tool_input)
                    return {
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result,
                    }

                tool_results = await asyncio.gather(
                    *[execute_tool(block) for block in tool_use_blocks]
                )

                self.conversation_history.append({
                    "role": "user",
                    "content": list(tool_results),
                })

            return "Dosiahnuty maximalny pocet iteracii. Skus zjednodusit otazku."

        except Exception as e:
            error_msg = str(e)
            if "tool_use" in error_msg and "tool_result" in error_msg:
                # Vycisti problematicku historiu
                self.conversation_history = [
                    msg for msg in self.conversation_history
                    if not (isinstance(msg.get("content"), list) and
                            any(b.get("type") == "tool_use" for b in msg.get("content", []) if isinstance(b, dict)))
                ]
                return "Nastala chyba v konverzacii. Historia bola vycistena. Skus znova."
            if "ConnectError" in error_msg or "connection" in error_msg.lower():
                return f"Chyba: Nemozem sa pripojit k SAP Hyperspace Proxy na {self.base_url}."
            return f"AI chyba: {error_msg}"

    def reset_conversation(self):
        """Resetuj konverzaciu."""
        self.conversation_history = []


async def main():
    """Interaktivny CLI rezim."""
    agent = FlightAgent()

    print("=" * 60)
    print("  Flight Search AI Agent (SAP Hyperspace)")
    print("=" * 60)
    print("Pripajam sa k MCP serveru...")

    try:
        await agent.connect_to_mcp()
    except Exception as e:
        print(f"Chyba pripojenia k MCP: {e}")
        print("Skontroluj ci su nainstalovane zavislosti: pip install -r requirements.txt")
        return

    print(f"Model: {agent.model}")
    print("\nPripraveny! Pytaj sa na letenky.")
    print("Prikazy: 'quit' = koniec, 'reset' = nova konverzacia\n")

    try:
        while True:
            user_input = input("Ty: ").strip()

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if user_input.lower() == "reset":
                agent.reset_conversation()
                print("[Konverzacia resetovana]\n")
                continue

            # Max dlzka CLI vstupu
            if len(user_input) > MAX_CLI_INPUT_LENGTH:
                print(f"[Vstup orezany na {MAX_CLI_INPUT_LENGTH} znakov]")
                user_input = user_input[:MAX_CLI_INPUT_LENGTH]

            print("Agent: ", end="", flush=True)
            response = await agent.chat(user_input)
            print(response)
            print()

    except KeyboardInterrupt:
        print("\n\nUkoncujem...")
    finally:
        await agent.disconnect()
        print("Odpojeny od MCP servera.")


if __name__ == "__main__":
    asyncio.run(main())