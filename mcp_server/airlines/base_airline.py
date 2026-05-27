"""
Abstraktná trieda pre adaptéry leteckých spoločností.
Každá nová letecká spoločnosť musí implementovať tieto metódy.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Flight:
    """Dátová trieda reprezentujúca jeden let."""
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    currency: str = "EUR"
    direct: bool = True
    origin_city: str = ""
    destination_city: str = ""
    duration_minutes: int = 0
    booking_url: str = ""

    def to_dict(self) -> dict:
        return {
            "airline": self.airline,
            "flight_number": self.flight_number,
            "origin": self.origin,
            "origin_city": self.origin_city,
            "destination": self.destination,
            "destination_city": self.destination_city,
            "departure_time": self.departure_time.isoformat(),
            "arrival_time": self.arrival_time.isoformat(),
            "price": self.price,
            "currency": self.currency,
            "direct": self.direct,
            "duration_minutes": self.duration_minutes,
            "booking_url": self.booking_url,
        }


@dataclass
class FlightSearchRequest:
    """Požiadavka na vyhľadávanie letov."""
    origin: str
    destination: str
    departure_date: date
    return_date: Optional[date] = None
    adults: int = 1
    currency: str = "EUR"
    max_results: int = 10
    flexible_dates: bool = False


@dataclass
class FlightSearchResult:
    """Výsledok vyhľadávania letov."""
    outbound_flights: list = field(default_factory=list)
    return_flights: list = field(default_factory=list)
    airline: str = ""
    search_timestamp: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "airline": self.airline,
            "search_timestamp": self.search_timestamp,
            "outbound_flights": [f.to_dict() if isinstance(f, Flight) else f for f in self.outbound_flights],
            "return_flights": [f.to_dict() if isinstance(f, Flight) else f for f in self.return_flights],
            "error": self.error,
        }


class BaseAirline(ABC):
    """Abstraktná trieda pre adaptéry leteckých spoločností."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def code(self) -> str:
        pass

    @abstractmethod
    async def search_flights(self, request: FlightSearchRequest) -> FlightSearchResult:
        pass

    @abstractmethod
    async def get_destinations(self, origin: str) -> list[dict]:
        pass

    def _get_timestamp(self) -> str:
        return datetime.now().isoformat()