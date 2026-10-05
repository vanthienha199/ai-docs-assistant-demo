const order = document.getElementById("order");
const form = document.getElementById("composer");
const input = document.getElementById("q");
const send = document.getElementById("send");
const pane = () => document.getElementById("source");
const sheets = document.getElementById("sheets");
const sourceHead = document.getElementById("sourceHead");

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const clock = () =>
  new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

let ref = 4471;

/* The handbook is printed once into the right pane, so clicking a footnote only
   has to scroll and outline a paragraph that is already on the page. */
async function printHandbook() {
  const data = await (await fetch("/api/handbook")).json();
  sheets.innerHTML = data.pages
    .map(
      (page) => `
      <section class="sheet">
        <div class="running"><b>${esc(page.title)}</b><span class="folio">Page ${page.page}</span></div>
        ${page.blocks
          .map(
            (block) => `<div class="para" id="${block.anchor}">
              ${block.heading ? `<h4>${esc(block.heading)}</h4>` : ""}
              ${block.html}
            </div>`
          )
          .join("")}
      </section>`
    )
    .join("");
  sourceHead.textContent = `Blue Harbor Plumbing handbook, ${data.documents.length} documents`;
}

function openCitation(citation) {
  document.querySelectorAll(".para.lit").forEach((el) => el.classList.remove("lit"));
  document.querySelectorAll(".fn.on").forEach((el) => el.classList.remove("on"));
  const target = document.getElementById(citation.anchor);
  if (!target) return;
  target.classList.add("lit");
  order
    .querySelectorAll(`.fn[data-n="${citation.n}"]`)
    .forEach((el) => el.classList.add("on"));
  sourceHead.textContent = `${citation.cite}, ${citation.label.split(" > ")[0]}`;
  const top = target.offsetTop - sourceHead.offsetHeight - 16;
  pane().scrollTo({ top, behavior: "smooth" });
}

function render(question, data) {
  const citations = data.citations || [];
  order.className = "order" + (data.grounded ? "" : data.offline ? " offline" : " refused");

  const state = data.offline
    ? "Server not reachable"
    : data.grounded
      ? `Answered from the handbook, ${citations.length} citation${citations.length === 1 ? "" : "s"}`
      : "Not in the handbook";

  const answerHtml = esc(data.answer).replace(
    /\s*\[(\d+)\]/g,
    (whole, n) => `<button class="fn" data-n="${n}" aria-label="Open citation ${n}">${n}</button>`
  );

  const notes = citations.length
    ? `<div class="notes">
        <h3>Sources</h3>
        <ol>
          ${citations
            .map(
              (c) => `<li>
                <span class="mark">${c.n}</span>
                <button type="button" data-n="${c.n}">
                  <b>${esc(c.cite)}</b>
                  <em> ${esc(c.label.replace(" > ", ", "))}</em>
                </button>
              </li>`
            )
            .join("")}
        </ol>
      </div>`
    : "";

  order.innerHTML = `
    <div class="order-head">
      <div class="order-ref"><b>WO ${ref}</b><span>Asked ${clock()}</span></div>
      <div class="order-q">
        <h2>${esc(question)}</h2>
        <p class="state">${esc(state)}</p>
      </div>
    </div>
    <div class="order-body">
      <div class="answer-col">
        ${
          data.offline
            ? `<div class="offline-note">
                 <h2>The assistant did not answer</h2>
                 <p>The question reached the page but the server did not reply, so nothing is being guessed here.</p>
                 <p>Start it again with <code>./run.sh</code> and ask once more. The handbook on the right is the copy already loaded in this tab.</p>
               </div>`
            : `<p class="answer">${answerHtml}</p>${notes}`
        }
      </div>
      <div class="source-col" id="source"></div>
    </div>`;

  /* The printed handbook is moved across rather than fetched again, so the
     scroll position and the outline survive every new question. */
  const column = pane();
  column.appendChild(sourceHead);
  column.appendChild(sheets);
  bind(citations);
  if (citations.length) openCitation(citations[0]);
}

function bind(citations) {
  const find = (n) => citations.find((c) => String(c.n) === String(n));
  order.querySelectorAll(".fn, .notes button").forEach((button) => {
    button.addEventListener("click", () => {
      const citation = find(button.dataset.n);
      if (citation) openCitation(citation);
    });
  });
}

async function ask(question) {
  send.disabled = true;
  send.textContent = "Reading";
  ref += 1;
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    render(question, await res.json());
  } catch (error) {
    render(question, { answer: "", offline: true, grounded: false, citations: [] });
  } finally {
    send.disabled = false;
    send.textContent = "Ask";
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

printHandbook();
