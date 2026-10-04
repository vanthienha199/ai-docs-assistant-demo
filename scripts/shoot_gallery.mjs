import puppeteer from "puppeteer";
const BASE = "http://127.0.0.1:8111";
const OUT = "..";
const browser = await puppeteer.launch({ headless: true });
async function go(theme, path = "/") {
  const p = await browser.newPage();
  await p.setViewport({ width: 1280, height: 769, deviceScaleFactor: 2 });
  await p.goto(`${BASE}${path}${theme === "light" ? "?theme=light" : ""}`, { waitUntil: "networkidle0" });
  return p;
}
async function ask(p, q) {
  const n = await p.$$eval(".turn-a", (x) => x.length);
  await p.type("#q", q);
  await p.keyboard.press("Enter");
  await p.waitForFunction((k) => document.querySelectorAll(".turn-a").length > k, { timeout: 120000 }, n);
  await new Promise((r) => setTimeout(r, 400));
}
let p = await go("dark");
await ask(p, "My water heater is leaking at 11 PM. What will an emergency visit cost and is the repair under warranty?");
await p.screenshot({ path: `${OUT}/shot1.png` }); await p.close();

p = await go("light", "/admin");
await new Promise((r) => setTimeout(r, 500));
await p.screenshot({ path: `${OUT}/shot2.png` }); await p.close();

p = await go("dark");
await ask(p, "Do you install swimming pools in Canada?");
await p.screenshot({ path: `${OUT}/shot3.png` }); await p.close();
await browser.close();
console.log("gallery shots done");
