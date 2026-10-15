// AGRI Smart Irrigation - Frontend Dashboard Logic

const API_BASE = window.location.origin;

let currentSelectedCrop = "wheat";
let currentActiveMode = "hardware";
let isSwitchingMode = false;
let latestTelemetryCache = null;

// DOM Elements - Metrics
const elMoisture = document.getElementById("val-moisture");
const elMoistureFill = document.getElementById("moisture-fill");
const elTemp = document.getElementById("val-temp");
const elHumidity = document.getElementById("val-humidity");
const elSensorDot = document.getElementById("sensor-dot");
const elSensorText = document.getElementById("sensor-status-text");
const elPumpBadge = document.getElementById("pump-state-badge");
const elPumpDetail = document.getElementById("pump-status-detail");
const elRecTag = document.getElementById("rec-status-tag");
const elRecReason = document.getElementById("rec-reason-text");
const elRecTarget = document.getElementById("rec-target-moisture");
const elRecSourcePill = document.getElementById("rec-source-pill");
const elWeatherTemp = document.getElementById("weather-temp");
const elWeatherCondition = document.getElementById("weather-condition");
const elWeatherLocation = document.getElementById("weather-location");
const elWeatherSource = document.getElementById("weather-source");
const elLastSync = document.getElementById("last-sync-time");
const elNotification = document.getElementById("notification-banner");
const elNotificationMsg = document.getElementById("notification-msg");

// Mode Selector DOM Elements
const elBtnModeHardware = document.getElementById("btn-mode-hardware");
const elBtnModeSimulation = document.getElementById("btn-mode-simulation");

// Provenance & Chemistry DOM Elements
const elSrcMoisture = document.getElementById("src-moisture");
const elSrcTemp = document.getElementById("src-temp");
const elSrcHumidity = document.getElementById("src-humidity");
const elSrcWeather = document.getElementById("src-weather");
const elSrcChemistry = document.getElementById("src-chemistry");
const elValNitrogen = document.getElementById("val-nitrogen");
const elSrcValNitrogen = document.getElementById("src-val-nitrogen");
const elValPhosphorus = document.getElementById("val-phosphorus");
const elSrcValPhosphorus = document.getElementById("src-val-phosphorus");
const elValPotassium = document.getElementById("val-potassium");
const elSrcValPotassium = document.getElementById("src-val-potassium");
const elValPh = document.getElementById("val-ph");
const elSrcValPh = document.getElementById("src-val-ph");
const elChemMeta = document.getElementById("chem-meta");

// Provenance Badge Helpers
function applySourceBadge(element, sourceLabel) {
  if (!element) return;
  let normalized = (sourceLabel || "simulation").toLowerCase();
  if (normalized === "simulated") normalized = "simulation";
  element.className = "source-pill " + normalized;
  element.textContent = (normalized === "simulation") ? "SIMULATION" : normalized.toUpperCase();
}

function applyChemSourceTag(element, sourceLabel) {
  if (!element) return;
  let normalized = (sourceLabel || "simulation").toLowerCase();
  if (normalized === "simulated") normalized = "simulation";
  element.className = "chem-source-tag " + normalized;
  element.textContent = (normalized === "simulation") ? "SIMULATION" : normalized.toUpperCase();
}

// Notification Helper
let bannerTimer = null;

function showBanner(message, isError = false) {
  if (!elNotification) return;
  if (bannerTimer) clearTimeout(bannerTimer);
  elNotificationMsg.textContent = message;
  elNotification.classList.remove("hidden");
  elNotification.style.borderColor = isError ? "rgba(244, 63, 94, 0.5)" : "rgba(59, 130, 246, 0.5)";
  bannerTimer = setTimeout(() => {
    dismissBanner();
  }, isError ? 8000 : 4000);
}

function dismissBanner() {
  if (bannerTimer) {
    clearTimeout(bannerTimer);
    bannerTimer = null;
  }
  if (elNotification) elNotification.classList.add("hidden");
}

