// ============================================================
// Spent — iOS Scriptable Widget
// ============================================================
//
// INSTALLATION:
// 1. Install the free "Scriptable" app from the App Store
// 2. Open Scriptable and tap the "+" button to create a new script
// 3. Paste this entire file into the editor
// 4. Change BASE_URL below to your ngrok or Railway URL
// 5. Add a Scriptable widget to your home screen
// 6. Long-press the widget → Edit Widget → choose this script
// 7. Set widget size to "Medium" for best results
//
// PERIOD PREFERENCE:
// Option 1 (recommended): Long-press the widget → Edit Widget → Parameter
//   Type "daily", "weekly", or "monthly". Each widget can show a different period.
// Option 2: Run this script in Scriptable and tap the switch button to cycle
//   the period. Saves to Keychain as a fallback when no parameter is set.
// ============================================================

// ── Configuration ──────────────────────────────────────────
const BASE_URL = 'https://spent-production.up.railway.app'; // ← Railway URL
const PERIOD_KEY = 'spent_period';
const LAST_FETCH_KEY = 'spent_last_fetch';
const REFRESH_INTERVAL_S = 60; // re-fetch if data is older than this many seconds
const DARK_BG = new Color('#1A1A2E');
const ACCENT = new Color('#4ECDC4');
const WHITE = Color.white();
const GRAY = new Color('#AAAAAA');

// ── Category colors matching backend ───────────────────────
const CATEGORY_COLORS = {
  'Food & Drink': '#FF6B6B',
  Transport: '#4ECDC4',
  Entertainment: '#45B7D1',
  Shopping: '#96CEB4',
  Health: '#FFEAA7',
  Utilities: '#DDA0DD',
  Travel: '#F0A500',
  Other: '#B0BEC5',
};

// ── Period management ───────────────────────────────────────
function getSavedPeriod() {
  const VALID = ['daily', 'weekly', 'monthly'];
  const param = (args.widgetParameter || '').trim().toLowerCase();
  if (VALID.includes(param)) return param;
  if (Keychain.contains(PERIOD_KEY)) return Keychain.get(PERIOD_KEY);
  return 'monthly';
}

