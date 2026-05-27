"""
AI Agent pre hľadanie lacných leteniek.
Používa MCP server cez subprocess a Claude AI cez SAP AI Proxy.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Pridaj parent do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from agent.prompts import FLIGHT_AGENT_SYSTEM_PROMPT


class FlightAgent:
    """AI Agent pre hľadanie lacných leteniek s MCP tools."""

    def __init__(self):
        self.session = None
        self.base_url = os.environ.get("AI_PROXY_BASE_URL", "http://localhost:6655")
        self.api_key = os.environ.get("AI_PROXY_API_KEY", "")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
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

        # Načítaj dostupné tools
        tools_response = await self.session.list_tools()
        self.tools = tools_response.tools
        print(f"[Agent] Pripojený k MCP serveru. Dostupné tools: {[t.name for t in self.tools]}")

    async def disconnect(self):
        """Odpoj sa od MCP servera."""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._transport:
            await self._transport.__aexit__(None, None, None)

    def _get_tools_for_api(self) -> list[dict]:
        """Konvertuj MCP tools na formát pre Claude API."""
        api_tools = []
        for tool in self.tools:
            api_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            })
        return api_tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Zavolaj MCP tool."""
        result = await self.session.call_tool(tool_name, arguments)
        if result.content:
            return result.content[0].text
        return "No result"

    async def chat(self, user_message: str) -> str:
        """Spracuj správu od používateľa."""
        import httpx

        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Vyber API endpoint
        if self.api_key and self.base_url:
            # SAP AI Proxy
            api_url = f"{self.base_url}/v1/messages"
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }
        elif self.anthropic_key:
            # Priamy Anthropic API
            api_url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.anthropic_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }
        else:
            return "Chyba: Žiadny API kľúč nie je nastavený. Nastav AI_PROXY_API_KEY alebo ANTHROPIC_API_KEY v .env"

        # Volanie Claude API
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": FLIGHT_AGENT_SYSTEM_PROMPT,
            "tools": self._get_tools_for_api(),
            "messages": self.conversation_history,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)

            if response.status_code != 200:
                return f"API chyba ({response.status_code}): {response.text[:300]}"

            data = response.json()

        # Spracuj odpoveď - môže obsahovať tool_use
        assistant_message = {"role": "assistant", "content": data.get("content", [])}
        self.conversation_history.append(assistant_message)

        # Skontroluj či Claude chce volať tool
        final_text = ""
        tool_results = []

        for block in data.get("content", []):
            if block.get("type") == "text":
                final_text += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_name = block.get("name", "")
                tool_input = block.get("input", {})
                tool_id = block.get("id", "")

                print(f"[Agent] Volám tool: {tool_name}({json.dumps(tool_input, ensure_ascii=False)})")

                # Zavolaj MCP tool
                tool_result = await self.call_tool(tool_name, tool_input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": tool_result,
                })

        # Ak boli tool calls, pošli výsledky späť Claude-ovi
        if tool_results:
            self.conversation_history.append({
                "role": "user",
                "content": tool_results,
            })

            # Druhé volanie pre finálnu odpoveď
            payload["messages"] = self.conversation_history
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(api_url, json=payload, headers=headers)

                if response.status_code != 200:
                    return f"API chyba ({response.status_code}): {response.text[:300]}"

                data = response.json()

            assistant_message2 = {"role": "assistant", "content": data.get("content", [])}
            self.conversation_history.append(assistant_message2)

            final_text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    final_text += block.get("text", "")

        return final_text

    def reset_conversation(self):
        """Resetuj konverzáciu."""
        self.conversation_history = []


async def main():
    """Interaktívny CLI režim."""
    agent = FlightAgent()

    print("=" * 60)
    print("✈️  Flight Search AI Agent")
    print("=" * 60)
    print("Pripájam sa k MCP serveru...")

    try:
        await agent.connect_to_mcp()
    except Exception as e:
        print(f"Chyba pripojenia k MCP: {e}")
        print("Skontroluj či sú nainštalované závislosti: pip install -r requirements.txt")
        return

    print("\nPripravený! Pýtaj sa na letenky (napr. 'Nájdi najlacnejšiu letenku z Bratislavy do Londýna na 15.7.2026')")
    print("Príkazy: 'quit' = koniec, 'reset' = nová konverzácia\n")

    try:
        while True:
            user_input = input("Ty: ").strip()

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if user_input.lower() == "reset":
                agent.reset_conversation()
                print("[Konverzácia resetovaná]\n")
                continue

            print("Agent: ", end="", flush=True)
            response = await agent.chat(user_input)
            print(response)
            print()

    except KeyboardInterrupt:
        print("\n\nUkončujem...")
    finally:
        await agent.disconnect()
        print("Odpojený od MCP servera.")


if __name__ == "__main__":
    asyncio.run(main())