// Mode UI Synchronization
function updateModeUI(mode) {
  currentActiveMode = mode;
  const isHw = (mode === "hardware");
  const isSim = (mode === "simulation");

  if (elBtnModeHardware) {
    elBtnModeHardware.classList.toggle("active", isHw);
    elBtnModeHardware.setAttribute("aria-checked", isHw ? "true" : "false");
    elBtnModeHardware.setAttribute("tabindex", isHw ? "0" : "-1");
  }
  if (elBtnModeSimulation) {
    elBtnModeSimulation.classList.toggle("active", isSim);
    elBtnModeSimulation.setAttribute("aria-checked", isSim ? "true" : "false");
    elBtnModeSimulation.setAttribute("tabindex", isSim ? "0" : "-1");
  }
}

// Mode Switch Handler
async function switchMode(targetMode) {
  if (isSwitchingMode) return;
  if (targetMode === currentActiveMode) return;

  isSwitchingMode = true;
  if (elBtnModeHardware) elBtnModeHardware.disabled = true;
  if (elBtnModeSimulation) elBtnModeSimulation.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/telemetry/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: targetMode }),
    });

    if (res.ok) {
      const data = await res.json();
      updateModeUI(data.active_mode);
      showBanner(`Mode switched to ${data.active_mode.toUpperCase()} MODE.`);
      // Immediately refresh telemetry and recommendations for the new mode
      await Promise.all([syncTelemetry(), updateCropRecommendation()]);
    } else {
      const errData = await res.json().catch(() => ({}));
      showBanner(`Failed to switch mode: ${errData.detail || res.statusText}`, true);
    }
  } catch (err) {
    showBanner(`Connection error while switching mode: ${err.message}`, true);
  } finally {
    isSwitchingMode = false;
    if (elBtnModeHardware) elBtnModeHardware.disabled = false;
    if (elBtnModeSimulation) elBtnModeSimulation.disabled = false;
  }
}

// Fetch Initial Authoritative Mode on Boot
async function fetchInitialMode() {
  try {
    const res = await fetch(`${API_BASE}/api/telemetry/mode`);
    if (res.ok) {
      const data = await res.json();
      if (data.active_mode) {
        updateModeUI(data.active_mode);
      }
    }
  } catch (err) {
    console.debug("Mode initialization waiting for backend...", err);
  }
}

// Setup Keyboard & Click Controls for Segmented Mode Selector
function setupModeControls() {
  const group = document.querySelector(".mode-selector-group");
  if (group) {
    group.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        if (currentActiveMode !== "hardware") {
          switchMode("hardware");
          if (elBtnModeHardware) elBtnModeHardware.focus();
        }
      } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        if (currentActiveMode !== "simulation") {
          switchMode("simulation");
          if (elBtnModeSimulation) elBtnModeSimulation.focus();
        }
      }
    });
  }

  if (elBtnModeHardware) {
    elBtnModeHardware.addEventListener("click", () => switchMode("hardware"));
  }
  if (elBtnModeSimulation) {
    elBtnModeSimulation.addEventListener("click", () => switchMode("simulation"));
  }
}

