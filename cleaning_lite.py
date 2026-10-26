"""
cleaning_lite.py - Data cleaning pipeline for CargoAI raw responses.
Normalizes airline names, airports, dates, prices, and preserves rich cargo metadata
needed for filtering, sorting, and edge cases.
"""
import re
from datetime import datetime

AIRLINE_ALIASES = {
    "lh": "LH", "lufthansa": "LH", "lufthansa cargo": "LH", "dlh": "LH",
    "ai": "AI", "air india": "AI", "air india cargo": "AI", "aic": "AI",
    "ek": "EK", "emirates": "EK", "emirates skycargo": "EK", "uae": "EK",
    "qr": "QR", "qatar airways": "QR", "qatar airways cargo": "QR", "qtr": "QR",
    "tk": "TK", "turkish cargo": "TK", "turkish airlines": "TK", "thy": "TK",
    "ba": "BA", "british airways": "BA", "british airways cargo": "BA", "baw": "BA",
    "vs": "VS", "virgin atlantic": "VS", "virgin atlantic cargo": "VS", "vir": "VS",
    "aa": "AA", "american airlines": "AA", "american airlines cargo": "AA", "aal": "AA",
}

TIME_FORMATS = [
    "%Y-%m-%d %H:%M", "%d-%b-%Y %I:%M %p", "%Y/%m/%d %H:%M",
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"
]
EUR_TO_USD = 1.08  # Demo exchange rate


def _airline(text):
    return AIRLINE_ALIASES.get(str(text).strip().lower(), str(text).strip()[:2].upper())


def _airport(text):
    match = re.search(r"([A-Za-z]{3})\)?\s*$", str(text))
    return match.group(1).upper() if match else str(text).strip()[:3].upper()


def _when(text):
    """Try known date formats; return datetime or None."""
    if not text:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(str(text).strip(), fmt)
        except ValueError:
            pass
    return None


def _price(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    rate = EUR_TO_USD if ("€" in text or "EUR" in text.upper()) else 1.0
    digits = re.sub(r"[^0-9.\-]", "", text)
    return round(float(digits) * rate, 2) if digits else None


def _stops(value, legs):
    if value is not None:
        text = str(value).strip().lower()
        if text == "direct":
            return 0
        found = re.search(r"\d+", text)
        if found:
            return int(found.group())
    count = len(legs.split(",")) if isinstance(legs, str) else len(legs or [])
    return max(0, count - 1)


def _yes(value):
    if value is None:
        return True
    return str(value).strip().lower() in ("true", "yes", "y", "1")


def clean(raw):
    """
    Cleans raw CargoAI search response.
    Returns: (list of tidy flights, report dict)
    """
    rows = [dict(r) for r in raw.get("flights", [])]
    report = {"rows_in": len(rows)}
    if not rows:
        report["rows_out"] = 0
        return [], report

    # 1. Standardise airline names
    for r in rows:
        r["airline_code"] = _airline(r.get("airline", ""))
    report["airline_names_fixed"] = sum(1 for r in rows if r.get("airline") != r["airline_code"])
    report["unknown_airline_removed"] = sum(1 for r in rows if r["airline_code"] is None)
    rows = [r for r in rows if r["airline_code"] is not None]

    # 2. Tidy text, dates, prices and stops
    for r in rows:
        fn = r.get("flightNumber", r.get("flight_no", ""))
        r["flight_no"] = re.sub(r"[^A-Za-z0-9]", "", str(fn)).upper()
        r["origin"] = _airport(r.get("origin"))
        r["destination"] = _airport(r.get("destination"))
        r["dep"] = _when(r.get("departure"))
        r["arr"] = _when(r.get("arrival"))
        r["total_usd"] = _price(r.get("total"))
        r["stops_n"] = _stops(r.get("stops"), r.get("legs"))

    report["prices_converted_to_usd"] = sum(1 for r in rows if isinstance(r.get("total"), str))
    report["stops_inferred_from_legs"] = sum(1 for r in rows if r.get("stops") is None)

    # 3. Deduplicate
    seen, unique = set(), []
    for r in rows:
        key = (r["flight_no"], str(r["dep"]))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    report["duplicates_removed"] = len(rows) - len(unique)
    rows = unique

    # 4. Filter invalid times and negative prices
    def bad_time(r):
        return r["dep"] is None or r["arr"] is None or r["arr"] <= r["dep"]

    def bad_price(r):
        return r["total_usd"] is not None and r["total_usd"] < 0

    report["invalid_times_removed"] = sum(1 for r in rows if bad_time(r))
    rows = [r for r in rows if not bad_time(r)]
    report["negative_prices_removed"] = sum(1 for r in rows if bad_price(r))
    rows = [r for r in rows if not bad_price(r)]

    # 5. Build rich result preserving all Section 3 fields
    out = []
    for r in rows:
        # Extract features and body type
        features = r.get("features", {})
        bookable = features.get("bookable", True) if isinstance(features, dict) else True
        co2_data = r.get("co2", {})
        co2_val = co2_data.get("value", 450.0) if isinstance(co2_data, dict) else 450.0

        item = {
            "airline": r["airline_code"],
            "flight_no": r["flight_no"],
            "origin": r["origin"],
            "destination": r["destination"],
            "departure": r["dep"].strftime("%Y-%m-%d %H:%M") if r["dep"] else "",
            "arrival": r["arr"].strftime("%Y-%m-%d %H:%M") if r["arr"] else "",
            "duration_h": round((r["arr"] - r["dep"]).total_seconds() / 3600, 1) if (r["dep"] and r["arr"]) else 0.0,
            "stops": r["stops_n"],
            "total_usd": r["total_usd"],
            # Section 3 result fields
            "bookable": bookable,
            "available": _yes(r.get("available", True)),
            "available_reason": r.get("availableReason"),
            "body_type": r.get("bodyType", "Widebody"),
            "aircraft_code": r.get("aircraftCode", "B77F"),
            "co2": float(co2_val),
            "latest_acceptance_time": r.get("latestAcceptanceTime"),
            "time_of_availability": r.get("timeOfAvailability"),
            "rates": r.get("rates", [])
        }
        out.append(item)

    report["rows_out"] = len(out)
    return out, report
