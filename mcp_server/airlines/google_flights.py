"""
Google Flights adapter - vyuziva fast-flights kniznicu.
Zadarmo, bez API kluca, real-time data z Google Flights.
Obsahuje USD->EUR konverziu (live kurz).
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import httpx

from .base_airline import BaseAirline, Flight, FlightSearchRequest, FlightSearchResult

try:
    from fast_flights import FlightData, Passengers, create_filter, get_flights
    FAST_FLIGHTS_AVAILABLE = True
except ImportError:
    FAST_FLIGHTS_AVAILABLE = False

# Fallback kurz ak API nefunguje
FALLBACK_USD_TO_EUR = 0.92


async def get_usd_to_eur_rate() -> float:
    """Ziskaj aktualny USD->EUR kurz z free API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("https://api.frankfurter.app/latest?from=USD&to=EUR")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("rates", {}).get("EUR", FALLBACK_USD_TO_EUR)
    except Exception:
        pass
    return FALLBACK_USD_TO_EUR


class GoogleFlightsAdapter(BaseAirline):
    """Adapter pre Google Flights cez fast-flights kniznicu."""

    @property
    def name(self) -> str:
        return "Google Flights"

    @property
    def code(self) -> str:
        return "google_flights"

    def __init__(self, currency: str = "EUR"):
        if not FAST_FLIGHTS_AVAILABLE:
            raise ImportError(
                "Kniznica 'fast-flights' nie je nainstalovana. "
                "Spusti: pip install fast-flights"
            )
        self.currency = currency

    async def search_flights(self, request: FlightSearchRequest) -> FlightSearchResult:
        """Vyhladaj lety cez Google Flights."""
        result = FlightSearchResult(
            airline=self.name,
            search_timestamp=self._get_timestamp()
        )

        try:
            # Ziskaj aktualny kurz
            usd_to_eur = await get_usd_to_eur_rate()

            loop = asyncio.get_running_loop()
            outbound = await loop.run_in_executor(
                None,
                self._search_sync,
                request.origin,
                request.destination,
                request.departure_date,
                request.adults,
                request.max_results,
                usd_to_eur
            )
            result.outbound_flights = outbound

            if request.return_date:
                returns = await loop.run_in_executor(
                    None,
                    self._search_sync,
                    request.destination,
                    request.origin,
                    request.return_date,
                    request.adults,
                    request.max_results,
                    usd_to_eur
                )
                result.return_flights = returns

        except Exception as e:
            result.error = f"Google Flights error: {str(e)}"

        return result

    def _search_sync(self, origin, destination, flight_date, adults, max_results, usd_to_eur):
        """Synchronne vyhladavanie cez fast-flights."""
        flights = []

        try:
            date_str = flight_date.strftime("%Y-%m-%d")

            flight_filter = create_filter(
                flight_data=[
                    FlightData(
                        date=date_str,
                        from_airport=origin.upper(),
                        to_airport=destination.upper(),
                    )
                ],
                trip="one-way",
                passengers=Passengers(adults=adults),
            )

            result = get_flights(flight_filter)

            if result and result.flights:
                for i, flight in enumerate(result.flights[:max_results]):
                    try:
                        # Parse cenu
                        price_usd = 0
                        if hasattr(flight, 'price') and flight.price:
                            price_str = str(flight.price).replace('$', '').replace(',', '').replace(' ', '')
                            try:
                                price_usd = float(price_str)
                            except ValueError:
                                price_usd = 0

                        # Konverzia USD -> EUR
                        price_eur = round(price_usd * usd_to_eur, 2)

                        dep_time = datetime.now()
                        arr_time = datetime.now() + timedelta(hours=2)

                        if hasattr(flight, 'departure') and flight.departure:
                            try:
                                dep_time = datetime.fromisoformat(str(flight.departure))
                            except (ValueError, TypeError):
                                pass

                        if hasattr(flight, 'arrival') and flight.arrival:
                            try:
                                arr_time = datetime.fromisoformat(str(flight.arrival))
                            except (ValueError, TypeError):
                                arr_time = dep_time + timedelta(hours=2)

                        airline_name = "Google Flights"
                        if hasattr(flight, 'name') and flight.name:
                            airline_name = f"Google ({flight.name})"

                        duration = 0
                        if hasattr(flight, 'duration') and flight.duration:
                            try:
                                duration = int(flight.duration)
                            except (ValueError, TypeError):
                                duration = 0

                        # Google Flights deep link (OVERENY)
                        booking_url = f"https://www.google.com/travel/flights?q=flights+{origin}+{destination}+{date_str}"

                        if price_usd > 0:
                            flights.append(Flight(
                                airline=airline_name,
                                flight_number=f"GF-{i+1}",
                                origin=origin.upper(),
                                destination=destination.upper(),
                                departure_time=dep_time,
                                arrival_time=arr_time,
                                price=price_eur,
                                currency="EUR",
                                direct=True,
                                duration_minutes=duration,
                                origin_city=f"${price_usd} USD",
                                destination_city="",
                                booking_url=booking_url,
                            ))
                    except Exception as e:
                        print(f"[GoogleFlights] Parse error: {e}")
                        continue

        except Exception as e:
            print(f"[GoogleFlights] Search error: {e}")

        return flights

    async def get_destinations(self, origin: str) -> list[dict]:
        """Google Flights nepodporuje zoznam destinacii priamo."""
        return []