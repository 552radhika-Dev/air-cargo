"""
app.py - FastAPI Web Service for Air Cargo Chatbot.
Serves interactive chat API, 32 scenario runner endpoints, and the frontend web UI.
"""

import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

import bot

app = FastAPI(title="Air Cargo AI Assistant", version="1.0.0")

# Predefined 32 Scenarios Catalog matching Prompt Snippets.xlsx
SCENARIOS = [
    # Category 1: Schedule Search
    {"id": 1, "category": "Schedule Search", "title": "Complete Schedule Search",
     "prompt": "Show flights from Chennai to Frankfurt on Sep 22.",
     "desc": "Extracts MAA/FRA/Sep 22, detects schedule intent, searches immediately."},
    {"id": 2, "category": "Schedule Search", "title": "Missing Origin",
     "prompt": "Show flights to Frankfurt on Sep 22.",
     "desc": "Asks only for missing departure location."},
    {"id": 3, "category": "Schedule Search", "title": "Missing Destination",
     "prompt": "Show flights from Chennai on Sep 22.",
     "desc": "Asks only for missing arrival destination."},
    {"id": 4, "category": "Schedule Search", "title": "Missing Date",
     "prompt": "Show flights from Chennai to Frankfurt.",
     "desc": "Asks only for cargo-ready / departure date."},
    {"id": 5, "category": "Schedule Search", "title": "Schedule Shorthand",
     "prompt": "MAA to FRA next Friday.",
     "desc": "Infers schedule search from shorthand route and relative date."},
    {"id": 6, "category": "Schedule Search", "title": "Schedule by City",
     "prompt": "Show flights from Paris to Singapore on Nov 9.",
     "desc": "Resolves city pairs into airport hubs and searches."},
    {"id": 7, "category": "Schedule Search", "title": "Ambiguous Airport Market",
     "prompt": "Show flights from London to New York on Sep 25.",
     "desc": "Detects multiple airports in London/New York; asks for clarification."},

    # Category 2: Rate Search & Cargo Details
    {"id": 8, "category": "Rate Search", "title": "Basic Rate Request",
     "prompt": "Need the best air rate from Chennai to Frankfurt on Sep 22.",
     "desc": "Detects rate intent; asks for weight, pieces, and volume/dimensions."},
    {"id": 9, "category": "Rate Search", "title": "Rate with Weight Only",
     "prompt": "Need rates MAA to FRA Sep 22 for 850 kg.",
     "desc": "Captures weight; asks for missing pieces and volume/dimensions."},
    {"id": 10, "category": "Rate Search", "title": "Rate with Full Cargo",
     "prompt": "Best rate MAA to FRA Sep 22, 850 kg, 6 pallets, 6.5 CBM.",
     "desc": "Captures all cargo fields, calls Quote & Book rate API."},
    {"id": 11, "category": "Rate Search", "title": "Rate with Dimensions (Volume Derived)",
     "prompt": "Need rates MAA to FRA Sep 22, 6 pallets, 850 kg, 120 x 100 x 90 cm each.",
     "desc": "Calculates volume (6.48 CBM) and chargeable weight (1080 kg) from dimensions."},
    {"id": 12, "category": "Rate Search", "title": "Cheapest Air Rate",
     "prompt": "Show the cheapest air rate from Chennai to Frankfurt Sep 22 for 850 kg, 6 pallets, 6.5 CBM.",
     "desc": "Performs rate search and sorts by lowest total rate first."},
    {"id": 13, "category": "Rate Search", "title": "Fastest Flight Option",
     "prompt": "Fastest option from MAA to FRA Sep 22.",
     "desc": "Searches schedules and sorts by shortest transit duration first."},

    # Category 3: Filters & Refinements (Local - Rule 6)
    {"id": 14, "category": "Refinement & Filters", "title": "Direct Flights Only",
     "prompt": "Only show direct flights.",
     "desc": "Filters existing results to 0 stops (no new API call)."},
    {"id": 15, "category": "Refinement & Filters", "title": "One Stop Maximum",
     "prompt": "Show direct or one-stop flights only.",
     "desc": "Filters existing results to stops <= 1 (no new API call)."},
    {"id": 16, "category": "Refinement & Filters", "title": "Specific Airline (Lufthansa)",
     "prompt": "Only show Lufthansa options.",
     "desc": "Filters current results to Lufthansa / LH (no new API call)."},
    {"id": 17, "category": "Refinement & Filters", "title": "Bookable Only",
     "prompt": "Show only options I can book.",
     "desc": "Filters current results by features.bookable == true."},
    {"id": 18, "category": "Refinement & Filters", "title": "Available Only",
     "prompt": "Show only available flights.",
     "desc": "Filters current results by available == true."},
    {"id": 19, "category": "Refinement & Filters", "title": "Live Rates Only",
     "prompt": "Only show live rates.",
     "desc": "Filters rates to live pricing requests."},
    {"id": 20, "category": "Refinement & Filters", "title": "Depart After Time",
     "prompt": "Only flights departing after 6 PM.",
     "desc": "Filters departure time >= 18:00."},
    {"id": 21, "category": "Refinement & Filters", "title": "Arrive Before Time",
     "prompt": "Show flights arriving before 10 AM.",
     "desc": "Filters arrival time < 10:00."},
    {"id": 22, "category": "Refinement & Filters", "title": "Freighter Aircraft Only",
     "prompt": "Show freighter aircraft only.",
     "desc": "Filters aircraft bodyType to Freighter."},
    {"id": 23, "category": "Refinement & Filters", "title": "Widebody Preference",
     "prompt": "Show widebody flights.",
     "desc": "Filters aircraft bodyType to Widebody."},
    {"id": 24, "category": "Refinement & Filters", "title": "Lower CO2 Emission",
     "prompt": "Show the lower-emission options first.",
     "desc": "Sorts current flights by CO2 kg ascending."},
    {"id": 25, "category": "Refinement & Filters", "title": "Latest Acceptance Time",
     "prompt": "Show flights where cargo can be accepted after 2 PM.",
     "desc": "Filters latestAcceptanceTime >= 14:00."},

    # Category 4: Context Modifications (Re-runs - Rule 7)
    {"id": 26, "category": "Search Context Updates", "title": "Change Date After Results",
     "prompt": "What about Sep 24 instead?",
     "desc": "Reuses route & cargo, updates departureDate, re-runs API."},
    {"id": 27, "category": "Search Context Updates", "title": "Change Origin After Results",
     "prompt": "Try Bangalore instead of Chennai.",
     "desc": "Reuses destination, date & cargo, updates origin to BLR, re-runs API."},
    {"id": 28, "category": "Search Context Updates", "title": "Change Cargo Weight",
     "prompt": "Make it 1,200 kg instead.",
     "desc": "Updates cargo weight to 1200 kg, recalculates chargeable weight, re-runs rate API."},

    # Category 5: Edge Cases & Errors (Rule 8 & 9)
    {"id": 29, "category": "Edge Cases & Errors", "title": "No Schedule Results",
     "prompt": "Show flights from ZZZ to FRA on Sep 22.",
     "desc": "Distinguishes 'no flight results' from API error; offers nearby suggestions."},
    {"id": 30, "category": "Edge Cases & Errors", "title": "No Rate Results Available",
     "prompt": "Need rates NORATE to FRA Sep 22, 850 kg, 6 pallets, 6.5 CBM.",
     "desc": "Distinguishes 'flight found but no rate' from no flights."},
    {"id": 31, "category": "Edge Cases & Errors", "title": "Unavailable Due to Cargo Loadability",
     "prompt": "Rate result is unavailable because dimensions are not loadable.",
     "desc": "Displays specific loadability error reason on flight option."},
    {"id": 32, "category": "Edge Cases & Errors", "title": "Search Error for Some Airlines",
     "prompt": "Show flights from Chennai to Frankfurt on Sep 22.",
     "desc": "Displays usable flights while surfacing partial airline provider timeout warning."}
]


class ChatRequest(BaseModel):
    session_id: str = "default_user"
    message: str


class ResetRequest(BaseModel):
    session_id: str = "default_user"


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Processes chat messages and returns structured bot response."""
    return bot.handle_message(req.session_id, req.message)


@app.post("/api/reset")
def reset_endpoint(req: ResetRequest):
    """Resets the user session to blank state."""
    bot.SESSIONS[req.session_id] = bot.new_session()
    return {"status": "reset", "message": "Session reset successfully."}


@app.get("/api/scenarios")
def get_scenarios():
    """Returns the catalog of 32 test scenarios for one-click UI testing."""
    return SCENARIOS


@app.get("/api/state")
def get_state(session_id: str = "default_user"):
    """Returns the active search state and active filters for a session."""
    s = bot.SESSIONS.get(session_id, bot.new_session())
    return {
        "state": s.get("search", {}),
        "filters": s.get("filters", {}),
        "sort": s.get("sort"),
        "pending": s.get("pending"),
        "report": s.get("report")
    }


# Ensure static directory exists
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Serves the main dashboard application."""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return "<h1>Air Cargo Chatbot Backend is Running.</h1>"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
