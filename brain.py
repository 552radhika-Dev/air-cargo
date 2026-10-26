"""
brain.py - Natural Language Understanding (NLU) for Air Cargo Chatbot.
Extracts search intent, routes, dates, cargo specifications, filters, and sorts.
Supports all 32 prompt scenarios from Prompt Snippets.xlsx.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Non-origin keywords that should never be mistaken for origins
NON_LOCATIONS = {
    "flight", "flights", "schedule", "schedules", "rate", "rates",
    "option", "options", "show", "need", "best", "air", "cheapest",
    "fastest", "direct", "widebody", "freighter", "available", "bookable"
}

AIRPORTS = {
    "MAA": "Chennai", "FRA": "Frankfurt", "BLR": "Bangalore",
    "CDG": "Paris", "ORY": "Paris", "SIN": "Singapore",
    "LHR": "London", "LGW": "London", "JFK": "New York",
    "EWR": "New York", "DXB": "Dubai", "DOH": "Doha",
    "ORD": "Chicago", "LAX": "Los Angeles", "HKG": "Hong Kong"
}

CITY_TO_AIRPORT = {
    "chennai": "MAA", "frankfurt": "FRA", "bangalore": "BLR", "bengaluru": "BLR",
    "paris": "CDG", "singapore": "SIN", "dubai": "DXB", "doha": "DOH",
    "chicago": "ORD", "hong kong": "HKG"
}

AMBIGUOUS_CITIES = {"london", "new york"}

AIRLINE_MAP = {
    "lufthansa": "LH", "lh": "LH", "emirates": "EK", "ek": "EK",
    "air india": "AI", "ai": "AI", "qatar": "QR", "qatar airways": "QR", "qr": "QR",
    "british airways": "BA", "ba": "BA", "turkish": "TK", "turkish cargo": "TK", "tk": "TK",
    "virgin": "VS", "virgin atlantic": "VS", "vs": "VS"
}


def _parse_date(text: str) -> Optional[str]:
    """Parse explicit or relative date expressions."""
    t = text.lower()

    if "next friday" in t:
        return "next Friday"
    if "tomorrow" in t:
        return "tomorrow"
    if "next monday" in t:
        return "next Monday"

    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|september|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b", t)
    if m:
        month_str = m.group(1)[:3].title()
        day_str = m.group(2)
        return f"{month_str} {day_str}"

    m_iso = re.search(r"\b\d{4}-\d{2}-\d{2}\b", t)
    if m_iso:
        return m_iso.group(0)

    return None


def _parse_cargo(text: str) -> Dict[str, Any]:
    """Extract weight, pieces, volume, package type, and dimensions."""
    cargo = {}
    t = text.replace(",", "")

    # 1. Weight (kg)
    m_wt = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilogram|kilograms)\b", t, re.IGNORECASE)
    if m_wt:
        cargo["weight_kg"] = float(m_wt.group(1))

    # 2. Pieces / packages / pallets / boxes
    m_pcs = re.search(r"(\d+)\s*(pallets?|boxes?|cartons?|packages?|pieces?|pkgs?|pcs?)\b", t, re.IGNORECASE)
    if m_pcs:
        cargo["pieces"] = int(m_pcs.group(1))
        cargo["package_type"] = m_pcs.group(2).lower()

    # 3. Volume (cbm / m3)
    m_vol = re.search(r"(\d+(?:\.\d+)?)\s*(?:cbm|m3|cubic\s*metres?|cubic\s*meters?)\b", t, re.IGNORECASE)
    if m_vol:
        cargo["volume_cbm"] = float(m_vol.group(1))

    # 4. Dimensions (e.g. 120 x 100 x 90 cm)
    m_dim = re.search(r"(\d+(?:\.\d+)?)\s*(?:x|\*)\s*(\d+(?:\.\d+)?)\s*(?:x|\*)\s*(\d+(?:\.\d+)?)\s*(?:cm)?", t, re.IGNORECASE)
    if m_dim:
        cargo["dimensions_cm"] = (float(m_dim.group(1)), float(m_dim.group(2)), float(m_dim.group(3)))

    return cargo


def understand(text: str, pending: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses user input into semantic updates, filters, and sorts.
    """
    raw_text = text.strip()
    lower_text = raw_text.lower()

    res = {
        "reset": False,
        "updates": {},
        "filters": {},
        "sort": None,
        "airport_single": None
    }

    # Reset detection
    if re.search(r"\b(reset|start\s*over|start\s*fresh|clear\s*all|clear\s*search)\b", lower_text):
        res["reset"] = True
        return res

    # 1. Handle pending question responses directly
    if pending:
        if pending == "origin":
            for city, code in CITY_TO_AIRPORT.items():
                if city in lower_text:
                    res["updates"]["origin"] = city.title()
                    return res
            code_m = re.search(r"\b([A-Za-z]{3})\b", raw_text)
            if code_m:
                res["updates"]["origin"] = code_m.group(1).upper()
                return res

        elif pending == "destination":
            for city, code in CITY_TO_AIRPORT.items():
                if city in lower_text:
                    res["updates"]["destination"] = city.title()
                    return res
            code_m = re.search(r"\b([A-Za-z]{3})\b", raw_text)
            if code_m:
                res["updates"]["destination"] = code_m.group(1).upper()
                return res

        elif pending == "date":
            dt = _parse_date(raw_text)
            if dt:
                res["updates"]["date"] = dt
                return res

        elif pending == "airport":
            m_route = re.search(r"\b([A-Za-z]{3})\s*(?:to|-)\s*([A-Za-z]{3})\b", raw_text)
            if m_route:
                res["updates"]["origin"] = m_route.group(1).upper()
                res["updates"]["destination"] = m_route.group(2).upper()
                return res
            if "by city" in lower_text:
                res["airport_single"] = "CITY_MODE"
                return res
            single_code = re.search(r"\b([A-Za-z]{3})\b", raw_text)
            if single_code:
                res["airport_single"] = single_code.group(1).upper()
                return res

    # 2. Check for Filter & Sort intents FIRST
    # (Prevents "Show widebody flights" from triggering a new schedule search)
    has_filter_or_sort = False

    # Filters
    # Scenario 14: Direct only
    if re.search(r"\b(?:only\s+show\s+direct|show\s+only\s+direct|direct\s+flights\s+only|direct\s+only|only\s+direct|non-stop|non\s+stop)\b", lower_text):
        res["filters"]["direct_only"] = True
        has_filter_or_sort = True

    # Scenario 15: One stop maximum
    if re.search(r"\b(?:one\s*stop\s*maximum|direct\s+or\s+one-stop|direct\s+or\s+one\s+stop|max\s*1\s*stop)\b", lower_text):
        res["filters"]["max_stops"] = 1
        has_filter_or_sort = True

    # Scenario 16: Specific Airline
    for name, code in AIRLINE_MAP.items():
        if re.search(rf"\b(?:only\s+show\s+{name}|show\s+only\s+{name}|only\s+{name}|{name}\s+only|filter\s+to\s+{name}|{name}\s+options)\b", lower_text):
            res["filters"]["airline"] = code
            has_filter_or_sort = True
            break

    # Scenario 17: Bookable only
    if re.search(r"\b(?:bookable\s*only|only\s+options\s+i\s+can\s+book|show\s+only\s+options\s+i\s+can\s+book|can\s+book)\b", lower_text):
        res["filters"]["bookable"] = True
        has_filter_or_sort = True

    # Scenario 18: Available only
    if re.search(r"\b(?:available\s*only|only\s+available|show\s+only\s+available)\b", lower_text):
        res["filters"]["available"] = True
        has_filter_or_sort = True

    # Scenario 19: Live rates only
    if re.search(r"\b(?:live\s*rates\s*only|only\s+show\s+live\s*rates|only\s+live\s*rates)\b", lower_text):
        res["filters"]["live_rates_only"] = True
        has_filter_or_sort = True

    # Scenario 20: Depart after time
    m_dep = re.search(r"departing\s*after\s*(\d{1,2})(?::(\d{2}))?\s*(pm|am)?", lower_text)
    if m_dep:
        hr = int(m_dep.group(1))
        mn = int(m_dep.group(2) or 0)
        mer = m_dep.group(3)
        if mer == "pm" and hr < 12:
            hr += 12
        elif mer == "am" and hr == 12:
            hr = 0
        res["filters"]["depart_after"] = f"{hr:02d}:{mn:02d}"
        has_filter_or_sort = True

    # Scenario 21: Arrive before time
    m_arr = re.search(r"arriving\s*before\s*(\d{1,2})(?::(\d{2}))?\s*(pm|am)?", lower_text)
    if m_arr:
        hr = int(m_arr.group(1))
        mn = int(m_arr.group(2) or 0)
        mer = m_arr.group(3)
        if mer == "pm" and hr < 12:
            hr += 12
        elif mer == "am" and hr == 12:
            hr = 0
        res["filters"]["arrive_before"] = f"{hr:02d}:{mn:02d}"
        has_filter_or_sort = True

    # Scenario 22: Freighter only
    if re.search(r"\b(?:freighter\s*only|freighter\s*aircraft\s*only|freighters?\s*only)\b", lower_text):
        res["filters"]["body_type"] = "Freighter"
        has_filter_or_sort = True

    # Scenario 23: Widebody preference
    if re.search(r"\b(?:widebody|wide-body|wide\s*body)\b", lower_text):
        res["filters"]["body_type"] = "Widebody"
        has_filter_or_sort = True

    # Scenario 24: Lower CO2
    if re.search(r"\b(?:lower[-\s]*emission|lower[-\s]*co2|lowest[-\s]*co2|eco|greenest)\b", lower_text):
        res["sort"] = "co2"
        has_filter_or_sort = True

    # Scenario 25: Latest acceptance time after 2 PM -> 14:00
    m_lat = re.search(r"accepted\s*after\s*(\d{1,2})(?::(\d{2}))?\s*(pm|am)?", lower_text)
    if m_lat:
        hr = int(m_lat.group(1))
        mn = int(m_lat.group(2) or 0)
        mer = m_lat.group(3)
        if mer == "pm" and hr < 12:
            hr += 12
        res["filters"]["lat_after"] = f"{hr:02d}:{mn:02d}"
        has_filter_or_sort = True

    # Scenario 12 & 13: Sort preferences
    if re.search(r"\b(cheapest|lowest\s*price|lowest\s*total|lowest\s*rate)\b", lower_text):
        res["sort"] = "cheapest"
    if re.search(r"\b(fastest|shortest\s*transit|quickest)\b", lower_text):
        res["sort"] = "fastest"

    # Clear filters
    if re.search(r"\b(show\s*all|clear\s*filters|remove\s*filters)\b", lower_text):
        res["filters"] = {
            "direct_only": False, "max_stops": None, "airline": None,
            "bookable": False, "available": False, "live_rates_only": False,
            "depart_after": None, "arrive_before": None, "body_type": None,
            "lat_after": None
        }
        has_filter_or_sort = True

    # 3. Context updates / modifications (Scenarios 26, 27, 28)
    # Scenario 26: "What about Sep 24 instead?"
    m_date_change = re.search(r"(?:what\s+about|try|change\s+date\s+to|date\s+to)\s+([A-Za-z]+\s+\d+|\d{4}-\d{2}-\d{2})", lower_text)
    if m_date_change:
        res["updates"]["date"] = _parse_date(m_date_change.group(1)) or m_date_change.group(1).title()

    # Scenario 27: "Try Bangalore instead of Chennai."
    m_orig_change = re.search(r"(?:try|use|from|change\s+origin\s+to)\s+([A-Za-z]+)\s+instead", lower_text)
    if m_orig_change:
        place = m_orig_change.group(1).strip()
        res["updates"]["origin"] = place.title()

    # Scenario 28: "Make it 1,200 kg instead."
    m_wt_change = re.search(r"(?:make\s+it|change\s+weight\s+to|weight\s+to)\s+([\d,]+)\s*kg", lower_text)
    if m_wt_change:
        res["updates"]["weight_kg"] = float(m_wt_change.group(1).replace(",", ""))

    # If this message was purely a filter or sort refinement without new search criteria, return now!
    if has_filter_or_sort and not (m_date_change or m_orig_change or m_wt_change or "from" in lower_text or "to" in lower_text):
        return res

    # 4. Search Intent Detection (Rule 1)
    if re.search(r"\b(rate|rates|price|pricing|quote|cheapest\s*air\s*rate|cost)\b", lower_text):
        res["updates"]["intent"] = "rate"
    elif re.search(r"\b(flights\s+from|flight\s+from|show\s+flights|flights\s+to|schedules?)\b", lower_text):
        res["updates"]["intent"] = "schedule"

    # 5. Route Extraction
    # Pattern 5a: "from X to Y"
    m_from_to = re.search(r"\bfrom\s+([A-Za-z\s]+?)\s+to\s+([A-Za-z\s]+?)(?:\s+on|\s+for|\s+next|\s+in|\.|$)", raw_text, re.IGNORECASE)
    if m_from_to:
        orig_raw = m_from_to.group(1).strip()
        dest_raw = m_from_to.group(2).strip()
        if orig_raw.lower() not in NON_LOCATIONS:
            res["updates"]["origin"] = orig_raw.title()
        if dest_raw.lower() not in NON_LOCATIONS:
            res["updates"]["destination"] = dest_raw.title()
    else:
        # Pattern 5b: "X to Y" (e.g. "MAA to FRA next Friday", "Chennai to Frankfurt")
        m_to = re.search(r"\b([A-Za-z]{3,15})\s+to\s+([A-Za-z]{3,15})\b", raw_text, re.IGNORECASE)
        if m_to and not re.search(r"\b(try|change|make)\b", lower_text) and m_to.group(1).lower() not in NON_LOCATIONS and m_to.group(2).lower() not in NON_LOCATIONS:
            res["updates"]["origin"] = m_to.group(1).strip()
            res["updates"]["destination"] = m_to.group(2).strip()
            if "intent" not in res["updates"]:
                res["updates"]["intent"] = "schedule"
        else:
            # Pattern 5c: Single "to Y" (Scenario 2)
            m_only_to = re.search(r"\b(?:flights|schedules|rates)?\s*to\s+([A-Za-z\s]+?)(?:\s+on|\s+for|\s+next|\s+in|\.|$)", raw_text, re.IGNORECASE)
            # Pattern 5d: Single "from X" (Scenario 3)
            m_only_from = re.search(r"\bfrom\s+([A-Za-z\s]+?)(?:\s+on|\s+for|\s+next|\s+in|\.|$)", raw_text, re.IGNORECASE)

            if m_only_to and not m_only_from:
                dest = m_only_to.group(1).strip().title()
                if dest.lower() not in NON_LOCATIONS:
                    res["updates"]["destination"] = dest
            elif m_only_from and not m_only_to:
                orig = m_only_from.group(1).strip().title()
                if orig.lower() not in NON_LOCATIONS:
                    res["updates"]["origin"] = orig

    # 6. Date Extraction
    d = _parse_date(raw_text)
    if d and "date" not in res["updates"]:
        res["updates"]["date"] = d

    # 7. Cargo Extraction
    cargo = _parse_cargo(raw_text)
    res["updates"].update(cargo)

    return res
