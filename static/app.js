/**
 * app.js - Frontend client for Air Cargo AI Assistant
 */

const SESSION_ID = "default_user";
let currentScenarios = [];
let currentCategory = "All";

document.addEventListener("DOMContentLoaded", () => {
  initScenarios();
  initChatForm();
  initViewTabs();
  initResetButton();
});

// === 1. Scenarios Catalog & Runner ===

async function initScenarios() {
  try {
    const res = await fetch("/api/scenarios");
    currentScenarios = await res.json();
    renderScenarios();
    setupCategoryTabs();
  } catch (err) {
    console.error("Failed to load scenarios:", err);
  }
}

function setupCategoryTabs() {
  const tabs = document.querySelectorAll("#category-tabs .tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentCategory = tab.getAttribute("data-category");
      renderScenarios();
    });
  });
}

function renderScenarios() {
  const container = document.getElementById("scenarios-list");
  container.innerHTML = "";

  const filtered = currentCategory === "All"
    ? currentScenarios
    : currentScenarios.filter(s => s.category === currentCategory);

  filtered.forEach(sc => {
    const card = document.createElement("div");
    card.className = "scenario-card";
    card.onclick = () => sendPrompt(sc.prompt);

    card.innerHTML = `
      <div class="sc-header">
        <span class="sc-num">#${sc.id}</span>
        <span class="sc-title">${escapeHtml(sc.title)}</span>
      </div>
      <div class="sc-desc">${escapeHtml(sc.desc)}</div>
      <div class="sc-prompt">${escapeHtml(sc.prompt)}</div>
    `;
    container.appendChild(card);
  });
}

// === 2. Chat Form & Messaging ===

function initChatForm() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendPrompt(text);
  });
}

async function sendPrompt(text) {
  appendUserMessage(text);
  showTypingIndicator();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: SESSION_ID, message: text })
    });
    const data = await res.json();
    removeTypingIndicator();
    handleBotResponse(data);
  } catch (err) {
    removeTypingIndicator();
    appendBotMessage(`Error communicating with backend: ${err.message}`, null);
  }
}

