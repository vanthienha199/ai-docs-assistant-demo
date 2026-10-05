/* Captures every image the gig gallery and the case study use, straight from the
   running app. Nothing here is drawn by hand. */
import { mkdirSync } from "node:fs";
import puppeteer from "./puppeteer.mjs";

const BASE = "http://127.0.0.1:8111";
const RAW = "raw";
const SHOTS = "..";
mkdirSync(RAW, { recursive: true });

const browser = await puppeteer.launch({ headless: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function open(path = "/", width = 1280, height = 769) {
  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 2 });
  await page.goto(BASE + path, { waitUntil: "networkidle0" });
  await page.evaluateHandle("document.fonts.ready");
  return page;
}

async function ask(page, question) {
  await page.type("#q", question);
  await page.keyboard.press("Enter");
  await page.waitForSelector(".order-head", { timeout: 180000 });
  await sleep(1400);
}

async function clip(page, selector, out, pad = 0, maxHeight = 0) {
  const box = await (await page.$(selector)).boundingBox();
  if (maxHeight) box.height = Math.min(box.height, maxHeight);
  await page.screenshot({
    path: out,
    clip: {
      x: Math.max(0, box.x - pad),
      y: Math.max(0, box.y - pad),
      width: box.width + pad * 2,
      height: box.height + pad * 2,
    },
  });
}

/* 1. the hero: a cited answer sitting beside the handbook page it came from */
let page = await open("/", 1000, 769);
await ask(page, "How long is the workmanship guarantee and what does it not cover?");
/* the cover band covers the answer column, so the page is scrolled until the
   handbook page fills the part of the shot that stays visible */
await page.evaluate(() => window.scrollTo(0, document.querySelector(".order-body").getBoundingClientRect().top + window.scrollY - 8));
await sleep(500);
await page.screenshot({ path: `${RAW}/cover_band.png` });
await page.close();

page = await open("/", 1440, 900);
await ask(page, "How long is the workmanship guarantee and what does it not cover?");
await page.screenshot({ path: `${RAW}/hero_cited.png` });
await clip(page, ".order", `${RAW}/answer_card.png`);
await clip(page, ".answer-col", `${RAW}/answer_only.png`);
await clip(page, ".source-col", `${RAW}/source_pane.png`);
await clip(page, ".source-col", `${RAW}/source_top.png`, 0, 420);
await page.close();

/* the same view at gallery size, for shot1 */
page = await open("/", 1280, 769);
await ask(page, "How long is the workmanship guarantee and what does it not cover?");
await page.screenshot({ path: `${SHOTS}/shot1.png` });
await page.close();

/* 2. a refusal */
page = await open("/", 1280, 769);
await ask(page, "Do you install swimming pools in Canada?");
await page.screenshot({ path: `${SHOTS}/shot3.png` });
await clip(page, ".order", `${RAW}/refusal_card.png`, 0, 430);
await page.close();

/* 3. the empty state */
page = await open("/", 1280, 769);
await sleep(600);
await page.screenshot({ path: `${RAW}/empty.png` });
await page.close();

/* 4. the documents page */
page = await open("/admin", 1280, 769);
await sleep(900);
await page.screenshot({ path: `${SHOTS}/shot2.png` });
await clip(page, ".plain", `${RAW}/documents.png`);
await page.close();

/* 5. the cited answer on its own, for the before and after pair */
page = await open("/", 1100, 900);
await ask(page, "What does an emergency call out cost at night?");
await clip(page, ".order", `${RAW}/cited_emergency.png`);
await page.close();

await browser.close();
console.log("captures written");
