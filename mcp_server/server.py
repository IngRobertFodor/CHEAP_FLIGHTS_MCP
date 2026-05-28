"""
MCP Server pre vyhladavanie lacnych leteniek.
Pouziva moderny FastMCP pattern + asyncio.gather pre paralelne volanie airlines.
Podporuje stdio (lokalne) aj streamable-http (Smithery/remote) transport.
"""

import json
import os
import sys
import asyncio
from datetime import date
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent))

from airlines import (
    FlightSearchRequest,
    RyanairAdapter,
    WizzairAdapter,
    GoogleFlightsAdapter,
)

CONFIG_PATH = Path(__file__).parent / "config.json"
ENV_PATH = Path(__file__).parent.parent / ".env"


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)


def load_env():
    if ENV_PATH.exists():
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def get_airline_adapters(config: dict) -> dict:
    """Vytvor adaptery pre aktivne letecke spolocnosti."""
    adapters = {}
    currency = config.get("default_currency", "EUR")
    active = config.get("active_airlines", [])

    for airline_code in active:
        try:
            if airline_code == "ryanair":
                adapters["ryanair"] = RyanairAdapter(currency=currency)
            elif airline_code == "wizzair":
                adapters["wizzair"] = WizzairAdapter(currency=currency)
            elif airline_code == "google_flights":
                adapters["google_flights"] = GoogleFlightsAdapter(currency=currency)
        except ImportError as e:
            print(f"[Server] Cannot load {airline_code}: {e}", file=sys.stderr)

    return adapters


load_env()
mcp = FastMCP("flight-search")


@mcp.tool()
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = "",
    adults: int = 1,
    flexible_dates: bool = False,
) -> str:
    """Vyhladaj lety medzi dvoma letiskami. Vrati najlacnejsie lety zo vsetkych aktivnych leteckych spolocnosti.

    Args:
        origin: IATA kod odletoveho letiska (napr. BTS, VIE, BUD)
        destination: IATA kod cieloveho letiska (napr. STN, LTN, BCN)
        departure_date: Datum odletu vo formate YYYY-MM-DD
        return_date: Datum navratu vo formate YYYY-MM-DD (volitelne)
        adults: Pocet dospelych cestujucich (default 1)
        flexible_dates: Hladat +/- 3 dni (default False)
    """
    config = load_config()

    try:
        dep_date = date.fromisoformat(departure_date)
    except ValueError:
        return json.dumps({"error": f"Neplatny datum odletu: {departure_date}. Pouzi format YYYY-MM-DD."})

    ret_date = None
    if return_date:
        try:
            ret_date = date.fromisoformat(return_date)
        except ValueError:
            return json.dumps({"error": f"Neplatny datum navratu: {return_date}. Pouzi format YYYY-MM-DD."})

    request = FlightSearchRequest(
        origin=origin.upper(),
        destination=destination.upper(),
        departure_date=dep_date,
        return_date=ret_date,
        adults=adults,
        max_results=config.get("max_results_per_airline", 10),
        flexible_dates=flexible_dates,
    )

    adapters = get_airline_adapters(config)

    # PARALELNE volanie vsetkych airlines naraz
    tasks = [adapter.search_flights(request) for adapter in adapters.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_outbound = []
    all_return = []
    errors = []

    for result in results:
        if isinstance(result, Exception):
            errors.append(str(result))
        else:
            result_dict = result.to_dict()
            all_outbound.extend(result_dict.get("outbound_flights", []))
            all_return.extend(result_dict.get("return_flights", []))
            if result_dict.get("error"):
                errors.append(result_dict["error"])

    all_outbound.sort(key=lambda x: x.get("price", 9999))
    all_return.sort(key=lambda x: x.get("price", 9999))

    response = {
        "search": {
            "origin": origin.upper(),
            "destination": destination.upper(),
            "departure_date": departure_date,
            "return_date": return_date,
            "adults": adults,
        },
        "outbound_flights": all_outbound,
        "return_flights": all_return,
        "total_outbound": len(all_outbound),
        "total_return": len(all_return),
        "errors": errors,
    }

    return json.dumps(response, indent=2, ensure_ascii=False)


@mcp.tool()
async def list_active_airlines() -> str:
    """Zobraz zoznam aktualne aktivnych leteckych spolocnosti."""
    config = load_config()
    return json.dumps({
        "active_airlines": config.get("active_airlines", []),
        "available_airlines": config.get("available_airlines", []),
    }, indent=2)


@mcp.tool()
async def add_airline(airline_code: str) -> str:
    """Pridaj letecku spolocnost do aktivneho zoznamu.

    Args:
        airline_code: Kod spolocnosti (ryanair, wizzair, google_flights)
    """
    config = load_config()
    code = airline_code.lower()

    if code not in config.get("available_airlines", []):
        return f"Neznama spolocnost: {code}. Dostupne: {config['available_airlines']}"
    if code in config.get("active_airlines", []):
        return f"'{code}' je uz aktivna."

    config["active_airlines"].append(code)
    save_config(config)
    return f"'{code}' bola pridana. Aktivne: {config['active_airlines']}"


@mcp.tool()
async def remove_airline(airline_code: str) -> str:
    """Odober letecku spolocnost z aktivneho zoznamu.

    Args:
        airline_code: Kod spolocnosti (ryanair, wizzair, google_flights)
    """
    config = load_config()
    code = airline_code.lower()

    if code not in config.get("active_airlines", []):
        return f"'{code}' nie je v aktivnom zozname. Aktivne: {config['active_airlines']}"

    config["active_airlines"].remove(code)
    save_config(config)
    return f"'{code}' bola odobrata. Aktivne: {config['active_airlines']}"


@mcp.tool()
async def get_destinations(origin: str) -> str:
    """Ziskaj zoznam dostupnych destinacii z daneho letiska.

    Args:
        origin: IATA kod letiska (napr. BTS)
    """
    config = load_config()
    adapters = get_airline_adapters(config)

    tasks = [adapter.get_destinations(origin.upper()) for adapter in adapters.values()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_destinations = {}
    adapter_names = list(adapters.keys())

    for i, dests in enumerate(results):
        if isinstance(dests, Exception):
            continue
        airline_code = adapter_names[i]
        for d in dests:
            dest_code = d.get("code", "")
            if dest_code and dest_code not in all_destinations:
                all_destinations[dest_code] = d
                all_destinations[dest_code]["airlines"] = [airline_code]
            elif dest_code in all_destinations:
                all_destinations[dest_code]["airlines"].append(airline_code)

    return json.dumps({
        "origin": origin.upper(),
        "destinations": list(all_destinations.values()),
        "total": len(all_destinations),
    }, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Rozhodnutie: stdio (lokalne) vs http (remote/Smithery)
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "streamable-http":
        # HTTP transport pre Render.com / Smithery
        # FastMCP cita HOST a PORT z env automaticky
        os.environ.setdefault("HOST", "0.0.0.0")
        mcp.run(transport="streamable-http")
    else:
        # Default: stdio transport pre lokalne pouzitie
        mcp.run()