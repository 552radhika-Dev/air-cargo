# Air Cargo Conversational Chatbot Engine

A complete conversational air cargo chatbot adhering to the specifications in `Prompt Snippets.xlsx`. Supports **Schedule Search**, **Rate Search**, **32 Scenarios**, **Section 3 Filter & Sort capabilities**, and strictly enforces the **9 Chatbot Rules**. Integrated with a Mock CargoAI service with realistic multi-carrier flight data.

---

## 🚀 Key Features

1. **Two Search Modalities**:
   - **Schedule Search**: Requires only Origin, Destination, and Departure/Cargo-ready Date. Adheres to Rule 1 & Rule 2: never requests weight, pieces, or dimensions for schedule-only queries.
   - **Rate Search**: Requires route and pricing cargo details (Weight, Pieces, Volume or Dimensions). Automatically derives Volume ($CBM = L \times W \times H \times pieces / 1,000,000$) and Chargeable Weight ($max(Weight, Volume \times 1,000,000 / 6000)$) according to Rule 5.

2. **9 Chatbot Rules Enforced**:
   - **Rule 1**: Detects intent first (`schedule` vs `rate`).
   - **Rule 2**: Origin + Destination + Date are sufficient for schedule search.
   - **Rule 3**: Asks only for missing required fields without repeating questions.
   - **Rule 4**: Gathers required cargo parameters for rate calculations.
   - **Rule 5**: Accepts volume or calculates it from dimensions; never forces dimensions if volume is provided.
   - **Rule 6**: Conversation result filters (airline, direct flights, departure/arrival times, freighter/widebody, bookable, available, CO2, price) execute locally on existing flight results without a new API call.
   - **Rule 7**: Reruns CargoAI API search only when core parameters change (origin, destination, date, or cargo weight).
   - **Rule 8**: Distinct states for no schedule, no rate found, cargo loadability errors, and API timeouts.
   - **Rule 9**: Displays usable flights while separately surfacing airline provider warnings when partial timeouts occur.

3. **32 Scenarios Supported**:
   - **Scenarios 1–7 (Schedule Searches)**: Complete queries, missing origin/destination/date, shorthand dates, city hubs (Paris, Singapore), and ambiguous airport markets (London, New York).
   - **Scenarios 8–13 (Rate Searches & Cargo)**: Rate requests, weight-only, full cargo, dimensions calculation, cheapest rate sort, fastest transit sort.
   - **Scenarios 14–25 (Local Filters & Refinements)**: Direct only, max 1 stop, specific airline (Lufthansa), bookable only, available only, live rates only, depart after 6 PM, arrive before 10 AM, freighter aircraft, widebody aircraft, lower CO2 emission sort, latest acceptance time cutoff.
   - **Scenarios 26–28 (Context Updates & Re-runs)**: Change date, change origin, update cargo weight.
   - **Scenarios 29–32 (Edge Cases & Errors)**: No schedule results, rateless flights, cargo dimensions not loadable error, partial airline provider timeouts.

4. **Interactive Web Application**:
   - **32 Scenario Spec Runner**: 1-click execution for all 32 scenarios categorized by type.
   - **Conversational Chat Interface**: Real-time response with mode badges indicating `CargoAI API Re-run (Rule 7)` vs `Local Result Filter (Rule 6)`.
   - **Flight Results Cards**: Full Section 3 fields (Airline code & name, Flight number, Timeline, Stops, Body type, Aircraft code, CO2 kg, LAT, Bookable, Rate type, Total USD).
   - **Session State Inspector**: Real-time display of Gross Weight, Volume, Chargeable Weight, and active filters.
   - **Data Cleaning Report**: Live metrics of rows in, rows out, airline codes standardized, and currency conversions.

---

## 📂 Project Structure

- `bot.py`: Multi-turn conversational session manager and coordinator.
- `rulebook.py`: Rule decision engine implementing the 9 Chatbot Rules.
- `brain.py`: NLU entity and intent extraction pipeline.
- `cargo_client.py`: Mock CargoAI Routes & Schedules and Quote & Book service.
- `cleaning.py` / `cleaning_lite.py`: Raw payload standardization, deduplication, and data cleaning.
- `results.py`: Local filter and sort engine (Rule 6).
- `app.py`: FastAPI web service exposing REST APIs and hosting the UI.
- `static/`: Modern glassmorphic Web UI (`index.html`, `style.css`, `app.js`).
- `test_rulebook.py`: Rulebook unit tests.
- `test_scenarios.py`: Full pytest test suite covering all 32 scenarios.

---

## 🧪 Running the Tests

To run the automated test suite across all 32 scenarios and the rulebook:

```bash
pytest
```

All 43 tests pass with 100% test coverage for the specification.

---

## 🌐 Running the Web Application

To start the local web application:

```bash
python app.py
```

Or with Uvicorn directly:

```bash
uvicorn app:app --port 8000 --reload
```

Then open your browser at:
**`http://127.0.0.1:8000`**
