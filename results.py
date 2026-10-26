"""
results.py - Filtering and sorting on cleaned air cargo flights.
Implements Rule 6: Result filters/sorts work locally without a new API call.
Supports all Section 3 fields from Prompt Snippets.xlsx.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional


def apply_filters(flights: Optional[List[Dict[str, Any]]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Applies conversational filter criteria to current flight results.
    """
    if not flights:
        return []
    
    res = list(flights)

    # 1. Direct only (Scenario 14)
    if filters.get("direct_only"):
        res = [f for f in res if f.get("stops", 0) == 0]

    # 2. Max stops (Scenario 15: direct or 1-stop)
    if filters.get("max_stops") is not None:
        res = [f for f in res if f.get("stops", 0) <= filters["max_stops"]]

    # 3. Airline filter (Scenario 16: e.g. Lufthansa / LH)
    if filters.get("airline"):
        target = filters["airline"].strip().upper()
        res = [f for f in res if f.get("airline", "").upper() == target]

    # 4. Bookable only (Scenario 17: features.bookable == True)
    if filters.get("bookable"):
        res = [f for f in res if f.get("bookable") is True]

    # 5. Available only (Scenario 18: available == True)
    if filters.get("available"):
        res = [f for f in res if f.get("available") is True]

    # 6. Live rates only (Scenario 19)
    if filters.get("live_rates_only"):
        def has_live_rate(f):
            rates = f.get("rates", [])
            return any(r.get("type", "").upper() == "LIVE" for r in rates)
        res = [f for f in res if has_live_rate(f)]

    # 7. Depart after time (Scenario 20: e.g. "18:00")
    if filters.get("depart_after"):
        target_time = filters["depart_after"]  # e.g. "18:00"
        def departs_after(f):
            dep = f.get("departure", "")
            if " " in dep:
                time_part = dep.split(" ")[1]
                return time_part >= target_time
            return True
        res = [f for f in res if departs_after(f)]

    # 8. Arrive before time (Scenario 21: e.g. "10:00")
    if filters.get("arrive_before"):
        target_time = filters["arrive_before"]  # e.g. "10:00"
        def arrives_before(f):
            arr = f.get("arrival", "")
            if " " in arr:
                time_part = arr.split(" ")[1]
                return time_part < target_time
            return True
        res = [f for f in res if arrives_before(f)]

    # 9. Body type (Scenario 22: Freighter, Scenario 23: Widebody)
    if filters.get("body_type"):
        target_bt = filters["body_type"].strip().lower()
        res = [f for f in res if target_bt in f.get("body_type", "").lower()]

    # 10. Latest acceptance time (Scenario 25: accepted after "14:00")
    if filters.get("lat_after"):
        target_lat = filters["lat_after"]  # e.g. "14:00"
        def lat_after(f):
            lat = f.get("latest_acceptance_time", "")
            if not lat:
                return False
            time_part = lat.split(" ")[1] if " " in lat else lat
            return time_part >= target_lat
        res = [f for f in res if lat_after(f)]

    return res


def sort_flights(flights: Optional[List[Dict[str, Any]]], sort_by: Optional[str]) -> List[Dict[str, Any]]:
    """
    Sorts flight results according to user preference or defaults.
    Options: 'cheapest', 'fastest', 'departure', 'co2'
    """
    if not flights:
        return []

    res = list(flights)

    if sort_by == "cheapest":
        # Scenario 12: Lowest total price first (None prices at the end)
        res.sort(key=lambda f: (f.get("total_usd") is None, f.get("total_usd") or float("inf")))
    elif sort_by == "fastest":
        # Scenario 13: Shortest duration first
        res.sort(key=lambda f: (f.get("duration_h") is None, f.get("duration_h") or float("inf")))
    elif sort_by == "co2":
        # Scenario 24: Lower CO2 emission first
        res.sort(key=lambda f: (f.get("co2") is None, f.get("co2") or float("inf")))
    elif sort_by == "departure":
        # Earliest departure time first
        res.sort(key=lambda f: f.get("departure", ""))

    return res
