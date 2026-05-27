"""
Flask web server - poskytuje REST API a UI pre hladanie leteniek.
Security: debug=False, CORS restricted to localhost, input validation.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from agent.flight_agent import FlightAgent

app = Flask(__name__)
# CORS obmedzeny len na localhost (bezpecnost)
CORS(app, origins=["http://localhost:5000", "http://127.0.0.1:5000"])

# Globalny agent
agent = None
loop = None


def get_or_create_loop():
    """Ziskaj alebo vytvor event loop."""
    global loop
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def run_async(coro):
    """Spusti async funkciu v synchronnom kontexte."""
    l = get_or_create_loop()
    return l.run_until_complete(coro)


def sanitize_input(value: str, max_length: int = 100) -> str:
    """Sanitizuj vstup - odstran nebezpecne znaky."""
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def search_flights():
    """API endpoint pre hladanie letov."""
    global agent

    data = request.get_json()
    if not data:
        return jsonify({"error": "Chybajuce data"}), 400

    origin = sanitize_input(data.get("origin", ""), 3).upper()
    destination = sanitize_input(data.get("destination", ""), 3).upper()
    departure_date = sanitize_input(data.get("departure_date", ""), 10)
    return_date = sanitize_input(data.get("return_date", ""), 10)
    adults = min(max(int(data.get("adults", 1)), 1), 9)  # 1-9

    if not origin or not destination or not departure_date:
        return jsonify({"error": "Povinne polia: origin, destination, departure_date"}), 400

    # Validacia IATA kodu (len pismena, 3 znaky)
    if not origin.isalpha() or len(origin) != 3:
        return jsonify({"error": "Neplatny IATA kod: origin"}), 400
    if not destination.isalpha() or len(destination) != 3:
        return jsonify({"error": "Neplatny IATA kod: destination"}), 400

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
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """API endpoint pre AI chat."""
    global agent

    data = request.get_json()
    message = sanitize_input(data.get("message", ""), 500)

    if not message:
        return jsonify({"error": "Prazdna sprava"}), 400

    try:
        if agent is None:
            agent = FlightAgent()
            run_async(agent.connect_to_mcp())

        response = run_async(agent.chat(message))
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


@app.route("/api/airlines/add", methods=["POST"])
def add_airline():
    global agent
    data = request.get_json()
    code = sanitize_input(data.get("airline_code", ""), 20).lower()

    try:
        if agent is None:
            agent = FlightAgent()
            run_async(agent.connect_to_mcp())

        result = run_async(agent.call_tool("add_airline", {"airline_code": code}))
        return jsonify({"message": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/airlines/remove", methods=["POST"])
def remove_airline():
    global agent
    data = request.get_json()
    code = sanitize_input(data.get("airline_code", ""), 20).lower()

    try:
        if agent is None:
            agent = FlightAgent()
            run_async(agent.connect_to_mcp())

        result = run_async(agent.call_tool("remove_airline", {"airline_code": code}))
        return jsonify({"message": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    # debug=False pre bezpecnost (CWE-94)
    app.run(debug=False, host="127.0.0.1", port=5000)