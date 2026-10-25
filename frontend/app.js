const API_BASE = "http://127.0.0.1:8000";

async function checkHealth() {
  const status = document.getElementById("api-status");
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    status.textContent = `API ${data.status} · ${data.mode}`;
  } catch {
    status.textContent = "API not connected";
  }
}

document.getElementById("message-form").addEventListener("submit", (event) => {
  event.preventDefault();
  document.getElementById("result").textContent =
    "Frontend scaffold is ready. Connect this form to POST /api/messages when that endpoint is implemented.";
});

checkHealth();
