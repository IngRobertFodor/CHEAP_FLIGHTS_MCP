================================================================================
    CHEAP FLIGHTS - MCP Server + AI Agent
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


ARCHITEKTURA
------------

  BEZ AI (formular):
  Prehliadac → Flask → MCP Server → RyanAir/WizzAir API → real-time ceny

  S AI (chat):
  Prehliadac → Flask → Claude AI (SAP Proxy) → MCP Server → API → ceny

  Diagram:
  +------------+     +-----------+     +------------+
  | Web UI     |---->| Flask     |---->| MCP Server |----> RyanAir API
  | (formular) |     | (app.py)  |     | (server.py)|----> WizzAir API
  +------------+     +-----------+     +------------+----> Google Flights
        |                  |
        |            +-----------+
        +----------->| Claude AI | (len pre chat)
        (AI chat)    | (SAP Proxy|
                     +-----------+


CO POTREBUJE AI A CO NIE
------------------------
| Funkcia                     | AI (SAP Proxy) | Internet |
|-----------------------------|----------------|----------|
| Hladanie cez formular       | NEPOTREBUJE    | ANO      |
| AI chat (slovensky dotazy)  | POTREBUJE      | ANO      |
| Pridanie/odobranie airlines | NEPOTREBUJE    | NIE      |
| Odoslanie emailu            | NEPOTREBUJE    | NIE      |
| Test skript                 | NEPOTREBUJE    | ANO      |


LETECKE SPOLOCNOSTI
--------------------
| Spolocnost     | Zdroj dat        | Destinacie         | Poznamka          |
|----------------|------------------|--------------------|-------------------|
| RyanAir        | ryanair-py       | Routes API (vsetky)| Spolahlivy        |
| WizzAir        | Neoficialne API  | Route map          | Moze blokovat(429)|
| Google Flights | fast-flights     | Nepodporuje        | Kontrolny zdroj   |

RyanAir: Real-time ceny, kompletny zoznam destinacii (aj sezonnych).
WizzAir: Real-time ceny, retry s exponential backoff pri blokovani.
Google Flights: Overovaci zdroj, ceny konvertovane z USD na EUR (live kurz).


MCP TOOLS (nastroje servera)
-----------------------------
search_flights       - Hlada lety (origin, destination, date, return_date, adults)
list_active_airlines - Zobrazuje aktivne letecke spolocnosti
add_airline          - Prida spolocnost do aktivneho zoznamu
remove_airline       - Odobre spolocnost z aktivneho zoznamu
get_destinations     - Vsetky dostupne linky z letiska (vratane sezonnych)


BOOKING LINKY
-------------
Kazdy vysledok obsahuje priamy deep link na stranku leteckej spolocnosti:
- RyanAir: priamo na vysledky vyhladavania pre dany let
- WizzAir: priamo na vyber letu pre danu trasu
- Google Flights: vyhladavanie na Google pre overenie ceny

Vsetky linky su overene a funkcne.


EMAIL NOTIFIKACIE
-----------------
- Checkbox "Odoslat email s vysledkami" v UI
- Pole na email adresu + vyber max poctu vysledkov (1/3/5/10)
- Po vyhladani kliknes "Odoslat email" → otvori sa tvoj email klient
- Email obsahuje: ceny, trasy, priame booking linky
- Nevyzaduje ziadne heslo (pouziva mailto: protokol)


KONFIGURACIA
------------
Subor: mcp_server/config.json

{
    "active_airlines": ["ryanair", "wizzair"],
    "available_airlines": ["ryanair", "wizzair", "google_flights"],
    "default_currency": "EUR",
    "max_results_per_airline": 10
}

Zmenit mozes:
- Aktivne airlines (pridat google_flights pre kontrolu)
- Valutu (EUR default)
- Max pocet vysledkov na airline


POUZITE TECHNOLOGIE
--------------------
| Technologia    | Verzia | Ucel                                   |
|----------------|--------|----------------------------------------|
| Python         | 3.12   | Hlavny jazyk                           |
| MCP SDK        | 1.27+  | FastMCP server (Anthropic standard)     |
| Claude Sonnet 4| 2025   | AI agent (tool use + reasoning)        |
| ryanair-py     | 3.0    | RyanAir data                           |
| fast-flights   | 2.0+   | Google Flights data                    |
| httpx          | 0.27+  | Async HTTP (WizzAir, kurzy)            |
| tenacity       | 9.0+   | Retry s exponential backoff            |
| Flask          | 3.0+   | Web server                             |
| flask-cors     | 4.0+   | CORS podpora pre API                   |

Moderne postupy:
- FastMCP deklarativny pattern (@mcp.tool() dekorator)
- asyncio.gather() pre paralelne volanie vsetkych airlines
- Exponential backoff + jitter pre retry
- User-Agent rotacia proti blokovaniu
- Deep linky na booking (overene)
- USD->EUR live konverzia (frankfurter.app)


PRIDANIE NOVEJ SPOLOCNOSTI
---------------------------
1. Vytvor: mcp_server/airlines/nova.py (dedi z BaseAirline)
2. Implementuj: search_flights() + get_destinations()
3. Pridaj import do: mcp_server/airlines/__init__.py
4. Pridaj kod do: mcp_server/config.json → available_airlines
5. Pridaj do: mcp_server/server.py → get_airline_adapters()


STRUKTURA SUBOROV
------------------
cheap_flights/
|-- mcp_server/
|   |-- server.py              FastMCP server (5 tools)
|   |-- config.json            Nastavenia
|   |-- airlines/
|       |-- base_airline.py    Abstraktna trieda (interface)
|       |-- ryanair.py         RyanAir + deep link + routes API
|       |-- wizzair.py         WizzAir + retry + deep link
|       |-- google_flights.py  Google Flights + USD/EUR konverzia
|-- agent/
|   |-- flight_agent.py        Claude AI agent + MCP klient
|   |-- prompts.py             System prompt (instrukcie pre AI)
|-- web/
|   |-- app.py                 Flask REST API server
|   |-- templates/index.html   Web UI (formular + chat)
|   |-- static/css/style.css   Dark theme dizajn
|   |-- static/js/app.js       Frontend logika + mailto
|-- .env                       API kluce
|-- requirements.txt           Zavislosti
|-- test_search.py             Testovaci skript
|-- README.txt                 Tento subor
|-- HOW_TO_RUN_THIS.txt        Postup spustenia


AUTOR
-----
Vytvorene s pomocou AI (Claude + Cline), Maj 2026

================================================================================