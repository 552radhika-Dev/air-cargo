"""
test_scenarios.py - Automated validation suite for all 32 Air Cargo Chatbot Scenarios.
Directly tests the chatbot behavior against Prompt Snippets.xlsx specifications.
"""

import pytest
import bot
from bot import handle_message, SESSIONS, new_session
from rulebook import volume_from_dimensions, chargeable_weight


@pytest.fixture(autouse=True)
def clean_sessions():
    """Ensure each test runs in a clean session state."""
    SESSIONS.clear()


# === 1. Schedule Searches (Scenarios 1 - 7) ===

def test_scenario_01_complete_schedule_search():
    res = handle_message("s1", "Show flights from Chennai to Frankfurt on Sep 22.")
    assert "Found" in res["reply"] or "Searching" in res["reply"]
    assert res["flights"] is not None
    assert len(res["flights"]) > 0
    assert "New search sent" in res["how"]


def test_scenario_02_schedule_missing_origin():
    res = handle_message("s2", "Show flights to Frankfurt on Sep 22.")
    assert res["reply"] == "Where should the shipment depart from?"
    assert res["flights"] is None
    # Follow-up with origin
    res2 = handle_message("s2", "Chennai")
    assert "Found" in res2["reply"]
    assert res2["flights"] is not None


def test_scenario_03_schedule_missing_destination():
    res = handle_message("s3", "Show flights from Chennai on Sep 22.")
    assert res["reply"] == "Where is the shipment going to?"
    assert res["flights"] is None
    # Follow-up
    res2 = handle_message("s3", "Frankfurt")
    assert "Found" in res2["reply"]


def test_scenario_04_schedule_missing_date():
    res = handle_message("s4", "Show flights from Chennai to Frankfurt.")
    assert res["reply"] == "What is the cargo-ready / departure date?"
    assert res["flights"] is None
    # Follow-up
    res2 = handle_message("s4", "Sep 22")
    assert "Found" in res2["reply"]


def test_scenario_05_schedule_shorthand():
    res = handle_message("s5", "MAA to FRA next Friday.")
    assert res["flights"] is not None
    assert len(res["flights"]) > 0


def test_scenario_06_schedule_by_city():
    res = handle_message("s6", "Show flights from Paris to Singapore on Nov 9.")
    assert res["flights"] is not None
    assert len(res["flights"]) > 0


def test_scenario_07_ambiguous_airport():
    res = handle_message("s7", "Show flights from London to New York on Sep 25.")
    assert "Which airports should I use" in res["reply"]
    assert res["flights"] is None
    # User resolves
    res2 = handle_message("s7", "LHR to JFK")
    assert res2["flights"] is not None
    assert len(res2["flights"]) > 0


# === 2. Rate Searches & Cargo Details (Scenarios 8 - 13) ===

def test_scenario_08_basic_rate_request():
    res = handle_message("s8", "Need the best air rate from Chennai to Frankfurt on Sep 22.")
    assert "Please share the cargo weight" in res["reply"]
    assert res["flights"] is None


def test_scenario_09_rate_with_weight_only():
    res = handle_message("s9", "Need rates MAA to FRA Sep 22 for 850 kg.")
    assert "850 kg" in res["reply"]
    assert "pieces" in res["reply"].lower()
    assert res["flights"] is None


def test_scenario_10_rate_with_weight_pieces_volume():
    res = handle_message("s10", "Best rate MAA to FRA Sep 22, 850 kg, 6 pallets, 6.5 CBM.")
    assert res["flights"] is not None
    assert len(res["flights"]) > 0
    # Rates must be present on flights
    assert any(f.get("total_usd") is not None for f in res["flights"])


def test_scenario_11_rate_with_dimensions():
    res = handle_message("s11", "Need rates MAA to FRA Sep 22, 6 pallets, 850 kg, 120 x 100 x 90 cm each.")
    assert res["flights"] is not None
    assert res["state"].get("volume_cbm") == 6.48
    assert res["chargeable_weight"] == 1080.0


def test_scenario_12_cheapest_rate():
    res = handle_message("s12", "Show the cheapest air rate from Chennai to Frankfurt Sep 22 for 850 kg, 6 pallets, 6.5 CBM.")
    assert res["flights"] is not None
    assert res["sort"] == "cheapest"
    prices = [f["total_usd"] for f in res["flights"] if f.get("total_usd")]
    assert prices == sorted(prices)


def test_scenario_13_fastest_option():
    res = handle_message("s13", "Fastest option from MAA to FRA Sep 22.")
    assert res["flights"] is not None
    assert res["sort"] == "fastest"
    durations = [f["duration_h"] for f in res["flights"]]
    assert durations == sorted(durations)


# === 3. Result Refinement & Filters (Scenarios 14 - 25) ===

@pytest.fixture
def active_rate_search():
    """Initializes a search so refinement filters work without new API calls."""
    handle_message("refine", "Best rate MAA to FRA Sep 22, 850 kg, 6 pallets, 6.5 CBM.")
    return "refine"


def test_scenario_14_direct_only(active_rate_search):
    res = handle_message(active_rate_search, "Only show direct flights.")
    assert res["filters"].get("direct_only") is True
    assert all(f["stops"] == 0 for f in res["flights"])
    assert "no new API call" in res["how"]


