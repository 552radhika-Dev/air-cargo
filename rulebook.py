"""
rulebook.py - Phase 1 & 2
The "rulebook": given what we know so far about a search,
decide the next step (ask the user something, or call the API).
Enforces the 9 chatbot rules specified in Prompt Snippets.xlsx.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Union, Dict, Any

AMBIGUOUS_PLACES = {"london", "new york"}

# Standard air-cargo volumetric ratio: 1 CBM = 166.67 kg (6000 cm3 per kg)
CM3_PER_KG = 6000


@dataclass
class SearchState:
    """Everything we know so far about the user's search."""
    intent: Optional[str] = None          # "schedule" or "rate"
    origin: Optional[str] = None          # e.g. "MAA" or "Chennai"
    destination: Optional[str] = None     # e.g. "FRA" or "Frankfurt"
    date: Optional[str] = None            # e.g. "2026-09-22" or "Sep 22"
    weight_kg: Optional[float] = None
    pieces: Optional[int] = None
    volume_cbm: Optional[float] = None
    dimensions_cm: Optional[tuple] = None  # (length, width, height) of ONE piece in cm
    package_type: Optional[str] = None    # e.g. "pallet", "box"


def _to_state(state: Union[SearchState, Dict[str, Any]]) -> SearchState:
    if isinstance(state, SearchState):
        return state
    # Handle dict
    return SearchState(
        intent=state.get("intent"),
        origin=state.get("origin"),
        destination=state.get("destination"),
        date=state.get("date"),
        weight_kg=state.get("weight_kg"),
        pieces=state.get("pieces"),
        volume_cbm=state.get("volume_cbm"),
        dimensions_cm=state.get("dimensions_cm"),
        package_type=state.get("package_type"),
    )


def volume_from_dimensions(dimensions_cm, pieces=1):
    """Turn box size into total volume in cubic metres (CBM)."""
    if not dimensions_cm or not pieces:
        return None
    length, width, height = dimensions_cm
    return round(float(length) * float(width) * float(height) * int(pieces) / 1_000_000, 2)


def chargeable_weight(weight_kg, volume_cbm):
    """Airlines charge for whichever is bigger: gross weight or volumetric weight."""
    if weight_kg is None and volume_cbm is None:
        return 0.0
    w = float(weight_kg or 0.0)
    v = float(volume_cbm or 0.0)
    volumetric_kg = v * 1_000_000 / CM3_PER_KG
    return round(max(w, volumetric_kg), 1)


def is_ambiguous(place: Optional[str]) -> bool:
    """Check if a city/location has multiple major commercial airports."""
    if not place:
        return False
    return place.strip().lower() in AMBIGUOUS_PLACES


_is_ambiguous = is_ambiguous  # Backwards compatibility


def missing_cargo_details(state: Union[SearchState, Dict[str, Any]]):
    """For a RATE search: which cargo details are still missing? (Rule 4 & 5)"""
    st = _to_state(state)
    missing = []
    if st.weight_kg is None:
        missing.append("weight")
    if st.pieces is None:
        missing.append("pieces")
    # Volume OR dimensions is sufficient - volume can be calculated from dimensions (Rule 5)
    if st.volume_cbm is None and st.dimensions_cm is None:
        missing.append("volume_or_dimensions")
    return missing


def pending_field(state: Union[SearchState, Dict[str, Any]]) -> Optional[str]:
    """Identify which specific field is currently blocking an API call."""
    st = _to_state(state)
    if st.origin is None:
        return "origin"
    if st.destination is None:
        return "destination"
    if st.date is None:
        return "date"
    if is_ambiguous(st.origin) or is_ambiguous(st.destination):
        return "airport"
    if st.intent is None:
        return "intent"
    if st.intent == "rate":
        missing = missing_cargo_details(st)
        if missing:
            return "cargo"
    return None


def next_question(state: Union[SearchState, Dict[str, Any]]) -> Optional[str]:
    """Generates a friendly prompt for the next missing information."""
    field = pending_field(state)
    if field == "origin":
        return "Where should the shipment depart from?"
    if field == "destination":
        return "Where is the shipment going to?"
    if field == "date":
        return "What is the cargo-ready / departure date?"
    if field == "airport":
        return "Which airports should I use — for example LHR to JFK, or should I search by city?"
    if field == "intent":
        return "Would you like flight schedules or rates?"
    if field == "cargo":
        missing = missing_cargo_details(state)
        return _cargo_question(_to_state(state), missing)
    return None


def next_action(state: Union[SearchState, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Decides the next step based on the 9 Chatbot Rules.
    Returns:
      {"action": "ASK", "missing": [...], "message": "..."}
      {"action": "CALL_SCHEDULE_API"}
      {"action": "CALL_RATE_API"}
    """
    st = _to_state(state)

    # Step 1: Minimum information before API call (Rules 2 & 3)
    # Origin + Destination + Departure / Cargo Ready Date
    if st.origin is None:
        return {"action": "ASK", "missing": ["origin"],
                "message": "Where should the shipment depart from?"}
    if st.destination is None:
        return {"action": "ASK", "missing": ["destination"],
                "message": "Where is the shipment going to?"}
    if st.date is None:
        return {"action": "ASK", "missing": ["date"],
                "message": "What is the cargo-ready / departure date?"}

    # Step 2: Places with multiple airports need clarification (Scenario 7)
    if is_ambiguous(st.origin) or is_ambiguous(st.destination):
        return {"action": "ASK", "missing": ["airport"],
                "message": "Which airports should I use — for example LHR to JFK, or should I search by city?"}

    # Step 3: Intent detection (Rule 1)
    # Schedule search NEVER asks for cargo details (Rule 1 & 2)
    if st.intent == "schedule":
        return {"action": "CALL_SCHEDULE_API"}

    # Step 4: Rate search needs cargo details (Rule 4 & 5)
    if st.intent == "rate":
        missing = missing_cargo_details(st)
        if missing:
            return {"action": "ASK", "missing": missing,
                    "message": _cargo_question(st, missing)}
        return {"action": "CALL_RATE_API"}

    # Intent is unspecified - default to schedule if route/date given, or ask
    return {"action": "CALL_SCHEDULE_API"}


def _cargo_question(state: SearchState, missing: list) -> str:
    """Friendly question for missing cargo details (Scenario 8 & 9)."""
    # Scenario 8: No cargo details given yet
    if len(missing) == 3:
        return ("Sure. Please share the cargo weight, number of pieces/packages "
                "and volume. If you have dimensions, you can provide those "
                "instead of volume.")
    
    # Scenario 9: Weight is known, pieces/volume missing
    if state.weight_kg is not None and "weight" not in missing:
        weight_str = f"{int(state.weight_kg) if state.weight_kg.is_integer() else state.weight_kg} kg"
        parts = []
        if "pieces" in missing:
            parts.append("how many pieces/packages there are")
        if "volume_or_dimensions" in missing:
            parts.append("what is the total volume or package dimensions")
        return f"Got it — {weight_str}. " + " and ".join(parts).capitalize() + "?"

    # Other combinations
    parts = []
    if "weight" in missing:
        parts.append("the cargo weight")
    if "pieces" in missing:
        parts.append("number of pieces/packages")
    if "volume_or_dimensions" in missing:
        parts.append("total volume or package dimensions")
    return "Got it. Could you share " + " and ".join(parts) + "?"
