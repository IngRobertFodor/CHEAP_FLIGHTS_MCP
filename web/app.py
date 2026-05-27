"""
Flask web server - REST API a UI pre hladanie leteniek.
Security: debug=False, CORS localhost, input validation, generic errors.
"""

import asyncio
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from agent.flight_agent import FlightAgent

app = Flask(__name__)
CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000"])

agent = None
loop = None


def get_or_create_loop():
    global loop
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def run_async(coro):
    l = get_or_create_loop()
    return l.run_until_complete(coro)


def sanitize_input(value, max_length: int = 100) -> str:
    """Sanitizuj vstup."""
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def safe_int(value, default: int = 1, min_val: int = 1, max_val: int = 9) -> int:
    """Bezpecna konverzia na int s limitmi."""
    try:
        v = int(value)
        return max(min_val, min(v, max_val))
    except (ValueError, TypeError):
        return default


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search_flights():
    global agent

    data = request.get_json()
    if not data:
        return jsonify({"error": "Chybajuce data"}), 400

    origin = sanitize_input(data.get("origin", ""), 3).upper()
    destination = sanitize_input(data.get("destination", ""), 3).upper()
    departure_date = sanitize_input(data.get("departure_date", ""), 10)
    return_date = sanitize_input(data.get("return_date", ""), 10)
    adults = safe_int(data.get("adults", 1))

    if not origin or not destination or not departure_date:
        return jsonify({"error": "Povinne polia: origin, destination, departure_date"}), 400

    # IATA validacia
    if not origin.isalpha() or len(origin) != 3:
        return jsonify({"error": "Neplatny IATA kod: origin (3 pismena)"}), 400
    if not destination.isalpha() or len(destination) != 3:
        return jsonify({"error": "Neplatny IATA kod: destination (3 pismena)"}), 400

    # Rovnake origin a destination
    if origin == destination:
        return jsonify({"error": "Origin a destination musia byt rozne"}), 400

    # Datum validacia
    try:
        dep_date = date.fromisoformat(departure_date)
    except ValueError:
        return jsonify({"error": "Neplatny format datumu odletu (YYYY-MM-DD)"}), 400

    if dep_date < date.today():
        return jsonify({"error": "Datum odletu nemoze byt v minulosti"}), 400

    if return_date:
        try:
            ret_date = date.fromisoformat(return_date)
            if ret_date <= dep_date:
                return jsonify({"error": "Datum navratu musi byt po datume odletu"}), 400
        except ValueError:
            return jsonify({"error": "Neplatny format datumu navratu (YYYY-MM-DD)"}), 400

    try:
        if agent is None:
            agent = FlightAgent()
            run_async(agent.connect_to_mcp())

        args = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "adults": adults,
        }
        if return_date:
            args["return_date"] = return_date

        result = run_async(agent.call_tool("search_flights", args))
        return jsonify(json.loads(result))

    except Exception as e:
        # Genericka chybova sprava (neodhaluje internals)
        print(f"[Flask] Search error: {e}", file=sys.stderr)
        return jsonify({"error": "Nastala chyba pri vyhladavani. Skuste znova."}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    global agent

    data = request.get_json()
    message = sanitize_input(data.get("message", ""), 1000)

    if not message:
        return jsonify({"error": "Prazdna sprava"}), 400

    try:
        if agent is None:
            agent = FlightAgent()
            run_async(agent.connect_to_mcp())

        response = run_async(agent.chat(message))
        return jsonify({"response": response})

    except Exception as e:
        print(f"[Flask] Chat error: {e}", file=sys.stderr)
        return jsonify({"error": "Nastala chyba pri spracovani. Skuste znova."}), 500


@app.route("/api/airlines", methods=["GET"])
def list_airlines():
    global agent

    try:
        if agent is None:
            agent = FlightAgent()
            run_async(agent.connect_to_mcp())

        result = run_async(agent.call_tool("list_active_airlines", {}))
        return jsonify(json.loads(result))

    except Exception as e:
        print(f"[Flask] Airlines error: {e}", file=sys.stderr)
        return jsonify({"error": "Chyba pri nacitani airlines"}), 500


@app.route("/api/airlines/add", methods=["POST"])
def add_airline():
    global agent
    data = request.get_json()
    code = sanitize_input(data.get("airline_code", ""), 20).lower()

    if not code.replace("_", "").isalpha():
        return jsonify({"error": "Neplatny kod spolocnosti"}), 400

    try:
        if agent is None:
            agent = FlightAgent()
            run_async(agent.connect_to_mcp())

        result = run_async(agent.call_tool("add_airline", {"airline_code": code}))
        return jsonify({"message": result})

    except Exception as e:
        print(f"[Flask] Add airline error: {e}", file=sys.stderr)
        return jsonify({"error": "Chyba pri pridavani spolocnosti"}), 500


@app.route("/api/airlines/remove", methods=["POST"])
def remove_airline():
    global agent
    data = request.get_json()
    code = sanitize_input(data.get("airline_code", ""), 20).lower()

    if not code.replace("_", "").isalpha():
        return jsonify({"error": "Neplatny kod spolocnosti"}), 400

    try:
        if agent is None:
            agent = FlightAgent()
            run_async(agent.connect_to_mcp())

        result = run_async(agent.call_tool("remove_airline", {"airline_code": code}))
        return jsonify({"message": result})

    except Exception as e:
        print(f"[Flask] Remove airline error: {e}", file=sys.stderr)
        return jsonify({"error": "Chyba pri odoberani spolocnosti"}), 500


@app.route("/api/reset", methods=["POST"])
def reset_chat():
    global agent
    if agent:
        agent.reset_conversation()
    return jsonify({"message": "Konverzacia resetovana"})


if __name__ == "__main__":
    print("=" * 60)
    print("  Flight Search Web Server")
    print("=" * 60)
    print("  http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, host="127.0.0.1", port=5000)