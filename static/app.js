/**
 * app.js - Frontend client for Air Cargo AI Assistant
 * Responsive for Mobile, Tablet, and Desktop.
 */

const SESSION_ID = "default_user";
let currentScenarios = [];
let currentCategory = "All";

document.addEventListener("DOMContentLoaded", () => {
  initScenarios();
  initChatForm();
  initViewTabs();
  initResetButton();
  initMobileNav();
});

// === 1. Mobile Bottom Navigation ===

function initMobileNav() {
  const navBtns = document.querySelectorAll("#mobile-nav .mobile-nav-btn");
  navBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetPanelId = btn.getAttribute("data-target");
      switchToPanel(targetPanelId);
    });
  });
}

function switchToPanel(targetPanelId) {
  // Update mobile nav buttons
  const navBtns = document.querySelectorAll("#mobile-nav .mobile-nav-btn");
  navBtns.forEach(btn => {
    if (btn.getAttribute("data-target") === targetPanelId) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Toggle active panel
  const panels = document.querySelectorAll(".main-layout .panel");
  panels.forEach(p => {
    if (p.id === targetPanelId) {
      p.classList.add("mobile-active");
    } else {
      p.classList.remove("mobile-active");
    }
  });
}

// === 2. Scenarios Catalog & Runner ===

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
    card.onclick = () => {
      // On mobile, automatically switch to Chat view
      if (window.innerWidth <= 1024) {
        switchToPanel("panel-chat");
      }
      sendPrompt(sc.prompt);
    };

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

// === 3. Chat Form & Messaging ===

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
  // Ensure we are viewing chat if on mobile
  if (window.innerWidth <= 1024) {
    switchToPanel("panel-chat");
  }

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
    tagHtml += ` <div class="action-tag" style="color:#38bdf8;">Scenario #${scenario}</div>`;
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
      Searching air cargo network...
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-bubble");
  if (el) el.remove();
}

// === 4. Handling Bot Results & UI Updates ===

function handleBotResponse(data) {
  appendBotMessage(data.reply, data.how, data.scenario);
  updateActionModeBadge(data.how);
  updateFlightCards(data.flights);
  updateStateInspector(data.state, data.chargeable_weight, data.filters, data.sort, data.pending);
  updateCleaningReport(data.report);

  // If on mobile and flights were returned, show a quick tap prompt
  if (window.innerWidth <= 1024 && data.flights && data.flights.length > 0) {
    const badge = document.getElementById("mobile-flights-badge");
    if (badge) badge.textContent = data.flights.length.toString();
  }
}

function updateActionModeBadge(how) {
  const badge = document.getElementById("action-mode-badge");
  if (!badge) return;
  if (!how) {
    badge.className = "mode-badge badge-idle";
    badge.textContent = "Ready";
  } else if (how.includes("New search")) {
    badge.className = "mode-badge badge-new-api";
    badge.textContent = "API Re-run (Rule 7)";
  } else {
    badge.className = "mode-badge badge-local-filter";
    badge.textContent = "Local Filter (Rule 6)";
  }
}

function updateFlightCards(flights) {
  const container = document.getElementById("flight-cards-container");
  const emptyState = document.getElementById("empty-results");
  const countEl = document.getElementById("flights-count");
  const mobileCountEl = document.getElementById("mobile-flights-badge");

  const countStr = (flights && flights.length) ? flights.length.toString() : "0";
  if (countEl) countEl.textContent = countStr;
  if (mobileCountEl) mobileCountEl.textContent = countStr;

  if (!flights || flights.length === 0) {
    container.innerHTML = "";
    if (emptyState) emptyState.style.display = "block";
    return;
  }

  if (emptyState) emptyState.style.display = "none";
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

// === 5. State Inspector & Cleaning Report ===

function updateStateInspector(state, chgWeight, filters, sort, pending) {
  if (!state) return;
  const setEl = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setEl("st-intent", state.intent ? state.intent.toUpperCase() : "-");
  setEl("st-origin", state.origin || "-");
  setEl("st-dest", state.destination || "-");
  setEl("st-date", state.date || "-");
  setEl("st-weight", state.weight_kg ? `${state.weight_kg} kg` : "-");
  setEl("st-pieces", state.pieces ? `${state.pieces} (${state.package_type || 'pieces'})` : "-");
  setEl("st-volume", state.volume_cbm ? `${state.volume_cbm} CBM` : "-");
  setEl("st-dims", state.dimensions_cm ? `${state.dimensions_cm.join(' × ')} cm` : "-");
  setEl("st-chgweight", chgWeight ? `${chgWeight} kg` : "-");
  setEl("st-sort", sort || "Default");
  setEl("st-pending", pending || "None (Ready)");

  const fContainer = document.getElementById("active-filters-badges");
  if (fContainer) {
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
}

function updateCleaningReport(report) {
  if (!report) return;
  const setNum = (id, num) => {
    const el = document.getElementById(id);
    if (el) el.textContent = num || "0";
  };
  setNum("cl-in", report.rows_in);
  setNum("cl-out", report.rows_out);
  setNum("cl-airline", report.airline_names_fixed);
  setNum("cl-dup", report.duplicates_removed);
  setNum("cl-price", report.prices_converted_to_usd);
  setNum("cl-rateless", report.flights_without_rate_removed);
}

// === 6. View Tabs & Reset ===

function initViewTabs() {
  const tabs = document.querySelectorAll(".view-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      const targetId = tab.getAttribute("data-view");
      document.querySelectorAll(".view-content").forEach(c => c.classList.remove("active"));
      const targetEl = document.getElementById(targetId);
      if (targetEl) targetEl.classList.add("active");
    });
  });
}

function initResetButton() {
  const btn = document.getElementById("reset-btn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    try {
      await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: SESSION_ID })
      });
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
