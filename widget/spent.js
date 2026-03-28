// Spent Widget — Phase 4
// A Scriptable widget that displays your spending donut chart on the iOS home screen.
//
// HOW TO USE (Phase 4):
//   1. Install Scriptable from the App Store (free)
//   2. Paste this script into a new Scriptable script
//   3. Set BACKEND_URL to your deployed backend URL
//   4. Add a Scriptable widget to your home screen and select this script
//
// WHAT IT WILL DO:
//   - Calls GET /api/v1/summary to fetch category totals
//   - Renders a donut chart with spending by category
//   - Shows total spend for the current month
//   - Updates automatically when the widget refreshes (every ~15 minutes)

// ─── Configuration ────────────────────────────────────────────────────────────

// TODO (Phase 4): Replace with your deployed backend URL
// For local testing you can use ngrok to expose localhost:8000
const BACKEND_URL = "https://your-backend-url.com"
const API_PATH = "/api/v1/summary"

// ─── Color palette for categories ─────────────────────────────────────────────

const CATEGORY_COLORS = {
  food:          new Color("#FF6B6B"),
  transport:     new Color("#4ECDC4"),
  entertainment: new Color("#45B7D1"),
  shopping:      new Color("#96CEB4"),
  health:        new Color("#FFEAA7"),
  utilities:     new Color("#DDA0DD"),
  other:         new Color("#B0BEC5"),
}

// ─── Main widget logic ────────────────────────────────────────────────────────

async function fetchSummary() {
  // TODO (Phase 4): Fetch spending summary from the backend
  // const req = new Request(`${BACKEND_URL}${API_PATH}`)
  // return await req.loadJSON()
  return null
}

async function buildWidget(summary) {
  const widget = new ListWidget()
  widget.backgroundColor = new Color("#1C1C1E")

  if (!summary) {
    // TODO (Phase 4): Show a "not available" state with a reload prompt
    const text = widget.addText("Spent — data unavailable")
    text.textColor = Color.white()
    return widget
  }

  // TODO (Phase 4):
  //   1. Draw a donut chart using DrawContext
  //   2. Add category labels and amounts
  //   3. Show the monthly total at the top
  //   4. Style with the CATEGORY_COLORS palette

  return widget
}

// ─── Entry point ──────────────────────────────────────────────────────────────

const summary = await fetchSummary()
const widget = await buildWidget(summary)

if (config.runsInWidget) {
  Script.setWidget(widget)
} else {
  // Preview in Scriptable app
  widget.presentSmall()
}

Script.complete()
