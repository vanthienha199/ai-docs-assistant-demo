const thread = document.getElementById("thread");
const form = document.getElementById("composer");
const input = document.getElementById("q");
const send = document.getElementById("send");

const escapeHtml = (s) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const withCitations = (s) =>
  escapeHtml(s).replace(/\s*\[(\d+)\]/g, '<sup>$1</sup>');

function addQuestion(text) {
  const empty = document.getElementById("empty");
  if (empty) empty.remove();
  const el = document.createElement("div");
  el.className = "turn-q";
  el.textContent = text;
  thread.appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
}

function addAnswer(data) {
  const el = document.createElement("div");
  el.className = data.grounded ? "turn-a" : "turn-a nogo";

  const sources = (data.citations || [])
    .map(
      (c) => `
      <div class="source">
        <div class="num">${c.n}</div>
        <div class="source-body">
          <div class="source-label">${escapeHtml(c.label)}</div>
          <p class="source-text">${escapeHtml(c.snippet)}</p>
          <div class="source-meta">${escapeHtml(c.document)} &middot; match score ${c.score}</div>
        </div>
      </div>`
    )
    .join("");

  el.innerHTML = `
    <p class="answer">${withCitations(data.answer)}</p>
    ${sources ? `<div class="sources"><h3>Sources</h3>${sources}</div>` : ""}
    <div class="meta-row">
      <span><b>Grounded</b> ${data.grounded ? "yes" : "no, the assistant is blocked from answering"}</span>
      <span><b>Top match</b> ${data.top_score}</span>
      <span><b>Model</b> ${escapeHtml(data.model || data.backend)}</span>
      <span><b>Coverage</b> ${data.coverage}</span>
      ${data.dropped_citations ? `<span><b>Dropped</b> ${data.dropped_citations} bad citation</span>` : ""}
      <span><b>Time</b> ${data.ms} ms</span>
    </div>`;
  thread.appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function ask(question) {
  addQuestion(question);
  send.disabled = true;
  send.textContent = "Reading";
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    addAnswer(await res.json());
  } catch (error) {
    addAnswer({
      answer: "The assistant is not reachable. Check that the server is running.",
      grounded: false,
      citations: [],
      backend: "none",
      model: "none",
      top_score: 0,
      ms: 0,
    });
  } finally {
    send.disabled = false;
    send.textContent = "Ask";
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  ask(question);
});

document.querySelectorAll(".examples button").forEach((button) => {
  button.addEventListener("click", () => ask(button.textContent.trim()));
});
