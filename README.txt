================================================================================
    CHEAP FLIGHTS MCP - Server + AI Agent
    Hladanie najlacnejsich leteniek v realnom case
================================================================================


CO JE TENTO PROJEKT
-------------------
System na automaticke vyhladavanie najlacnejsich leteniek.
Sklada sa z 3 komponentov:

1. MCP SERVER  = Nastroje na hladanie letov (vola RyanAir/WizzAir priamo)
2. AI AGENT    = Claude AI ktory rozumie ludskej reci a pouziva MCP nastroje
3. WEB UI      = Webova stranka s formularom a AI chatom

Kazdy komponent funguje samostatne:
- Web formular nevyzaduje AI (priamo hlada lety)
- AI agent vyzaduje SAP AI Proxy (Claude model)
- MCP server je jadro - pouzivaju ho obe vrstvy


UMIESTNENIE
-----------
Lokalne: C:\Users\I070494\Desktop\TEST AUTOMATION\SCRIPTS\CHEAP_FLIGHTS_MCP
GitHub:  https://github.com/IngRobertFodor/CHEAP_FLIGHTS_MCP


BEZPECNOST
----------
- API kluc je LEN v .env (NIKDY necommitovat!)
- .gitignore chrani .env pred commitom
- Na GitHub ide iba .env.example (bez kluca)
- debug=False, CORS localhost only, input validacia


SPUSTENIE
---------
Pozri: HOW_TO_RUN_THIS.txt


ARCHITEKTURA
------------
  BEZ AI (formular):
  Prehliadac -> Flask -> MCP Server -> RyanAir/WizzAir API -> real-time ceny

  S AI (chat):
  Prehliadac -> Flask -> Claude AI (SAP Proxy) -> MCP Server -> API -> ceny


LETECKE SPOLOCNOSTI
--------------------
| Spolocnost     | Zdroj dat        | Poznamka              |
|----------------|------------------|-----------------------|
| RyanAir        | ryanair-py       | Spolahlivy, real-time |
| WizzAir        | Neoficialne API  | Retry + backoff       |
| Google Flights | fast-flights     | Kontrolny zdroj       |


MCP TOOLS
---------
search_flights       - Hlada lety (origin, destination, date, return, adults)
list_active_airlines - Zobrazuje aktivne letecke spolocnosti
add_airline          - Prida spolocnost do aktivneho zoznamu
remove_airline       - Odobre spolocnost z aktivneho zoznamu
get_destinations     - Vsetky dostupne linky z letiska


TECHNOLOGIE
-----------
Python 3.12, MCP SDK (FastMCP), httpx, ryanair-py, fast-flights,
tenacity (retry), Flask, SAP Hyperspace AI Proxy (Claude)


TESTY
-----
python test_search.py           - rychly test bez AI
python test_agent_prompts.py    - 8 use cases s AI (vyzaduje SAP Proxy)


AUTOR
-----
Robert Fodor, 2026

================================================================================