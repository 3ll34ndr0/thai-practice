let mediaRecorder;
let chunks = [];
let currentExercise = null;

const thaiEl = document.getElementById("thai-text");
const translationEl = document.getElementById("translation");
const recordBtn = document.getElementById("record-btn");
const nextBtn = document.getElementById("next-btn");
const resultEl = document.getElementById("result");
const statusEl = document.getElementById("status");

async function loadExercise() {
  resultEl.innerHTML = "";
  statusEl.textContent = "";
  const res = await fetch("/api/exercise");
  currentExercise = await res.json();
  thaiEl.textContent = currentExercise.thai;
  translationEl.textContent = currentExercise.translation_en;
}

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  chunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
  mediaRecorder.onstop = onRecordingStop;
  mediaRecorder.start();
  recordBtn.textContent = "Stop";
  statusEl.textContent = "Recording...";
}

function stopRecording() {
  mediaRecorder.stop();
  mediaRecorder.stream.getTracks().forEach((t) => t.stop());
}

recordBtn.addEventListener("click", () => {
  if (!mediaRecorder || mediaRecorder.state === "inactive") {
    startRecording();
  } else {
    stopRecording();
    recordBtn.textContent = "Record";
  }
});

async function onRecordingStop() {
  statusEl.textContent = "Transcribing...";
  const blob = new Blob(chunks, { type: "audio/webm" });
  const form = new FormData();
  form.append("exercise_id", currentExercise.id);
  form.append("audio", blob, "recording.webm");

  const res = await fetch("/api/submit", { method: "POST", body: form });
  if (!res.ok) {
    statusEl.textContent = "Error: " + (await res.text());
    return;
  }
  renderResult(await res.json());
  statusEl.textContent = "";
}

function renderResult(data) {
  resultEl.innerHTML = "";

  const scoreLine = document.createElement("p");
  scoreLine.className = "score";
  scoreLine.textContent = `Score: ${data.score}%`;

  const diffLine = document.createElement("p");
  diffLine.className = "diff";
  data.diff.forEach((d) => {
    const span = document.createElement("span");
    span.textContent = d.word;
    span.className = "word " + d.status;
    diffLine.appendChild(span);
    diffLine.appendChild(document.createTextNode(" "));
  });

  const transcriptLine = document.createElement("p");
  transcriptLine.textContent = "You said: " + (data.transcript || "(nothing recognized)");

  const youglishLine = document.createElement("p");
  const youglishLink = document.createElement("a");
  youglishLink.href = `https://youglish.com/pronounce/${encodeURIComponent(data.target)}/thai`;
  youglishLink.target = "_blank";
  youglishLink.rel = "noopener";
  youglishLink.textContent = "Hear native speakers say this on YouGlish";
  youglishLine.appendChild(youglishLink);

  resultEl.appendChild(scoreLine);
  resultEl.appendChild(diffLine);
  resultEl.appendChild(transcriptLine);
  resultEl.appendChild(youglishLine);
}

nextBtn.addEventListener("click", loadExercise);
loadExercise();
