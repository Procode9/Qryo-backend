const API_BASE = "https://qryo-backend.onrender.com";

const statusEl = document.getElementById("api-status");
const resultEl = document.getElementById("result");

/* API STATUS */
fetch(`${API_BASE}/`)
  .then(res => res.json())
  .then(data => {
    statusEl.innerText = "API Status: ONLINE";
    statusEl.classList.add("ok");
  })
  .catch(() => {
    statusEl.innerText = "API Status: OFFLINE";
    statusEl.classList.add("fail");
  });

/* SUBMIT JOB */
function submitJob() {
  const apiKey = document.getElementById("apiKey").value.trim();
  const jobType = document.getElementById("jobType").value;
  const payloadText = document.getElementById("payload").value;

  resultEl.textContent = "Submitting...";

  let payload;
  try {
    payload = JSON.parse(payloadText);
  } catch {
    resultEl.textContent = "Invalid JSON payload";
    return;
  }

  fetch(`${API_BASE}/submit-job`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey
    },
    body: JSON.stringify({
      job_type: jobType,
      payload: payload
    })
  })
    .then(res => res.json())
    .then(data => {
      resultEl.textContent = JSON.stringify(data, null, 2);
    })
    .catch(err => {
      resultEl.textContent = "Submission failed";
    });
}
