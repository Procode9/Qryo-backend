const API_BASE = "https://qryo-backend.onrender.com";

const statusEl = document.getElementById("api-status");

fetch(`${API_BASE}/`)
  .then(res => {
    if (!res.ok) throw new Error("API error");
    return res.json();
  })
  .then(data => {
    statusEl.innerText = "API Status: " + (data.status || "ONLINE");
    statusEl.classList.add("ok");
  })
  .catch(() => {
    statusEl.innerText = "API Status: OFFLINE";
    statusEl.classList.add("fail");
  });
