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

  // -------------------------------------------------------------------------
  // Part 1: Reset to clean baseline
  // -------------------------------------------------------------------------
  console.log('[E2E Screenshot Runner] Resetting production database to clean state...');
  await page.goto('http://127.0.0.1:8000/docs', { waitUntil: 'domcontentloaded' });
  await page.evaluate(async () => {
    await fetch('/api/faults/reset', { method: 'POST' });
  });
  await sleep(4000);

  // -------------------------------------------------------------------------
  // Screenshot 06: /timeline clean
  // -------------------------------------------------------------------------
  console.log('[E2E Screenshot Runner] 6. Navigating to /timeline (clean)...');
  await page.goto('http://127.0.0.1:5173/timeline', { waitUntil: 'networkidle0', timeout: 30000 });
  await sleep(2500);

  const cleanTimelinePath = path.join(SCREENSHOTS_DIR, '06_timeline_clean.png');
  await page.screenshot({ path: cleanTimelinePath, fullPage: false });
  console.log('  -> Saved: 06_timeline_clean.png');

  // -------------------------------------------------------------------------
  // Screenshot 07: /timeline after stale_feed and row_drop with incident expanded
  // -------------------------------------------------------------------------
  console.log('[E2E Screenshot Runner] 7. Injecting stale_feed and row_drop for /timeline...');
  await page.evaluate(async () => {
    await fetch('/api/faults/stale_feed', { method: 'POST' });
    await new Promise((r) => setTimeout(r, 1500));
    await fetch('/api/faults/row_drop', { method: 'POST' });
  });
  await sleep(4000);

  // Click the first card to expand it
  await page.evaluate(() => {
    const cards = document.querySelectorAll('.cursor-pointer');
    if (cards.length > 0) {
      cards[0].click();
    }
  });
  await sleep(1500);

  const faultedTimelinePath = path.join(SCREENSHOTS_DIR, '07_timeline_faulted.png');
  await page.screenshot({ path: faultedTimelinePath, fullPage: false });
  console.log('  -> Saved: 07_timeline_faulted.png');

  // -------------------------------------------------------------------------
  // Screenshot 08: /runs clean with horizontal lanes
  // -------------------------------------------------------------------------
  console.log('[E2E Screenshot Runner] 8. Resetting and navigating to /runs (clean lanes)...');
  await page.evaluate(async () => {
    await fetch('/api/faults/reset', { method: 'POST' });
  });
  await sleep(4000);

  await page.goto('http://127.0.0.1:5173/runs', { waitUntil: 'networkidle0', timeout: 30000 });
  await sleep(2500);

  const cleanRunsPath = path.join(SCREENSHOTS_DIR, '08_runs_clean.png');
  await page.screenshot({ path: cleanRunsPath, fullPage: false });
  console.log('  -> Saved: 08_runs_clean.png');

  // -------------------------------------------------------------------------
  // Screenshot 09: /runs after job_failure showing failed and skipped stages
  // -------------------------------------------------------------------------
  console.log('[E2E Screenshot Runner] 9. Injecting job_failure for /runs...');
  await page.evaluate(async () => {
    await fetch('/api/faults/job_failure', { method: 'POST' });
  });
  await sleep(4000);

  const jobFailurePath = path.join(SCREENSHOTS_DIR, '09_runs_job_failure.png');
  await page.screenshot({ path: jobFailurePath, fullPage: false });
  console.log('  -> Saved: 09_runs_job_failure.png');

  // -------------------------------------------------------------------------
  // Screenshot 10: /runs after late_load
  // -------------------------------------------------------------------------
  console.log('[E2E Screenshot Runner] 10. Resetting and injecting late_load for /runs...');
  await page.evaluate(async () => {
    await fetch('/api/faults/reset', { method: 'POST' });
    await new Promise((r) => setTimeout(r, 2000));
    await fetch('/api/faults/late_load', { method: 'POST' });
  });
  await sleep(4000);

  const lateLoadPath = path.join(SCREENSHOTS_DIR, '10_runs_late_load.png');
  await page.screenshot({ path: lateLoadPath, fullPage: false });
  console.log('  -> Saved: 10_runs_late_load.png');

  // -------------------------------------------------------------------------
  // Screenshot 11: A stage SidePanel
  // -------------------------------------------------------------------------
  console.log('[E2E Screenshot Runner] 11. Opening stage SidePanel on /runs...');
  await page.evaluate(() => {
    // Click on a stage card
    const stageCards = document.querySelectorAll('.cursor-pointer');
    if (stageCards.length > 0) {
      stageCards[0].click();
    }
  });
  await sleep(2000);

  const sidePanelPath = path.join(SCREENSHOTS_DIR, '11_runs_sidepanel.png');
  await page.screenshot({ path: sidePanelPath, fullPage: false });
  console.log('  -> Saved: 11_runs_sidepanel.png');

  // -------------------------------------------------------------------------
  // Final Reset to restore clean production state
  // -------------------------------------------------------------------------
  console.log('[E2E Screenshot Runner] Resetting production database to clean state...');
  await page.evaluate(async () => {
    await fetch('/api/faults/reset', { method: 'POST' });
  });
  await sleep(3500);

  await browser.close();

  console.log('\n[E2E Screenshot Runner] Summary:');
  console.log('Total Console Errors Caught:', consoleErrors.length);
  if (consoleErrors.length > 0) {
    console.warn('Console Errors:', consoleErrors);
  } else {
    console.log('>> [PASS] Zero console errors during all Prompt 3 UI flows!');
  }
}

run().catch((err) => {
  console.error('[E2E Screenshot Runner Error]:', err);
  process.exit(1);
});