# Contributing to cheap-flights-mcp

Thank you for your interest in contributing!

## How to Contribute

### Reporting Issues
- Use [GitHub Issues](https://github.com/IngRobertFodor/cheap-flights-mcp/issues)
- Include: steps to reproduce, expected vs actual behavior, Python version

### Suggesting New Airlines
- Open an issue with the airline name and any known API endpoints
- See "Adding a New Airline" section in README.md

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-airline`
3. Make your changes
4. Test: `python test_search.py`
5. Commit: `git commit -m "Add EasyJet adapter"`
6. Push: `git push origin feature/new-airline`
7. Open a Pull Request

### Code Style
- Python 3.12+
- Type hints where possible
- Docstrings for public methods
- Follow existing adapter patterns (inherit from `BaseAirline`)

### Security
- Never commit API keys or `.env` files
- Run `bandit` before submitting: `bandit -r mcp_server/ agent/ web/`
- Run `pip-audit` for dependency checks

## Adding a New Airline Adapter

```python
# mcp_server/airlines/new_airline.py
from .base_airline import BaseAirline, Flight, FlightSearchRequest, FlightSearchResult

class NewAirlineAdapter(BaseAirline):
    @property
    def name(self) -> str:
        return "New Airline"

    @property
    def code(self) -> str:
        return "new_airline"

    async def search_flights(self, request: FlightSearchRequest) -> FlightSearchResult:
        # Your implementation here
        pass

    async def get_destinations(self, origin: str) -> list[dict]:
        # Your implementation here
        pass
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.