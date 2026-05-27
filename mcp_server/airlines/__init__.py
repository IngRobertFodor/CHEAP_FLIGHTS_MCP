"""
Airlines module - adaptery pre letecke spolocnosti.
"""

from .base_airline import BaseAirline, Flight, FlightSearchRequest, FlightSearchResult
from .ryanair import RyanairAdapter
from .wizzair import WizzairAdapter
from .google_flights import GoogleFlightsAdapter

__all__ = [
    "BaseAirline",
    "Flight",
    "FlightSearchRequest",
    "FlightSearchResult",
    "RyanairAdapter",
    "WizzairAdapter",
    "GoogleFlightsAdapter",
]