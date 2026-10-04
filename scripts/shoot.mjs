import puppeteer from "puppeteer";
import fs from "node:fs";

const BASE = process.env.BASE || "http://127.0.0.1:8111";
const OUT = process.env.OUT || "raw";
fs.mkdirSync(OUT, { recursive: true });

const browser = await puppeteer.launch({ headless: true });

async function page(w, h, theme, path = "/") {
  const p = await browser.newPage();
  await p.setViewport({ width: w, height: h, deviceScaleFactor: 2 });
  await p.goto(`${BASE}${path}${theme === "light" ? "?theme=light" : ""}`, { waitUntil: "networkidle0" });
  return p;
}

async function ask(p, q) {
  const n = await p.$$eval(".turn-a", (x) => x.length);
  await p.type("#q", q);
  await p.keyboard.press("Enter");
  await p.waitForFunction((k) => document.querySelectorAll(".turn-a").length > k, { timeout: 120000 }, n);
  await new Promise((r) => setTimeout(r, 500));
}

// The CLI backend pays a process startup cost, so its timing is not representative
// of the hosted API. Rather than show a misleading number, the hero omits it.
const dropTiming = (p) =>
  p.evaluate(() => {
    document.querySelectorAll(".meta-row span").forEach((s) => {
      if (s.textContent.trim().startsWith("Time")) s.remove();
    });
  });

// 1. hero, dark, bigger UI so the answer is readable inside the frame
{
  const p = await page(1150, 780, "dark");
  await ask(p, "What do you charge for a blocked sink and how do I pay the invoice?");
  await dropTiming(p);
  await p.screenshot({ path: `${OUT}/hero_dark.png` });
  await p.close();
  console.log("wrote hero_dark.png");
}

// 2. deliverable tiles, light, cropped to the main panel so each tile proves its own label
async function tile(file, theme, path, question, selector = ".main") {
  const p = await page(1180, 820, theme, path);
  if (question) await ask(p, question);
  await new Promise((r) => setTimeout(r, 400));
  // The local CLI backend's timing is not representative of the hosted API, so it
  // is left out of the tiles the same way it is left out of the hero.
  await dropTiming(p);
  const el = await p.$(selector);
  await el.screenshot({ path: `${OUT}/${file}` });
  await p.close();
  console.log("wrote", file);
}

// Tiles are captured from the tightest element that proves the label, so no tile
// carries dead space or another tile's chrome.
await tile("cited_light.png", "light", "/", "How long is the workmanship guarantee?", ".thread");
await tile("admin_light.png", "light", "/admin", null, "table");
await tile("refusal_light.png", "light", "/", "Do you install swimming pools in Canada?", ".thread");
await tile("upload_light.png", "light", "/admin", null, ".main");
await tile("empty_light.png", "light", "/", null, ".thread");

// 3. extra states kept for the demo folder gallery
{
  const p = await page(1280, 769, "dark");
  await ask(p, "Do you install swimming pools in Canada?");
  await p.screenshot({ path: `${OUT}/refusal_dark.png` });
  await p.close();
  console.log("wrote refusal_dark.png");
}

await browser.close();
console.log("all captures done");
