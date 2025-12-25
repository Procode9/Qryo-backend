const API_BASE = "https://qryo-backend.onrender.com";

const statusEl = document.getElementById("api-status");
const resultEl = document.getElementById("result");
const jobsEl = document.getElementById("jobs");

/* API STATUS */
fetch(`${API_BASE}/`)
  .then(res => res.json())
  .then(() => {
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
      payload
    })
  })
    .then(res => res.json())
    .then(data => {
      resultEl.textContent = JSON.stringify(data, null, 2);
      loadJobs();
    })
    .catch(() => {
      resultEl.textContent = "Submission failed";
    });
}

/* LOAD JOBS */
function loadJobs() {
  jobsEl.innerHTML = "Loading jobs...";

  fetch(`${API_BASE}/jobs`)
    .then(res => res.json())
    .then(jobs => {
      if (!jobs.length) {
        jobsEl.innerHTML = "<p>No jobs found.</p>";
        return;
      }

      jobsEl.innerHTML = jobs.map(job => `
        <div class="job">
          <div><strong>ID:</strong> ${job.id}</div>
          <div><strong>Type:</strong> ${job.job_type}</div>
          <div><strong>Status:</strong> <span class="status ${job.status}">${job.status}</span></div>
          <div><strong>Created:</strong> ${job.created_at}</div>
        </div>
      `).join("");
    })
    .catch(() => {
      jobsEl.innerHTML = "Failed to load jobs.";
    });
}

/* AUTO LOAD */
loadJobs();
