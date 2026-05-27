"""
Automaticky test AI agenta s roznymi use cases.
Spustenie: python test_agent_prompts.py
Vyzaduje: SAP Hyperspace AI Proxy na localhost:6655
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from agent.flight_agent import FlightAgent

# Test prompty - rozne use cases
TEST_PROMPTS = [
    {
        "id": 1,
        "name": "Zakladne vyhladavanie",
        "prompt": "Najdi najlacnejsi let z BTS do STN na 15.7.2026.",
        "expect_tool": True,
    },
    {
        "id": 2,
        "name": "Spiatocny let",
        "prompt": "Najdi spiatocnu letenku z Bratislavy do Londyna, odlet 1.6.2026, navrat 4.6.2026, pre 2 dospelych.",
        "expect_tool": True,
    },
    {
        "id": 3,
        "name": "Flexibilne datumy",
        "prompt": "Aka je najlacnejsia letenka z BTS do BCN v juli 2026?",
        "expect_tool": True,
    },
    {
        "id": 4,
        "name": "Destinacie z BTS",
        "prompt": "Ake destinacie su dostupne z BTS cez RyanAir?",
        "expect_tool": True,
    },
    {
        "id": 5,
        "name": "Porovnanie cien",
        "prompt": "Porovnaj ceny z BTS do STN na 10.7.2026 pre 1 osobu.",
        "expect_tool": True,
    },
    {
        "id": 6,
        "name": "Vikendovy vylet",
        "prompt": "Chcem ist na vikend z BTS do Rimu (CIA) 20-22.6.2026, pre 2 ludi. Najdi najlacnejsiu moznost.",
        "expect_tool": True,
    },
    {
        "id": 7,
        "name": "Zoznam airlines",
        "prompt": "Ake letecke spolocnosti su prave aktivne?",
        "expect_tool": True,
    },
    {
        "id": 8,
        "name": "Jednoduchy one-way",
        "prompt": "Najdi one-way let BTS do DUB (Dublin) na 5.8.2026.",
        "expect_tool": True,
    },
]


async def run_tests():
    """Spusti vsetky testy."""
    agent = FlightAgent()

    print("=" * 70)
    print("  FLIGHT AGENT - AUTOMATED TEST")
    print("=" * 70)
    print("Pripajam sa k MCP serveru...")

    try:
        await agent.connect_to_mcp()
    except Exception as e:
        print(f"FATAL: Nemozem sa pripojit k MCP: {e}")
        return

    print(f"Model: {agent.model}")
    print(f"Pocet testov: {len(TEST_PROMPTS)}")
    print("=" * 70)

    results = []

    for test in TEST_PROMPTS:
        print(f"\n--- Test {test['id']}: {test['name']} ---")
        print(f"Prompt: {test['prompt']}")
        print(f"Agent: ", end="", flush=True)

        # Reset konverzacie pred kazdym testom
        agent.reset_conversation()

        try:
            response = await agent.chat(test["prompt"])
            print(response[:300] + ("..." if len(response) > 300 else ""))

            # Vyhodnotenie
            passed = True
            reason = ""

            if not response:
                passed = False
                reason = "Prazdna odpoved"
            elif "API chyba" in response:
                passed = False
                reason = "API chyba"
            elif "ValidationError" in response:
                passed = False
                reason = "Validation error"
            elif "Chyba" in response and "pripojit" in response:
                passed = False
                reason = "Connection error"

            results.append({
                "id": test["id"],
                "name": test["name"],
                "passed": passed,
                "reason": reason,
            })

            status = "PASS" if passed else f"FAIL ({reason})"
            print(f"\nResult: {status}")

        except Exception as e:
            print(f"\nException: {e}")
            results.append({
                "id": test["id"],
                "name": test["name"],
                "passed": False,
                "reason": str(e)[:100],
            })

    # Sumar
    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for r in results if r["passed"])
    failed_count = sum(1 for r in results if not r["passed"])

    for r in results:
        status = "PASS" if r["passed"] else f"FAIL: {r['reason']}"
        print(f"  [{status:40}] Test {r['id']}: {r['name']}")

    print(f"\n  Total: {len(results)} | Passed: {passed_count} | Failed: {failed_count}")
    print("=" * 70)

    await agent.disconnect()


if __name__ == "__main__":
    asyncio.run(run_tests())