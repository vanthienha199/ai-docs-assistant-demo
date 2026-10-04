const { chromium } = require("/Users/hale/projects/vooks/vooks-ui/node_modules/playwright");

const BASE = process.env.BASE || "http://127.0.0.1:8077";
const OUT = process.env.OUT || "/Users/hale/Desktop/Career/fiverr_demos/ai-docs-assistant";
const SIZE = { width: 1280, height: 769 };

const askAndWait = async (page, text) => {
  const before = await page.locator(".turn-a").count();
  await page.fill("#q", text);
  await page.click("#send");
  await page.waitForFunction(
    (n) => document.querySelectorAll(".turn-a").length > n,
    before,
    { timeout: 240000 }
  );
  await page.waitForTimeout(900);
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: SIZE, deviceScaleFactor: 2 });
  const page = await ctx.newPage();

  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);

  await askAndWait(page, "How long is the workmanship guarantee?");
  await page.screenshot({ path: `${OUT}/shot1.png` });
  console.log("shot1 done");

  const admin = await ctx.newPage();
  await admin.goto(`${BASE}/admin`, { waitUntil: "networkidle" });
  await admin.waitForTimeout(1200);
  await admin.screenshot({ path: `${OUT}/shot2.png` });
  console.log("shot2 done");
  await admin.close();

  const fresh = await ctx.newPage();
  await fresh.goto(BASE, { waitUntil: "networkidle" });
  await fresh.waitForTimeout(1200);
  await askAndWait(fresh, "Do you install swimming pools in Canada?");
  await fresh.evaluate(() => window.scrollTo(0, 0));
  await fresh.waitForTimeout(500);
  await fresh.screenshot({ path: `${OUT}/shot3.png` });
  console.log("shot3 done");
  await fresh.close();

  await ctx.close();
  await browser.close();
})();
