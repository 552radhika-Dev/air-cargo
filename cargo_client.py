"""
cargo_client.py - Mock CargoAI Service
Simulates CargoAI Routes & Schedules and Quote & Book APIs with realistic flight data.
Supports all 32 scenarios including filters, edge cases, rateless flights,
oversized cargo errors, and partial airline timeouts.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List


def _normalize_airport_code(text: Optional[str]) -> str:
    if not text:
        return "MAA"
    clean = text.strip().upper()
    if clean in ("EMPTY", "NONE", "ZZZ", "NORATE"):
        return clean
    # City mappings
    city_map = {
        "CHENNAI": "MAA", "FRANKFURT": "FRA", "BANGALORE": "BLR",
        "BENGALURU": "BLR", "PARIS": "CDG", "SINGAPORE": "SIN",
        "LONDON": "LHR", "NEW YORK": "JFK", "DUBAI": "DXB", "DOHA": "DOH"
    }
    return city_map.get(clean, clean[-3:])


def _generate_flights_for_route(origin_code: str, dest_code: str, date_str: str,
                                is_rate: bool = False, weight_kg: float = 850.0,
                                volume_cbm: float = 6.5, dimensions_cm: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """Generates a rich, varied set of flight options."""
    try:
        # Try parsing date, default to 2026-09-22 if standard string
        if " " in date_str:
            dep_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            dep_date = datetime(2026, 9, 22).date()
    except Exception:
        dep_date = datetime(2026, 9, 22).date()

    d_base = dep_date.strftime("%Y-%m-%d")

    # Base price calculation if rate search
    w = weight_kg or 850.0
    v = volume_cbm or 6.5
    volumetric_w = (v * 1_000_000) / 6000
    chg_weight = max(w, volumetric_w)

    # Base flights pool
    flights = [
        # Flight 1: Lufthansa - Direct, Freighter, Live Rate, Bookable, Low CO2
        {
            "airline": "Lufthansa Cargo",
            "flightNumber": "LH8220",
            "origin": f"{origin_code}",
            "destination": f"{dest_code}",
            "departure": f"{d_base} 04:30",
            "arrival": f"{d_base} 13:45",
            "legs": [origin_code, dest_code],
            "stops": 0,
            "available": True,
            "availableReason": None,
            "features": {"bookable": True},
            "bodyType": "Freighter",
            "aircraftCode": "B77F",
            "co2": {"value": 395.0},
            "latestAcceptanceTime": f"{d_base} 01:00",
            "timeOfAvailability": f"{d_base} 16:30",
            "total": f"{round(chg_weight * 3.80, 2)} USD" if is_rate else None,
            "rates": [
                {
                    "total": round(chg_weight * 3.80, 2),
                    "allInRate": 3.80,
                    "netRate": 3.30,
                    "type": "LIVE",
                    "name": "General Cargo Live",
                    "currency": "USD"
                }
            ] if is_rate else []
        },
        # Flight 2: Emirates SkyCargo - 1 Stop via DXB, Widebody, Evening departure (>18:00)
        {
            "airline": "Emirates SkyCargo",
            "flightNumber": "EK9502",
            "origin": f"{origin_code}",
            "destination": f"{dest_code}",
            "departure": f"{d_base} 19:30",
            "arrival": f"{d_base} 07:15",  # arriving next morning before 10 AM!
            "legs": [origin_code, "DXB", dest_code],
            "stops": 1,
            "available": True,
            "availableReason": None,
            "features": {"bookable": True},
            "bodyType": "Widebody",
            "aircraftCode": "B77W",
            "co2": {"value": 460.0},
            "latestAcceptanceTime": f"{d_base} 15:30",  # cargo accepted after 2 PM!
            "timeOfAvailability": f"{d_base} 11:00",
            "total": f"{round(chg_weight * 3.50, 2)} USD" if is_rate else None,
            "rates": [
                {
                    "total": round(chg_weight * 3.50, 2),
                    "allInRate": 3.50,
                    "netRate": 3.05,
                    "type": "LIVE",
                    "name": "SkyCargo Priority",
                    "currency": "USD"
                }
            ] if is_rate else []
        },
        # Flight 3: Qatar Airways - 1 Stop via DOH, Widebody, Cheapest option
        {
            "airline": "Qatar Airways Cargo",
            "flightNumber": "QR8140",
            "origin": f"{origin_code}",
            "destination": f"{dest_code}",
            "departure": f"{d_base} 09:15",
            "arrival": f"{d_base} 21:00",
            "legs": [origin_code, "DOH", dest_code],
            "stops": 1,
            "available": True,
            "availableReason": None,
            "features": {"bookable": True},
            "bodyType": "Widebody",
            "aircraftCode": "A359",
            "co2": {"value": 420.0},
            "latestAcceptanceTime": f"{d_base} 05:00",
            "timeOfAvailability": f"{d_base} 23:45",
            "total": f"{round(chg_weight * 3.20, 2)} USD" if is_rate else None,
            "rates": [
                {
                    "total": round(chg_weight * 3.20, 2),
                    "allInRate": 3.20,
                    "netRate": 2.80,
                    "type": "LIVE",
                    "name": "Secure Air Live",
                    "currency": "USD"
                }
            ] if is_rate else []
        },
        # Flight 4: Air India Cargo - Direct, Widebody, Contract Rate (Non-live), Arrives before 10 AM
        {
            "airline": "Air India Cargo",
            "flightNumber": "AI101",
            "origin": f"{origin_code}",
            "destination": f"{dest_code}",
            "departure": f"{d_base} 01:10",
            "arrival": f"{d_base} 08:45",  # Arrives before 10:00 AM!
            "legs": [origin_code, dest_code],
            "stops": 0,
            "available": True,
            "availableReason": None,
            "features": {"bookable": False},
            "bodyType": "Widebody",
            "aircraftCode": "B789",
            "co2": {"value": 510.0},
            "latestAcceptanceTime": f"{d_base} 20:00",
            "timeOfAvailability": f"{d_base} 12:00",
            "total": f"{round(chg_weight * 3.65, 2)} USD" if is_rate else None,
            "rates": [
                {
                    "total": round(chg_weight * 3.65, 2),
                    "allInRate": 3.65,
                    "netRate": 3.15,
                    "type": "CONTRACT",
                    "name": "Standard Contract Rate",
                    "currency": "USD"
                }
            ] if is_rate else []
        },
        # Flight 5: British Airways - 1 Stop, Freighter, High LAT (16:00)
        {
            "airline": "British Airways Cargo",
            "flightNumber": "BA3580",
            "origin": f"{origin_code}",
            "destination": f"{dest_code}",
            "departure": f"{d_base} 21:00",
            "arrival": f"{d_base} 09:30",
            "legs": [origin_code, "LHR", dest_code],
            "stops": 1,
            "available": True,
            "availableReason": None,
            "features": {"bookable": True},
            "bodyType": "Freighter",
            "aircraftCode": "B77F",
            "co2": {"value": 485.0},
            "latestAcceptanceTime": f"{d_base} 16:00",  # cargo accepted after 2 PM!
            "timeOfAvailability": f"{d_base} 14:00",
            "total": f"{round(chg_weight * 4.10, 2)} USD" if is_rate else None,
            "rates": [
                {
                    "total": round(chg_weight * 4.10, 2),
                    "allInRate": 4.10,
                    "netRate": 3.60,
                    "type": "LIVE",
                    "name": "Live Express",
                    "currency": "USD"
                }
            ] if is_rate else []
        },
        # Flight 6: Turkish Cargo - 2 Stops, Narrowbody, Unavailable due to cargo loadability if dimensions extreme
        {
            "airline": "Turkish Cargo",
            "flightNumber": "TK6520",
            "origin": f"{origin_code}",
            "destination": f"{dest_code}",
            "departure": f"{d_base} 11:00",
            "arrival": f"{d_base} 23:30",
            "legs": [origin_code, "IST", "MUC", dest_code],
            "stops": 2,
            "available": True,
            "availableReason": None,
            "features": {"bookable": False},
            "bodyType": "Narrowbody",
            "aircraftCode": "A321F",
            "co2": {"value": 620.0},
            "latestAcceptanceTime": f"{d_base} 07:00",
            "timeOfAvailability": f"{d_base} 04:00",
            "total": f"{round(chg_weight * 3.10, 2)} USD" if is_rate else None,
            "rates": [
                {
                    "total": round(chg_weight * 3.10, 2),
                    "allInRate": 3.10,
                    "netRate": 2.70,
                    "type": "LIVE",
                    "name": "Economy Live Cargo",
                    "currency": "USD"
                }
            ] if is_rate else []
        }
    ]

    # Scenario 31 condition: If dimensions are extreme or length >= 250 cm, mark loadability error
    if dimensions_cm and (max(dimensions_cm) >= 200 or any(d > 160 for d in dimensions_cm)):
        flights[-1]["available"] = False
        flights[-1]["availableReason"] = "dimensions are not loadable"

    return flights


def search_schedules(origin: str, destination: str, departure_date: str) -> Dict[str, Any]:
    """
    Mock CargoAI Routes & Schedules API: POST /search
    Returns schedule options and any partial airline errors.
    """
    orig = _normalize_airport_code(origin)
    dest = _normalize_airport_code(destination)

    # Scenario 29: Trigger empty schedule results
    if orig in ("EMPTY", "NONE", "ZZZ") or dest in ("EMPTY", "NONE", "ZZZ"):
        return {"flights": [], "metadata": {"searchErrors": []}}

    flights = _generate_flights_for_route(orig, dest, departure_date, is_rate=False)

    # Scenario 32: Partial airline search errors
    search_errors = [
        {"airline": "EK", "message": "Routes & Schedules provider timeout"}
    ]

    return {
        "flights": flights,
        "metadata": {
            "searchErrors": search_errors
        }
    }


def search_rates(origin: str, destination: str, departure_date: str,
                 weight_kg: Optional[float] = 850.0, volume_cbm: Optional[float] = 6.5,
                 pieces: Optional[int] = 6, dimensions_cm: Optional[tuple] = None,
                 force_rateless: bool = False, force_oversize: bool = False) -> Dict[str, Any]:
    """
    Mock CargoAI Quote & Book API: POST /search
    Returns flights with rate information, handling codes, and any partial search errors.
    """
    orig = _normalize_airport_code(origin)
    dest = _normalize_airport_code(destination)

    # Scenario 29: Empty results
    if orig in ("EMPTY", "NONE", "ZZZ") or dest in ("EMPTY", "NONE", "ZZZ"):
        return {"flights": [], "metadata": {"searchErrors": []}}

    # Scenario 30: Schedule found but no rate available
    if force_rateless or orig in ("NORATE",) or dest in ("NORATE",):
        flights = _generate_flights_for_route(orig, dest, departure_date, is_rate=False)
        for f in flights:
            f["total"] = None
            f["rates"] = []
        return {
            "flights": flights,
            "metadata": {"searchErrors": []}
        }

    # Handle dimensions conversion if volume not directly passed
    if volume_cbm is None and dimensions_cm and pieces:
        volume_cbm = round(dimensions_cm[0] * dimensions_cm[1] * dimensions_cm[2] * pieces / 1_000_000, 2)

    flights = _generate_flights_for_route(
        orig, dest, departure_date, is_rate=True,
        weight_kg=weight_kg or 850.0,
        volume_cbm=volume_cbm or 6.5,
        dimensions_cm=dimensions_cm
    )

    # Scenario 31: If explicitly flagged or cargo is marked oversized
    if force_oversize:
        flights[0]["available"] = False
        flights[0]["availableReason"] = "dimensions are not loadable"

    # Scenario 32: Partial airline timeout
    search_errors = [
        {"airline": "EK", "message": "Quote service timeout"}
    ]

    return {
        "flights": flights,
        "metadata": {
            "searchErrors": search_errors
        }
    }