function cyclePeriod(current) {
  const periods = ['monthly', 'weekly', 'daily'];
  const next = periods[(periods.indexOf(current) + 1) % periods.length];
  Keychain.set(PERIOD_KEY, next);
  return next;
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ── API helpers ─────────────────────────────────────────────
async function fetchSummary(period) {
  try {
    const req = new Request(`${BASE_URL}/api/v1/summary?period=${period}`);
    req.timeoutInterval = 10;
    return await req.loadJSON();
  } catch (e) {
    console.error('fetchSummary failed: ' + e.message);
    return null;
  }
}

async function fetchDonutChart(period) {
  try {
    const req = new Request(`${BASE_URL}/api/v1/charts/donut?period=${period}`);
    req.timeoutInterval = 15;
    return await req.loadImage();
  } catch (e) {
    console.error('fetchDonutChart failed: ' + e.message);
    return null;
  }
}

// ── Widget builder ──────────────────────────────────────────
async function buildWidget(summary, chartImg, period) {
  const widget = new ListWidget();
  widget.backgroundColor = DARK_BG;
  widget.setPadding(12, 14, 12, 14);
  widget.url = `${BASE_URL}/`;  // opens the spending dashboard in Safari

  // Header row: icon + title + period badge
  const headerStack = widget.addStack();
  headerStack.layoutHorizontally();
  headerStack.centerAlignContent();

  const titleText = headerStack.addText('💸 Spent');
  titleText.textColor = WHITE;
  titleText.font = Font.boldSystemFont(13);

  headerStack.addSpacer();

  const periodBadge = headerStack.addText(capitalize(period));
  periodBadge.textColor = ACCENT;
  periodBadge.font = Font.mediumSystemFont(11);

  widget.addSpacer(6);

  if (!summary) {
    // Error state
    const errStack = widget.addStack();
    errStack.layoutVertically();
    errStack.centerAlignContent();

    const errText = errStack.addText("⚠️ Can't connect");
    errText.textColor = new Color('#FF6B6B');
    errText.font = Font.mediumSystemFont(12);
    errText.centerAlignText();

    const hintText = errStack.addText('Check BASE_URL in script');
    hintText.textColor = GRAY;
    hintText.font = Font.systemFont(10);
    hintText.centerAlignText();

    return widget;
  }

  // Main content row: chart on left, breakdown on right
  const contentStack = widget.addStack();
  contentStack.layoutHorizontally();
  contentStack.centerAlignContent();

  // Chart image (left column)
  if (chartImg) {
    const imgStack = contentStack.addStack();
    imgStack.layoutVertically();
    imgStack.centerAlignContent();

    const img = imgStack.addImage(chartImg);
    img.imageSize = new Size(80, 80);
    img.centerAlignImage();

    imgStack.addSpacer(4);

    const totalLabel = imgStack.addText(`$${(+(summary.total_spent || 0)).toFixed(2)}`);
    totalLabel.textColor = WHITE;
    totalLabel.font = Font.boldSystemFont(14);
    totalLabel.centerAlignText();
  } else {
    const placeholder = contentStack.addText('📊');
    placeholder.font = Font.systemFont(40);
  }

  contentStack.addSpacer(12);

  // Category breakdown (right column)
  const breakdownStack = contentStack.addStack();
  breakdownStack.layoutVertically();
  breakdownStack.centerAlignContent();

  const breakdown = summary.breakdown || [];
  const topItems = breakdown.slice(0, 4); // show top 4 categories

  for (const item of topItems) {
    const rowStack = breakdownStack.addStack();
    rowStack.layoutHorizontally();
    rowStack.centerAlignContent();

    // Color dot
    const colorHex = CATEGORY_COLORS[item.category] || '#B0BEC5';
    const dot = rowStack.addText('●');
    dot.textColor = new Color(colorHex);
    dot.font = Font.systemFont(8);

    rowStack.addSpacer(4);

    // Category name (truncated)
    const shortName = item.category.split(' ')[0];
    const nameText = rowStack.addText(shortName);
    nameText.textColor = GRAY;
    nameText.font = Font.systemFont(10);

    rowStack.addSpacer();

    // Amount
    const amtText = rowStack.addText(`$${item.total.toFixed(0)}`);
    amtText.textColor = WHITE;
    amtText.font = Font.mediumSystemFont(10);

    breakdownStack.addSpacer(3);
  }

  if (breakdown.length === 0) {
    const emptyText = breakdownStack.addText('No data yet');
    emptyText.textColor = GRAY;
    emptyText.font = Font.systemFont(11);
  }

  widget.addSpacer();

  // Footer: last updated
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const footer = widget.addText(`Updated ${timeStr}`);
  footer.textColor = GRAY;
  footer.font = Font.systemFont(8);

  return widget;
}

// ── Refresh helpers ─────────────────────────────────────────
function shouldRefetch() {
  if (!Keychain.contains(LAST_FETCH_KEY)) return true;
  const lastFetch = parseInt(Keychain.get(LAST_FETCH_KEY), 10);
  const ageSeconds = (Date.now() - lastFetch) / 1000;
  return ageSeconds >= REFRESH_INTERVAL_S;
}

function markFetched() {
  Keychain.set(LAST_FETCH_KEY, String(Date.now()));
}

// ── Main ────────────────────────────────────────────────────
async function run() {
  const period = getSavedPeriod();

  if (!config.runsInWidget) {
    const alert = new Alert();
    alert.title = '💸 Spent Widget';
    alert.message = `Current period: ${capitalize(period)}\nChange it below or tap Preview to see the widget.`;
    alert.addAction('Switch to ' + capitalize(cyclePeriod(period)));
    alert.addAction('Preview Widget');
    alert.addCancelAction('Cancel');

    await alert.present();
  }

  // Always fetch fresh data if the last fetch was more than REFRESH_INTERVAL_S ago
  let summary, chartImg;
  if (shouldRefetch()) {
    [summary, chartImg] = await Promise.all([fetchSummary(period), fetchDonutChart(period)]);
    if (summary) markFetched(); // only stamp if we got good data
  } else {
    [summary, chartImg] = await Promise.all([fetchSummary(period), fetchDonutChart(period)]);
    markFetched();
  }

  const widget = await buildWidget(summary, chartImg, period);

  // Ask Scriptable to re-run this script in ~1 minute so the widget
  // reflects new transactions quickly without waiting for iOS to schedule it.
  const nextRefresh = new Date(Date.now() + REFRESH_INTERVAL_S * 1000);
  widget.refreshAfterDate = nextRefresh;

  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    widget.presentMedium();
  }

  Script.complete();
}

await run();
