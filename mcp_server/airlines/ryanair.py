"""
RyanAir adapter - vyuziva kniznicu ryanair-py pre pristup k RyanAir API.
Deep link: priamo na vysledky vyhladavania na ryanair.com
get_destinations: pouziva oficialny RyanAir routes endpoint (vsetky linky).
POZOR: Vsetky logy idu do stderr (stdout je pre MCP komunikaciu).
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Optional

import httpx

from .base_airline import BaseAirline, Flight, FlightSearchRequest, FlightSearchResult

try:
    from ryanair import Ryanair
    RYANAIR_AVAILABLE = True
except ImportError:
    RYANAIR_AVAILABLE = False

RYANAIR_ROUTES_URL = "https://www.ryanair.com/api/views/locate/searchWidget/routes/en/airport/{}"


def _log(msg: str):
    """Log do stderr (stdout je pre MCP)."""
    print(msg, file=sys.stderr)


class RyanairAdapter(BaseAirline):
    """Adapter pre RyanAir vyuzivajuci ryanair-py kniznicu."""

    @property
    def name(self) -> str:
        return "Ryanair"

    @property
    def code(self) -> str:
        return "ryanair"

    def __init__(self, currency: str = "EUR"):
        if not RYANAIR_AVAILABLE:
            raise ImportError(
                "Kniznica 'ryanair-py' nie je nainstalovana. "
                "Spusti: pip install ryanair-py"
            )
        self.currency = currency
        self.api = Ryanair(currency)

    async def search_flights(self, request: FlightSearchRequest) -> FlightSearchResult:
        result = FlightSearchResult(
            airline=self.name,
            search_timestamp=self._get_timestamp()
        )

        try:
            loop = asyncio.get_running_loop()

            outbound = await loop.run_in_executor(
                None, self._search_one_way,
                request.origin, request.destination,
                request.departure_date, request.flexible_dates, request.max_results
            )
            result.outbound_flights = outbound

            if request.return_date:
                return_flights = await loop.run_in_executor(
                    None, self._search_one_way,
                    request.destination, request.origin,
                    request.return_date, request.flexible_dates, request.max_results
                )
                result.return_flights = return_flights

        except Exception as e:
            result.error = f"RyanAir search error: {str(e)}"

        return result

    def _search_one_way(self, origin, destination, flight_date, flexible, max_results):
        flights = []

        try:
            if flexible:
                date_from = flight_date - timedelta(days=3)
                date_to = flight_date + timedelta(days=3)
            else:
                date_from = flight_date
                date_to = flight_date

            trips = self.api.get_cheapest_flights(
                airport=origin,
                date_from=date_from,
                date_to=date_to,
                destination_airport=destination
            )

            if trips:
                for trip in trips[:max_results]:
                    flight = self._convert_trip(trip)
                    if flight:
                        flights.append(flight)

        except Exception as e:
            _log(f"[RyanAir] Error searching {origin}->{destination}: {e}")

        return flights

    def _convert_trip(self, trip) -> Optional[Flight]:
        try:
            departure = getattr(trip, 'departureTime', None) or getattr(trip, 'departure_time', None)
            arrival = getattr(trip, 'arrivalTime', None) or getattr(trip, 'arrival_time', None)

            if isinstance(departure, str):
                departure = datetime.fromisoformat(departure)
            if isinstance(arrival, str):
                arrival = datetime.fromisoformat(arrival)

            price = getattr(trip, 'price', 0) or getattr(trip, 'totalPrice', 0)
            origin = getattr(trip, 'origin', '') or getattr(trip, 'originFull', '')
            destination = getattr(trip, 'destination', '') or getattr(trip, 'destinationFull', '')
            flight_number = getattr(trip, 'flightNumber', f"FR-{origin}-{destination}")

            duration = 0
            if departure and arrival:
                duration = int((arrival - departure).total_seconds() / 60)

            orig_code = str(origin)[:3].upper()
            dest_code = str(destination)[:3].upper()
            dep_date_str = departure.strftime("%Y-%m-%d") if departure else ""

            booking_url = (
                f"https://www.ryanair.com/sk/sk/trip/flights/select"
                f"?adults=1&dateOut={dep_date_str}&isReturn=false"
                f"&originIata={orig_code}&destinationIata={dest_code}"
            )

            return Flight(
                airline="Ryanair",
                flight_number=str(flight_number),
                origin=orig_code,
                destination=dest_code,
                departure_time=departure or datetime.now(),
                arrival_time=arrival or datetime.now(),
                price=float(price) if price else 0.0,
                currency=self.currency,
                direct=True,
                duration_minutes=duration,
                origin_city=getattr(trip, 'originFull', ''),
                destination_city=getattr(trip, 'destinationFull', ''),
                booking_url=booking_url,
            )
        except Exception as e:
            _log(f"[RyanAir] Error converting trip: {e}")
            return None

    async def get_destinations(self, origin: str) -> list[dict]:
        """Kompletny zoznam destinacii (vratane sezonnych) cez Routes API."""
        try:
            url = RYANAIR_ROUTES_URL.format(origin.upper())
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0"
                })

                if resp.status_code == 200:
                    data = resp.json()
                    destinations = []
                    for route in data:
                        arrival = route.get("arrivalAirport", {})
                        dest_code = arrival.get("iataCode", "")
                        dest_name = arrival.get("name", "")
                        country = arrival.get("countryName", "")

                        if dest_code:
                            destinations.append({
                                "code": dest_code,
                                "city": dest_name,
                                "country": country
                            })
                    return destinations

        except Exception as e:
            _log(f"[RyanAir] Routes API error: {e}")

        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._get_destinations_fallback, origin)
        except Exception as e:
            _log(f"[RyanAir] Fallback error: {e}")
            return []

    def _get_destinations_fallback(self, origin: str) -> list[dict]:
        try:
            from datetime import date
            today = date.today()
            date_to = today + timedelta(days=90)

            trips = self.api.get_cheapest_flights(
                airport=origin, date_from=today, date_to=date_to
            )

            destinations = {}
            if trips:
                for trip in trips:
                    dest = getattr(trip, 'destination', '')
                    dest_city = getattr(trip, 'destinationFull', str(dest))
                    if dest and dest not in destinations:
                        destinations[dest] = {
                            "code": str(dest)[:3].upper(),
                            "city": str(dest_city),
                            "country": ""
                        }

            return list(destinations.values())
        except Exception as e:
            _log(f"[RyanAir] Fallback error: {e}")
            return []