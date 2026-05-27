"""Quick test - flight search via RyanAir and WizzAir."""
import sys
import os
import asyncio
from pathlib import Path
from datetime import date

# Fix encoding on Windows
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))

from airlines import FlightSearchRequest, RyanairAdapter, WizzairAdapter


async def test():
    print("=" * 50)
    print("TEST: Flight search BTS -> STN (15.7.2026)")
    print("=" * 50)

    # Test RyanAir
    print("\n--- RyanAir ---")
    try:
        ryanair = RyanairAdapter()
        req = FlightSearchRequest(
            origin="BTS",
            destination="STN",
            departure_date=date(2026, 7, 15)
        )
        result = await ryanair.search_flights(req)
        print(f"Flights found: {len(result.outbound_flights)}")
        if result.error:
            print(f"Error: {result.error}")
        for f in result.outbound_flights[:3]:
            print(f"  {f.price} {f.currency} | {f.origin}->{f.destination} | {f.departure_time}")
    except Exception as e:
        print(f"RyanAir error: {e}")

    # Test WizzAir
    print("\n--- WizzAir ---")
    try:
        wizzair = WizzairAdapter()
        req = FlightSearchRequest(
            origin="BTS",
            destination="LTN",
            departure_date=date(2026, 7, 15)
        )
        result = await wizzair.search_flights(req)
        print(f"Flights found: {len(result.outbound_flights)}")
        if result.error:
            print(f"Error: {result.error}")
        for f in result.outbound_flights[:3]:
            print(f"  {f.price} {f.currency} | {f.origin}->{f.destination} | {f.departure_time}")
    except Exception as e:
        print(f"WizzAir error: {e}")

    print("\nTest done!")


if __name__ == "__main__":
    asyncio.run(test())