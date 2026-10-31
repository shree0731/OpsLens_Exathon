const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const SCREENSHOTS_DIR = path.resolve(__dirname, '../../docs/screenshots');
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function run() {
  console.log('[E2E Screenshot Runner] Starting headless Chrome...');

  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1520,960'],
    defaultViewport: { width: 1520, height: 960 },
  });

  const page = await browser.newPage();

  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
      console.log('  [Browser Error]:', msg.text());
    }
  });

  page.on('pageerror', (err) => {
    consoleErrors.push(err.toString());
    console.log('  [Page Exception]:', err.toString());
  });

  console.log('[E2E Screenshot Runner] Navigating to http://127.0.0.1:5173/lineage ...');
  await page.goto('http://127.0.0.1:5173/lineage', { waitUntil: 'networkidle0', timeout: 30000 });

  // Wait for react flow nodes to render
  await page.waitForSelector('.react-flow__node', { timeout: 15000 });
  await sleep(2000);

  // 1. Initial / Clean State
  console.log('[E2E Screenshot Runner] 1. Resetting to clean state...');
  await page.evaluate(async () => {
    await fetch('/api/faults/reset', { method: 'POST' });
  });
  await sleep(3500);

  const cleanPath = path.join(SCREENSHOTS_DIR, '01_clean_graph.png');
  await page.screenshot({ path: cleanPath, fullPage: false });
  console.log('  -> Saved: 01_clean_graph.png');

  // 2. Inject stale_feed
  console.log('[E2E Screenshot Runner] 2. Injecting stale_feed...');
  await page.evaluate(async () => {
    await fetch('/api/faults/stale_feed', { method: 'POST' });
  });
  await sleep(3000);

  const stalePath = path.join(SCREENSHOTS_DIR, '02_stale_feed.png');
  await page.screenshot({ path: stalePath, fullPage: false });
  console.log('  -> Saved: 02_stale_feed.png');

  // 3. Reset and inject row_drop
  console.log('[E2E Screenshot Runner] 3. Resetting and injecting row_drop...');
  await page.evaluate(async () => {
    await fetch('/api/faults/reset', { method: 'POST' });
    await new Promise((r) => setTimeout(r, 2000));
    await fetch('/api/faults/row_drop', { method: 'POST' });
  });
  await sleep(3000);

  const rowDropPath = path.join(SCREENSHOTS_DIR, '03_row_drop.png');
  await page.screenshot({ path: rowDropPath, fullPage: false });
  console.log('  -> Saved: 03_row_drop.png');

  // 4. Open SidePanel for node ORDERS
  console.log('[E2E Screenshot Runner] 4. Opening node SidePanel for ORDERS...');
  const ordersNode = await page.evaluateHandle(() => {
    const nodes = Array.from(document.querySelectorAll('.react-flow__node'));
    return nodes.find((n) => n.textContent && n.textContent.includes('ORDERS'));
  });

  if (ordersNode) {
    await ordersNode.click();
    await sleep(2000);
  }

  const sidePanelPath = path.join(SCREENSHOTS_DIR, '04_sidepanel.png');
  await page.screenshot({ path: sidePanelPath, fullPage: false });
  console.log('  -> Saved: 04_sidepanel.png');

  // 5. Reset and verify
  console.log('[E2E Screenshot Runner] 5. Resetting to clean state...');
  await page.evaluate(async () => {
    await fetch('/api/faults/reset', { method: 'POST' });
  });
  await sleep(3000);

  // Close sidepanel by pressing escape or clicking backdrop
  await page.keyboard.press('Escape');
  await sleep(1000);

  const resetPath = path.join(SCREENSHOTS_DIR, '05_reset.png');
  await page.screenshot({ path: resetPath, fullPage: false });
  console.log('  -> Saved: 05_reset.png');

  await browser.close();

  console.log('\n[E2E Screenshot Runner] Summary:');
  console.log('Total Console Errors Caught:', consoleErrors.length);
  if (consoleErrors.length > 0) {
    console.warn('Console Errors:', consoleErrors);
  } else {
    console.log('>> [PASS] Zero console errors during all 5 UI states!');
  }
}

run().catch((err) => {
  console.error('[E2E Screenshot Runner Error]:', err);
  process.exit(1);
});
