/* The error state is captured for real: the page is loaded, the server is then
   stopped, and the question is asked against a server that is no longer there. */
import { execSync } from "node:child_process";
import puppeteer from "./puppeteer.mjs";

const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 769, deviceScaleFactor: 2 });
await page.goto("http://127.0.0.1:8111/", { waitUntil: "networkidle0" });
await page.evaluateHandle("document.fonts.ready");

execSync("lsof -ti:8111 | xargs kill");
await new Promise((r) => setTimeout(r, 1200));

await page.type("#q", "Can I cancel an appointment on the day?");
await page.keyboard.press("Enter");
await page.waitForSelector(".order.offline", { timeout: 30000 });
await new Promise((r) => setTimeout(r, 600));
await page.screenshot({ path: "raw/offline.png" });
const box = await (await page.$(".order")).boundingBox();
await page.screenshot({ path: "raw/offline_card.png", clip: box });
await browser.close();
console.log("offline captured");
