"""
WizzAir adapter - neoficialne WizzAir JSON API s retry mechanizmom.
Deep link: priamo na vysledky vyhladavania na wizzair.com
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result

from .base_airline import BaseAirline, Flight, FlightSearchRequest, FlightSearchResult

WIZZAIR_METADATA_URL = "https://wizzair.com/static_fe/metadata.json"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
]


def _build_wizzair_booking_url(origin: str, destination: str, date_str: str, adults: int = 1) -> str:
    """Zostav OVERENY WizzAir deep link."""
    return (
        f"https://wizzair.com/sk-sk/booking/select-flight/"
        f"{origin.upper()}/{destination.upper()}/{date_str}/null/{adults}/0/0/null#/"
    )


class WizzairAdapter(BaseAirline):
    """Adapter pre WizzAir s retry a User-Agent rotaciou."""

    @property
    def name(self) -> str:
        return "Wizz Air"

    @property
    def code(self) -> str:
        return "wizzair"

    def __init__(self, currency: str = "EUR"):
        self.currency = currency
        self._api_base = "https://be.wizzair.com/19.1/Api"

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-GB,en;q=0.9",
            "Origin": "https://wizzair.com",
            "Referer": "https://wizzair.com/",
        }

    async def _get_api_url(self) -> str:
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(
                    WIZZAIR_METADATA_URL,
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._api_base = data.get("apiUrl", self._api_base)
        except Exception as e:
            print(f"[WizzAir] Could not fetch metadata: {e}")
        return self._api_base

    async def search_flights(self, request: FlightSearchRequest) -> FlightSearchResult:
        result = FlightSearchResult(
            airline=self.name,
            search_timestamp=self._get_timestamp()
        )

        try:
            await self._get_api_url()
            outbound, returns = await self._search_with_retry(request)
            result.outbound_flights = outbound
            result.return_flights = returns
        except Exception as e:
            result.error = f"WizzAir search error: {str(e)}"

        return result

    async def _search_with_retry(self, request: FlightSearchRequest) -> tuple:
        outbound_flights = []
        return_flights = []

        payload = {
            "flightList": [
                {
                    "departureStation": request.origin.upper(),
                    "arrivalStation": request.destination.upper(),
                    "departureDate": request.departure_date.isoformat(),
                }
            ],
            "adultCount": request.adults,
            "childCount": 0,
            "infantCount": 0,
            "wdc": False,
            "isRescueFare": False,
        }

        if request.return_date:
            payload["flightList"].append({
                "departureStation": request.destination.upper(),
                "arrivalStation": request.origin.upper(),
                "departureDate": request.return_date.isoformat(),
            })

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(0.5, 1.5)
                    print(f"[WizzAir] Retry {attempt}/{max_retries}, waiting {delay:.1f}s...")
                    await asyncio.sleep(delay)

                async with httpx.AsyncClient(follow_redirects=True) as client:
                    resp = await client.post(
                        f"{self._api_base}/search/search",
                        json=payload,
                        headers=self._get_headers(),
                        timeout=15.0
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        outbound_flights = self._parse_flights(
                            data, "outboundFlights", request.origin, request.destination,
                            request.departure_date.isoformat(), request.adults
                        )
                        if request.return_date:
                            return_flights = self._parse_flights(
                                data, "returnFlights", request.destination, request.origin,
                                request.return_date.isoformat(), request.adults
                            )
                        return outbound_flights, return_flights

                    elif resp.status_code == 429:
                        print(f"[WizzAir] Rate limited (429), attempt {attempt + 1}/{max_retries}")
                        continue

                    else:
                        print(f"[WizzAir] Status {resp.status_code}, trying fare chart...")
                        outbound_flights = await self._search_fare_chart(request)
                        return outbound_flights, return_flights

            except httpx.TimeoutException:
                print(f"[WizzAir] Timeout, attempt {attempt + 1}/{max_retries}")
                continue
            except Exception as e:
                print(f"[WizzAir] Error: {e}")
                break

        return outbound_flights, return_flights

    async def _search_fare_chart(self, request: FlightSearchRequest) -> list[Flight]:
        flights = []
        try:
            params = {
                "departureStation": request.origin.upper(),
                "arrivalStation": request.destination.upper(),
                "from": request.departure_date.isoformat(),
                "to": (request.departure_date + timedelta(days=3)).isoformat(),
            }

            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(
                    f"{self._api_base}/fare/chart",
                    params=params,
                    headers=self._get_headers(),
                    timeout=15.0
                )

                if resp.status_code == 200:
                    data = resp.json()
                    for fare in data.get("outboundFares", [])[:request.max_results]:
                        price_data = fare.get("price", {})
                        if price_data and price_data.get("amount", 0) > 0:
                            dep_str = fare.get("departureDate", "")
                            dep_time = datetime.fromisoformat(dep_str) if dep_str else datetime.now()
                            date_for_url = dep_time.strftime("%Y-%m-%d")

                            flights.append(Flight(
                                airline="Wizz Air",
                                flight_number=f"W6-{request.origin}-{request.destination}",
                                origin=request.origin.upper(),
                                destination=request.destination.upper(),
                                departure_time=dep_time,
                                arrival_time=dep_time + timedelta(hours=2),
                                price=float(price_data["amount"]),
                                currency=price_data.get("currencyCode", self.currency),
                                direct=True,
                                booking_url=_build_wizzair_booking_url(
                                    request.origin, request.destination, date_for_url, request.adults
                                ),
                            ))
        except Exception as e:
            print(f"[WizzAir] Fare chart error: {e}")

        return flights

    def _parse_flights(self, data: dict, key: str, origin: str, dest: str,
                       date_str: str, adults: int) -> list[Flight]:
        flights = []
        for flight_data in data.get(key, []):
            try:
                for fare in flight_data.get("fares", []):
                    dep_str = fare.get("departureDateTime", "")
                    arr_str = fare.get("arrivalDateTime", "")
                    dep_time = datetime.fromisoformat(dep_str) if dep_str else datetime.now()
                    arr_time = datetime.fromisoformat(arr_str) if arr_str else dep_time + timedelta(hours=2)

                    base_fare = fare.get("baseFare", {})
                    price = base_fare.get("amount", 0) if base_fare else 0
                    currency = base_fare.get("currencyCode", self.currency) if base_fare else self.currency

                    if price > 0:
                        duration = int((arr_time - dep_time).total_seconds() / 60)
                        flights.append(Flight(
                            airline="Wizz Air",
                            flight_number=fare.get("flightNumber", f"W6-{origin}-{dest}"),
                            origin=origin.upper(),
                            destination=dest.upper(),
                            departure_time=dep_time,
                            arrival_time=arr_time,
                            price=float(price),
                            currency=currency,
                            direct=True,
                            duration_minutes=duration,
                            booking_url=_build_wizzair_booking_url(origin, dest, date_str, adults),
                        ))
            except Exception as e:
                print(f"[WizzAir] Parse error: {e}")
        return flights

    async def get_destinations(self, origin: str) -> list[dict]:
        try:
            await self._get_api_url()
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(
                    f"{self._api_base}/asset/map?languageCode=en-gb",
                    headers=self._get_headers(),
                    timeout=15.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    cities = data.get("cities", [])
                    for city in cities:
                        for airport in city.get("airports", []):
                            if airport.get("iata") == origin.upper():
                                result = []
                                for conn in airport.get("connections", []):
                                    dest_iata = conn.get("iata", "")
                                    dest_city = self._find_city(cities, dest_iata)
                                    result.append({"code": dest_iata, "city": dest_city, "country": ""})
                                return result
        except Exception as e:
            print(f"[WizzAir] Destinations error: {e}")
        return []

    def _find_city(self, cities: list, iata: str) -> str:
        for city in cities:
            for airport in city.get("airports", []):
                if airport.get("iata") == iata:
                    return city.get("name", iata)
        return iata