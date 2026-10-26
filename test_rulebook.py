"""
test_rulebook.py  -  each test = one scenario from your spreadsheet.
Run with:  pytest
"""

from rulebook import (SearchState, next_action, volume_from_dimensions,
                      chargeable_weight)


def test_scenario_1_complete_schedule_search():
    state = SearchState(intent="schedule", origin="MAA",
                        destination="FRA", date="2026-09-22")
    assert next_action(state)["action"] == "CALL_SCHEDULE_API"


def test_scenario_2_schedule_missing_origin():
    state = SearchState(intent="schedule", destination="FRA", date="2026-09-22")
    result = next_action(state)
    assert result["action"] == "ASK"
    assert result["missing"] == ["origin"]
    assert result["message"] == "Where should the shipment depart from?"


def test_scenario_3_schedule_missing_destination():
    state = SearchState(intent="schedule", origin="MAA", date="2026-09-22")
    result = next_action(state)
    assert result["missing"] == ["destination"]


def test_scenario_4_schedule_missing_date():
    state = SearchState(intent="schedule", origin="MAA", destination="FRA")
    result = next_action(state)
    assert result["missing"] == ["date"]


def test_schedule_never_asks_for_cargo_details():
    # Rule 1: no weight/pieces/dimensions for a schedule-only search
    state = SearchState(intent="schedule", origin="MAA",
                        destination="FRA", date="2026-09-22")
    assert "weight" not in next_action(state).get("missing", [])


def test_scenario_6_schedule_by_city():
    state = SearchState(intent="schedule", origin="Paris",
                        destination="Singapore", date="2026-11-09")
    assert next_action(state)["action"] == "CALL_SCHEDULE_API"


def test_scenario_7_ambiguous_airport():
    state = SearchState(intent="schedule", origin="London",
                        destination="New York", date="2026-09-25")
    result = next_action(state)
    assert result["action"] == "ASK"
    assert result["missing"] == ["airport"]


def test_scenario_8_basic_rate_request_asks_for_cargo():
    state = SearchState(intent="rate", origin="MAA",
                        destination="FRA", date="2026-09-22")
    result = next_action(state)
    assert result["action"] == "ASK"
    assert result["missing"] == ["weight", "pieces", "volume_or_dimensions"]


def test_scenario_9_rate_with_weight_only():
    state = SearchState(intent="rate", origin="MAA", destination="FRA",
                        date="2026-09-22", weight_kg=850)
    result = next_action(state)
    assert result["missing"] == ["pieces", "volume_or_dimensions"]


def test_scenario_10_rate_with_weight_pieces_volume():
    state = SearchState(intent="rate", origin="MAA", destination="FRA",
                        date="2026-09-22", weight_kg=850, pieces=6,
                        volume_cbm=6.5)
    assert next_action(state)["action"] == "CALL_RATE_API"


def test_scenario_11_rate_with_dimensions_instead_of_volume():
    state = SearchState(intent="rate", origin="MAA", destination="FRA",
                        date="2026-09-22", weight_kg=850, pieces=6,
                        dimensions_cm=(120, 100, 90))
    assert next_action(state)["action"] == "CALL_RATE_API"
    # ...and the volume we calculate from those dimensions:
    assert volume_from_dimensions((120, 100, 90), 6) == 6.48
    assert chargeable_weight(850, 6.48) == 1080.0
