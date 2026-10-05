/* Lays the real capture into the right hand side of the 1280x769 cover canvas,
   so the band in the cover template covers empty canvas instead of live UI. */
import puppeteer from "./puppeteer.mjs";
const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 769, deviceScaleFactor: 2 });
await page.goto("file://" + process.cwd() + "/scripts/cover.html", { waitUntil: "networkidle0" });
await page.screenshot({ path: "raw/cover_art.png" });
await browser.close();
console.log("cover art written");