def test_scenario_15_one_stop_maximum(active_rate_search):
    res = handle_message(active_rate_search, "Show direct or one-stop flights only.")
    assert res["filters"].get("max_stops") == 1
    assert all(f["stops"] <= 1 for f in res["flights"])
    assert "no new API call" in res["how"]


def test_scenario_16_specific_airline(active_rate_search):
    res = handle_message(active_rate_search, "Only show Lufthansa options.")
    assert res["filters"].get("airline") == "LH"
    assert all(f["airline"] == "LH" for f in res["flights"])
    assert "no new API call" in res["how"]


def test_scenario_17_bookable_only(active_rate_search):
    res = handle_message(active_rate_search, "Show only options I can book.")
    assert res["filters"].get("bookable") is True
    assert all(f["bookable"] is True for f in res["flights"])
    assert "no new API call" in res["how"]


def test_scenario_18_available_only(active_rate_search):
    res = handle_message(active_rate_search, "Show only available flights.")
    assert res["filters"].get("available") is True
    assert all(f["available"] is True for f in res["flights"])
    assert "no new API call" in res["how"]


def test_scenario_19_live_rates_only(active_rate_search):
    res = handle_message(active_rate_search, "Only show live rates.")
    assert res["filters"].get("live_rates_only") is True
    assert "no new API call" in res["how"]


def test_scenario_20_depart_after_time(active_rate_search):
    res = handle_message(active_rate_search, "Only flights departing after 6 PM.")
    assert res["filters"].get("depart_after") == "18:00"
    for f in res["flights"]:
        time_str = f["departure"].split(" ")[1]
        assert time_str >= "18:00"
    assert "no new API call" in res["how"]


def test_scenario_21_arrive_before_time(active_rate_search):
    res = handle_message(active_rate_search, "Show flights arriving before 10 AM.")
    assert res["filters"].get("arrive_before") == "10:00"
    for f in res["flights"]:
        time_str = f["arrival"].split(" ")[1]
        assert time_str < "10:00"
    assert "no new API call" in res["how"]


def test_scenario_22_freighter_only(active_rate_search):
    res = handle_message(active_rate_search, "Show freighter aircraft only.")
    assert res["filters"].get("body_type") == "Freighter"
    assert all("freighter" in f["body_type"].lower() for f in res["flights"])
    assert "no new API call" in res["how"]


def test_scenario_23_widebody_preference(active_rate_search):
    res = handle_message(active_rate_search, "Show widebody flights.")
    assert res["filters"].get("body_type") == "Widebody"
    assert all("widebody" in f["body_type"].lower() for f in res["flights"])
    assert "no new API call" in res["how"]


def test_scenario_24_lower_co2(active_rate_search):
    res = handle_message(active_rate_search, "Show the lower-emission options first.")
    assert res["sort"] == "co2"
    co2_vals = [f["co2"] for f in res["flights"]]
    assert co2_vals == sorted(co2_vals)
    assert "no new API call" in res["how"]


def test_scenario_25_latest_acceptance_time(active_rate_search):
    res = handle_message(active_rate_search, "Show flights where cargo can be accepted after 2 PM.")
    assert res["filters"].get("lat_after") == "14:00"
    for f in res["flights"]:
        lat = f.get("latest_acceptance_time")
        if lat and " " in lat:
            assert lat.split(" ")[1] >= "14:00"


# === 4. Search Modifications / Re-runs (Scenarios 26 - 28) ===

def test_scenario_26_change_date(active_rate_search):
    res = handle_message(active_rate_search, "What about Sep 24 instead?")
    assert "Sep 24" in res["reply"] or "2026-09-24" in str(res["state"].get("date"))
    assert "New search sent" in res["how"]


def test_scenario_27_change_origin(active_rate_search):
    res = handle_message(active_rate_search, "Try Bangalore instead of Chennai.")
    assert "Bangalore" in res["reply"] or "BLR" in res["reply"]
    assert "New search sent" in res["how"]


def test_scenario_28_change_cargo(active_rate_search):
    res = handle_message(active_rate_search, "Make it 1,200 kg instead.")
    assert "1200" in res["reply"] or "1,200" in res["reply"]
    assert res["state"].get("weight_kg") == 1200.0
    assert "New search sent" in res["how"]


# === 5. Edge Cases & Errors (Scenarios 29 - 32) ===

def test_scenario_29_no_schedule_results():
    res = handle_message("s29", "Show flights from ZZZ to FRA on Sep 22.")
    assert "couldn't find matching schedules" in res["reply"].lower()
    assert res["flights"] == []


def test_scenario_30_no_rate_results():
    res = handle_message("s30", "Need rates NORATE to FRA Sep 22, 850 kg, 6 pallets, 6.5 CBM.")
    assert "no matching rate is available" in res["reply"].lower()
    assert res["flights"] == []


def test_scenario_31_unavailable_due_to_cargo():
    res = handle_message("s31", "Rate result is unavailable because dimensions are not loadable.")
    assert "dimensions are not loadable" in res["reply"]


def test_scenario_32_search_error_for_some_airlines():
    res = handle_message("s32", "Show flights from Chennai to Frankfurt on Sep 22.")
    assert "some airlines did not respond" in res["reply"]
    assert len(res["errors"]) > 0
    assert len(res["flights"]) > 0