// Fetch Sensor Status & Telemetry for Currently Active Mode (1-second real-time sync)
async function syncTelemetry() {
  try {
    const [statusRes, dataRes] = await Promise.all([
      fetch(`${API_BASE}/api/telemetry/status?source=${encodeURIComponent(currentActiveMode)}`),
      fetch(`${API_BASE}/api/telemetry/latest?source=${encodeURIComponent(currentActiveMode)}`),
    ]);

    // 1. Process sensor connection heartbeat
    if (statusRes.ok) {
      const statusData = await statusRes.json();
      if (statusData.is_connected) {
        elSensorDot.className = "status-dot online";
        const devTag = statusData.device_id ? ` (${statusData.device_id})` : "";
        const srcTag = statusData.source ? ` [${statusData.source.toUpperCase()}]` : "";
        elSensorText.textContent = `Sensor: Online${devTag}${srcTag}`;
      } else {
        elSensorDot.className = "status-dot offline";
        const devTag = statusData.device_id ? ` (${statusData.device_id})` : "";
        const srcTag = ` [${(statusData.source || currentActiveMode).toUpperCase()}]`;
        elSensorText.textContent = `Sensor: ${statusData.status}${devTag}${srcTag}`;
      }
    }

    // 2. Process latest telemetry values
    if (dataRes.ok) {
      const data = await dataRes.json();
      const elMoistureMeta = document.getElementById("moisture-meta");
      const elMoistureUnit = document.querySelector("#card-soil .metric-unit");

      if (data) {
        latestTelemetryCache = data;

        // Soil moisture value
        if (data.soil_moisture !== null && data.soil_moisture !== undefined) {
          elMoisture.textContent = Number(data.soil_moisture).toFixed(1);
          if (elMoistureUnit) elMoistureUnit.style.display = "";
          elMoistureFill.style.width = `${Math.min(Math.max(data.soil_moisture, 0), 100)}%`;
          if (elMoistureMeta) elMoistureMeta.textContent = "Optimal band: Select crop";
        } else {
          elMoisture.textContent = "N/A";
          if (elMoistureUnit) elMoistureUnit.style.display = "none";
          elMoistureFill.style.width = "0%";
          if (elMoistureMeta) {
            if (data.raw_soil_adc !== null && data.raw_soil_adc !== undefined) {
              elMoistureMeta.textContent = `Raw ADC: ${data.raw_soil_adc} (Uncalibrated / Awaiting sensor calibration)`;
            } else {
              elMoistureMeta.textContent = "Soil sensor uncalibrated / unconfirmed";
            }
          }
        }

        elTemp.textContent = (data.temperature !== null && data.temperature !== undefined) ? Number(data.temperature).toFixed(1) : "--";
        elHumidity.textContent = (data.humidity !== null && data.humidity !== undefined) ? Number(data.humidity).toFixed(1) : "--";

        // Update primary metric source badges
        const sources = data.sources || {};
        applySourceBadge(elSrcMoisture, data.soil_moisture === null ? "unavailable" : (sources.soil_moisture || data.source));
        applySourceBadge(elSrcTemp, sources.temperature || data.source);
        applySourceBadge(elSrcHumidity, sources.humidity || data.source);

        // Update Soil Chemistry (NPK & pH)
        const chemPresent = (data.nitrogen !== null && data.nitrogen !== undefined) ||
                            (data.phosphorus !== null && data.phosphorus !== undefined) ||
                            (data.potassium !== null && data.potassium !== undefined) ||
                            (data.ph !== null && data.ph !== undefined);

        if (chemPresent) {
          if (elValNitrogen) elValNitrogen.textContent = data.nitrogen !== null && data.nitrogen !== undefined ? Number(data.nitrogen).toFixed(1) : "N/A";
          if (elSrcValNitrogen) applyChemSourceTag(elSrcValNitrogen, sources.nitrogen || "simulation");

          if (elValPhosphorus) elValPhosphorus.textContent = data.phosphorus !== null && data.phosphorus !== undefined ? Number(data.phosphorus).toFixed(1) : "N/A";
          if (elSrcValPhosphorus) applyChemSourceTag(elSrcValPhosphorus, sources.phosphorus || "simulation");

          if (elValPotassium) elValPotassium.textContent = data.potassium !== null && data.potassium !== undefined ? Number(data.potassium).toFixed(1) : "N/A";
          if (elSrcValPotassium) applyChemSourceTag(elSrcValPotassium, sources.potassium || "simulation");

          if (elValPh) elValPh.textContent = data.ph !== null && data.ph !== undefined ? Number(data.ph).toFixed(2) : "N/A";
          if (elSrcValPh) applyChemSourceTag(elSrcValPh, sources.ph || "simulation");

          applySourceBadge(elSrcChemistry, "simulation");
          if (elChemMeta) elChemMeta.textContent = "Explicit source: simulated nutrients active. Physical sensor not confirmed.";
        } else {
          if (elValNitrogen) elValNitrogen.textContent = "N/A";
          if (elSrcValNitrogen) applyChemSourceTag(elSrcValNitrogen, "unavailable");

          if (elValPhosphorus) elValPhosphorus.textContent = "N/A";
          if (elSrcValPhosphorus) applyChemSourceTag(elSrcValPhosphorus, "unavailable");

          if (elValPotassium) elValPotassium.textContent = "N/A";
          if (elSrcValPotassium) applyChemSourceTag(elSrcValPotassium, "unavailable");

          if (elValPh) elValPh.textContent = "N/A";
          if (elSrcValPh) applyChemSourceTag(elSrcValPh, "unavailable");

          applySourceBadge(elSrcChemistry, "unavailable");
          if (elChemMeta) {
            elChemMeta.textContent = (currentActiveMode === "hardware")
              ? "Physical NPK & pH sensors unconfirmed. Showing N/A."
              : "Simulated nutrients awaiting simulator data.";
          }
        }
      } else {
        // No data available for currently selected mode
        latestTelemetryCache = null;
        elMoisture.textContent = "N/A";
        if (elMoistureUnit) elMoistureUnit.style.display = "none";
        elMoistureFill.style.width = "0%";
        if (elMoistureMeta) {
          elMoistureMeta.textContent = (currentActiveMode === "hardware")
            ? "Hardware node awaiting telemetry / offline"
            : "Simulator stopped / awaiting telemetry";
        }

        elTemp.textContent = "--";
        elHumidity.textContent = "--";

        applySourceBadge(elSrcMoisture, "unavailable");
        applySourceBadge(elSrcTemp, currentActiveMode);
        applySourceBadge(elSrcHumidity, currentActiveMode);

        if (elValNitrogen) elValNitrogen.textContent = "N/A";
        if (elSrcValNitrogen) applyChemSourceTag(elSrcValNitrogen, "unavailable");
        if (elValPhosphorus) elValPhosphorus.textContent = "N/A";
        if (elSrcValPhosphorus) applyChemSourceTag(elSrcValPhosphorus, "unavailable");
        if (elValPotassium) elValPotassium.textContent = "N/A";
        if (elSrcValPotassium) applyChemSourceTag(elSrcValPotassium, "unavailable");
        if (elValPh) elValPh.textContent = "N/A";
        if (elSrcValPh) applyChemSourceTag(elSrcValPh, "unavailable");

        applySourceBadge(elSrcChemistry, "unavailable");
        if (elChemMeta) {
          elChemMeta.textContent = (currentActiveMode === "hardware")
            ? "Physical NPK & pH sensors unavailable. Showing N/A."
            : "Simulation nutrients awaiting simulator.";
        }
      }

      elLastSync.textContent = `Last Sync: ${new Date().toLocaleTimeString()}`;
    }
  } catch (err) {
    console.debug("Telemetry sync waiting for backend server...", err);
  }
}