function appendUserMessage(text) {
  const container = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "message-bubble user-message";
  div.innerHTML = `
    <div class="avatar">👤</div>
    <div class="bubble-content">
      <p>${escapeHtml(text)}</p>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendBotMessage(text, how, scenario) {
  const container = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "message-bubble bot-message";

  let tagHtml = "";
  if (how) {
    tagHtml = `<div class="action-tag">⚡ ${escapeHtml(how)}</div>`;
  }
  if (scenario) {
    tagHtml += ` <div class="action-tag" style="color:#38bdf8;">Scenario ${scenario}</div>`;
  }

  div.innerHTML = `
    <div class="avatar">✈️</div>
    <div class="bubble-content">
      <p>${escapeHtml(text)}</p>
      ${tagHtml}
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
  const container = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.id = "typing-bubble";
  div.className = "message-bubble bot-message";
  div.innerHTML = `
    <div class="avatar">✈️</div>
    <div class="bubble-content" style="color: #94a3b8;">
      Thinking...
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-bubble");
  if (el) el.remove();
}

// === 3. Handling Bot Results & UI Updates ===

function handleBotResponse(data) {
  appendBotMessage(data.reply, data.how, data.scenario);
  updateActionModeBadge(data.how);
  updateFlightCards(data.flights);
  updateStateInspector(data.state, data.chargeable_weight, data.filters, data.sort, data.pending);
  updateCleaningReport(data.report);
}

function updateActionModeBadge(how) {
  const badge = document.getElementById("action-mode-badge");
  if (!how) {
    badge.className = "mode-badge badge-idle";
    badge.textContent = "Ready";
  } else if (how.includes("New search")) {
    badge.className = "mode-badge badge-new-api";
    badge.textContent = "CargoAI API Re-run (Rule 7)";
  } else {
    badge.className = "mode-badge badge-local-filter";
    badge.textContent = "Local Result Filter (Rule 6)";
  }
}

function updateFlightCards(flights) {
  const container = document.getElementById("flight-cards-container");
  const emptyState = document.getElementById("empty-results");
  const countEl = document.getElementById("flights-count");

  if (!flights || flights.length === 0) {
    container.innerHTML = "";
    emptyState.style.display = "block";
    countEl.textContent = "0";
    return;
  }

  emptyState.style.display = "none";
  countEl.textContent = flights.length.toString();
  container.innerHTML = "";

  flights.forEach(f => {
    const card = document.createElement("div");
    card.className = "flight-card" + (!f.available ? " unavailable-card" : "");

    // Rate display
    let rateHtml = "";
    if (f.total_usd !== null && f.total_usd !== undefined) {
      const liveTag = f.rates && f.rates.length > 0 && f.rates[0].type === "LIVE"
        ? '<span class="rate-type-tag rate-live">LIVE RATE</span>'
        : '<span class="rate-type-tag rate-contract">CONTRACT</span>';

      rateHtml = `
        <div class="rate-badge-main">
          <div class="total-usd">$${f.total_usd.toFixed(2)}</div>
          ${liveTag}
        </div>
      `;
    }

    // Badges
    const stopsText = f.stops === 0 ? "Non-stop" : `${f.stops} stop${f.stops > 1 ? 's' : ''}`;
    const unavailNotice = (!f.available && f.available_reason)
      ? `<div class="unavail-banner">⚠️ Unavailable: ${escapeHtml(f.available_reason)}</div>`
      : "";

    card.innerHTML = `
      <div class="card-top">
        <div class="airline-badge-group">
          <span class="airline-code-tag">${escapeHtml(f.airline)}</span>
          <div>
            <div class="flight-num">${escapeHtml(f.flight_no)}</div>
            <div class="airline-name">${escapeHtml(f.airline)}</div>
          </div>
        </div>
        ${rateHtml}
      </div>

      <div class="route-timeline">
        <div class="time-loc">
          <span class="airport-code">${escapeHtml(f.origin)}</span>
          <span class="time-str">${f.departure.split(" ")[1] || f.departure}</span>
        </div>
        <div class="flight-path">
          <span class="duration-str">${f.duration_h} hrs</span>
          <div class="path-line"></div>
          <span class="path-stops">${stopsText}</span>
        </div>
        <div class="time-loc" style="text-align: right;">
          <span class="airport-code">${escapeHtml(f.destination)}</span>
          <span class="time-str">${f.arrival.split(" ")[1] || f.arrival}</span>
        </div>
      </div>

      <div class="card-badges">
        <span class="tag-badge ${f.body_type === 'Freighter' ? 'tag-freighter' : 'tag-widebody'}">
          ${escapeHtml(f.body_type)} (${escapeHtml(f.aircraft_code || '')})
        </span>
        <span class="tag-badge tag-co2">🌱 ${f.co2} kg CO2</span>
        ${f.latest_acceptance_time ? `<span class="tag-badge tag-lat">LAT: ${escapeHtml(f.latest_acceptance_time.split(" ")[1] || f.latest_acceptance_time)}</span>` : ''}
        ${f.bookable ? `<span class="tag-badge tag-bookable">✓ Bookable</span>` : ''}
      </div>
      ${unavailNotice}
    `;

    container.appendChild(card);
  });
}

// === 4. State Inspector & Cleaning Report ===

function updateStateInspector(state, chgWeight, filters, sort, pending) {
  if (!state) return;
  document.getElementById("st-intent").textContent = state.intent ? state.intent.toUpperCase() : "-";
  document.getElementById("st-origin").textContent = state.origin || "-";
  document.getElementById("st-dest").textContent = state.destination || "-";
  document.getElementById("st-date").textContent = state.date || "-";
  document.getElementById("st-weight").textContent = state.weight_kg ? `${state.weight_kg} kg` : "-";
  document.getElementById("st-pieces").textContent = state.pieces ? `${state.pieces} (${state.package_type || 'pieces'})` : "-";
  document.getElementById("st-volume").textContent = state.volume_cbm ? `${state.volume_cbm} CBM` : "-";
  document.getElementById("st-dims").textContent = state.dimensions_cm ? `${state.dimensions_cm.join(' × ')} cm` : "-";
  document.getElementById("st-chgweight").textContent = chgWeight ? `${chgWeight} kg` : "-";
  document.getElementById("st-sort").textContent = sort || "Default";
  document.getElementById("st-pending").textContent = pending || "None (Ready)";

  // Active filters badges
  const fContainer = document.getElementById("active-filters-badges");
  fContainer.innerHTML = "";
  const activeKeys = Object.entries(filters || {});
  if (activeKeys.length === 0) {
    fContainer.innerHTML = `<span class="badge badge-subtle">No filters active</span>`;
  } else {
    activeKeys.forEach(([k, v]) => {
      const span = document.createElement("span");
      span.className = "badge badge-accent";
      span.textContent = `${k}: ${v}`;
      fContainer.appendChild(span);
    });
  }
}

function updateCleaningReport(report) {
  if (!report) return;
  document.getElementById("cl-in").textContent = report.rows_in || "0";
  document.getElementById("cl-out").textContent = report.rows_out || "0";
  document.getElementById("cl-airline").textContent = report.airline_names_fixed || "0";
  document.getElementById("cl-dup").textContent = report.duplicates_removed || "0";
  document.getElementById("cl-price").textContent = report.prices_converted_to_usd || "0";
  document.getElementById("cl-rateless").textContent = report.flights_without_rate_removed || "0";
}

// === 5. View Tabs & Reset ===

function initViewTabs() {
  const tabs = document.querySelectorAll(".view-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const targetId = tab.getAttribute("data-view");
      document.querySelectorAll(".view-content").forEach(c => c.classList.remove("active"));
      document.getElementById(targetId).classList.add("active");
    });
  });
}

function initResetButton() {
  const btn = document.getElementById("reset-btn");
  btn.addEventListener("click", async () => {
    try {
      await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: SESSION_ID })
      });
      // Clear messages
      document.getElementById("chat-messages").innerHTML = `
        <div class="message-bubble bot-message">
          <div class="avatar">✈️</div>
          <div class="bubble-content">
            <p><strong>Session reset. Starting fresh!</strong></p>
            <p>What flight schedules or cargo rates would you like to explore?</p>
          </div>
        </div>
      `;
      updateFlightCards([]);
      updateActionModeBadge(null);
      updateStateInspector({}, 0, {}, null, null);
    } catch (err) {
      console.error("Failed to reset session:", err);
    }
  });
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