// Fetch Pump Status (Separates simulated vs hardware states)
async function syncPumpStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/pump/status`);
    if (res.ok) {
      const pump = await res.json();
      if (pump.is_active) {
        elPumpBadge.textContent = pump.is_hardware_connected ? "PUMP ON (HARDWARE)" : "PUMP ON (SIMULATED)";
        elPumpBadge.className = "badge active";
      } else {
        elPumpBadge.textContent = pump.is_hardware_connected ? "PUMP OFF" : "PUMP OFF (SIMULATED)";
        elPumpBadge.className = "badge inactive";
      }
      elPumpDetail.textContent = pump.message;
    }
  } catch (err) {
    console.debug("Pump status check waiting...", err);
  }
}

// Manual Pump Control Toggle
async function togglePump(targetState) {
  try {
    const res = await fetch(`${API_BASE}/api/pump/control`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state: targetState, duration_seconds: 60, mode: "manual" }),
    });

    if (res.ok) {
      const pump = await res.json();
      showBanner(`Pump set to ${pump.state} (${pump.is_hardware_connected ? "Hardware" : "Simulated"})`);
      syncPumpStatus();
    } else {
      showBanner("Failed to toggle pump state", true);
    }
  } catch (err) {
    showBanner(`Connection error: ${err.message}`, true);
  }
}

// Crop Selector Change Event
function onCropChange() {
  const select = document.getElementById("crop-select");
  currentSelectedCrop = select.value;
  updateCropRecommendation();
}

// Update Mode-Aware Crop Recommendation
async function updateCropRecommendation() {
  try {
    const url = `${API_BASE}/api/crops/${encodeURIComponent(currentSelectedCrop)}/recommendation?source=${encodeURIComponent(currentActiveMode)}`;
    const res = await fetch(url);
    if (res.ok) {
      const rec = await res.json();
      elRecTarget.textContent = rec.target_range;
      elRecReason.textContent = rec.reason;

      elRecTag.className = "rec-tag";
      if (rec.status === "WATER_NEEDED") {
        elRecTag.textContent = "Irrigation Needed";
        elRecTag.classList.add("water-needed");
      } else if (rec.status === "OPTIMAL") {
        elRecTag.textContent = "Moisture Optimal";
        elRecTag.classList.add("optimal");
      } else if (rec.status === "EXCESS_WATER") {
        elRecTag.textContent = "Moisture High";
        elRecTag.classList.add("excess");
      } else if (rec.status === "STALE_DATA") {
        elRecTag.textContent = "Stale Telemetry";
        elRecTag.classList.add("stale");
      } else if (rec.status === "NO_DATA") {
        elRecTag.textContent = "No Data / Withheld";
        elRecTag.classList.add("nodata");
      } else {
        elRecTag.textContent = rec.status;
      }

      if (elRecSourcePill) {
        applySourceBadge(elRecSourcePill, rec.source || currentActiveMode);
      }
    } else {
      elRecTag.className = "rec-tag nodata";
      elRecTag.textContent = "Unavailable";
      elRecReason.textContent = "Recommendation service unreachable.";
      if (elRecSourcePill) {
        applySourceBadge(elRecSourcePill, "unavailable");
      }
    }
  } catch (err) {
    console.debug("Recommendation sync waiting...", err);
  }
}

// Fetch Weather Module (Separated & Non-blocking)
async function syncWeather() {
  try {
    const res = await fetch(`${API_BASE}/api/weather/current`);
    if (res.ok) {
      const weather = await res.json();
      elWeatherTemp.textContent = weather.temperature.toFixed(1);
      elWeatherCondition.textContent = weather.condition;
      elWeatherLocation.textContent = `Location: ${weather.city}`;
      elWeatherSource.textContent = weather.source_detail || weather.source;

      if (elSrcWeather) {
        if (weather.source === "weather_api") {
          elSrcWeather.className = "source-pill weather-api";
          elSrcWeather.textContent = "WEATHER API";
        } else {
          elSrcWeather.className = "source-pill simulated";
          elSrcWeather.textContent = "SIMULATION";
        }
      }
    }
  } catch (err) {
    elWeatherCondition.textContent = "Weather unavailable (Module isolated)";
  }
}

// Initialize Dashboard and Setup Polling
async function initApp() {
  setupModeControls();
  await fetchInitialMode();

  // Initial immediate synchronizations
  syncTelemetry();
  syncPumpStatus();
  updateCropRecommendation();
  syncWeather();

  // Fast 1-second interval for live real-time sensor updates
  setInterval(syncTelemetry, 1000);
  setInterval(updateCropRecommendation, 2000);
  setInterval(syncPumpStatus, 2000);
  // Slower interval for weather
  setInterval(syncWeather, 60000);
}

// Launch on page ready
window.addEventListener("DOMContentLoaded", initApp);
