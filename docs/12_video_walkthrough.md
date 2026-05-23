# MCP Agent — Video Walkthrough Script & Recording Guide

> **Brief deliverable**: *"Provide a video showing the interaction and explain the architecture briefly."*

This document is the script + recording instructions for a **2-3 minute** video demonstrating the Air Côte d'Ivoire MCP agent in Claude Desktop. The video is to be tournée after Claude Desktop is wired to the MCP server (see `mcp_server/README.md`).

---

## 1. Pre-flight checklist (do this once before recording)

1. ✅ `dbt build` already ran (the file `dbt/airline.duckdb` exists).
2. ✅ Edit `%APPDATA%\Claude\claude_desktop_config.json` with the block from `mcp_server/claude_desktop_config.json`, replacing `<PROJECT_ROOT>` with the absolute path.
3. ✅ Restart Claude Desktop fully.
4. ✅ Verify in Claude Desktop's bottom-right "MCP" indicator that **`air-cote-divoire`** appears with **8 tools** and **1 resource**.
5. ✅ Recording tool ready: **ShareX** (Windows, free) or **OBS**. Output: MP4 720p, 30fps, ~20-30 MB.
6. ✅ Open the architecture slide in section §3 below in a second window (will be shown briefly on screen at 0:20).
7. ✅ Microphone test: speak the first sentence aloud, check audio level.

---

## 2. The script (voice-over + on-screen actions)

> Total target duration: **2 min 30 s**. All voice-over in **English**, neutral pace.

### `0:00 — 0:20` ▸ Hook + tool inventory

**Action on screen**: Claude Desktop open, sidebar visible with the 8 MCP tools listed.

**Voice-over**:
> "This is the Air Côte d'Ivoire analytics agent. It runs as a Model Context Protocol server I built in Python — eight specialised tools that expose dbt marts and five inferred business concepts. Let me ask it the three questions that drive our growth-allocation decision."

### `0:20 — 0:35` ▸ Architecture slide (15 seconds)

**Action on screen**: switch to the architecture slide (see §3 below).

**Voice-over**:
> "Architecture, in one breath. dbt builds a DuckDB database with marts, an ontology layer, and NLP-enriched feedback. The MCP server exposes eight tools, all read-only, all parameterised, all returning an audit envelope with the SQL they executed. Claude calls them over stdio."

### `0:35 — 1:00` ▸ Question 1 — Where to invest budget

**Action on screen**: switch back to Claude Desktop. Type and send:

> **"Which strategic routes are underperforming, and which routes have operational issues? Suggest where to put next quarter's budget."**

Watch the agent call `list_strategic_underperforming_routes` then `list_irops_heavy_routes`, both visible in the sidebar.

**Voice-over while it runs**:
> "Question one: where do we invest? The agent calls the strategic-route ontology, then the IROPS ontology — both pre-classified by our dbt models. The answer is grounded in the ontology, not improvised."

### `1:00 — 1:35` ▸ Question 2 — High-value customers at risk

**Action**: type and send:

> **"List the 5 most at-risk high-value customers and explain the signals."**

The agent calls `list_high_value_at_risk_customers(limit=5, sort_by='ltv')` and produces a table with monetary, recency, complaint_count, avg_sentiment.

**Voice-over**:
> "Question two: who do I need to retain? The agent reads the high-value at-risk concept directly. Each row is a customer the airline flagged programmatically — top of the dataset, $12 million lifetime value at stake."

### `1:35 — 2:15` ▸ Question 3 — Complaints on a specific route

**Action**: type and send:

> **"What are the dominant complaints on route R005, and quote a few customers verbatim."**

The agent calls `get_network_summary(route_id='R005')` THEN `search_feedback_text(route_id='R005', sentiment_label='negative', limit=4)`. The second call returns four raw feedbacks in FR and EN.

**Voice-over** (the key moment):
> "Question three is the hardest because it requires the unstructured source. The agent first checks the route's structured KPIs — load factor, OTP15, cancellation rate. Then it queries the customer feedback text — the actual words customers wrote. You see French and English complaints surfacing on seat comfort, delays, the lounge, the crew. This is structured plus unstructured, in one conversation."

### `2:15 — 2:30` ▸ Outro

**Action**: close Claude Desktop window, show the README on GitHub.

**Voice-over**:
> "Eight tools, one glossary resource, full audit trail, seventeen passing tests. The whole MCP server is in the `mcp_server/` folder of this repository, fully reproducible from a clean clone."

---

## 3. Architecture slide (paste this on screen at 0:20-0:35)

Open this in a second window — full-screen — and switch to it at 0:20:

```
   ┌────────────────────────────────────────────────────────────────┐
   │                       Claude Desktop                            │
   │              (MCP client over stdio)                            │
   └─────────────────────────────┬──────────────────────────────────┘
                                 │  JSON-RPC
                                 ▼
   ┌────────────────────────────────────────────────────────────────┐
   │              mcp_server (Python, FastMCP)                       │
   │                                                                 │
   │   ┌──────────────────────┐    ┌────────────────────────────┐  │
   │   │  8 Tools             │    │  1 Resource                 │  │
   │   │  • 5 ontology        │    │  • airline glossary         │  │
   │   │  • 1 network summary │    │    (LF, RASK, IROPS, …)     │  │
   │   │  • 1 feedback search │    └────────────────────────────┘  │
   │   │  • 1 compare_routes  │                                     │
   │   └──────────┬───────────┘                                     │
   │              │                                                 │
   │   ┌──────────▼───────────────────────────┐                    │
   │   │  safety.py — read-only enforcement,  │                    │
   │   │  row limit (1000), audit envelope    │                    │
   │   └──────────┬───────────────────────────┘                    │
   └──────────────┼─────────────────────────────────────────────────┘
                  │
                  ▼
   ┌────────────────────────────────────────────────────────────────┐
   │              dbt/airline.duckdb (read-only)                     │
   │  ├── main_marts        ← structured KPIs, dimensions, facts    │
   │  ├── main_intermediate ← NLP-enriched, route monthly perf      │
   │  └── main_ontology     ← 5 inferred concepts (Part 2)          │
   └────────────────────────────────────────────────────────────────┘
```

Suggested format: paste into a single-slide Google Slides or a plain image — anything that's readable for 15 seconds at the viewer's resolution.

---

## 4. Recording instructions

### ShareX (recommended on Windows)

1. Open ShareX → **Capture → Screen recording (GIF or video)** → choose **video**.
2. Codec: **x264** (compatible everywhere). Bitrate: 4-6 Mbps. Resolution: 1280×720 minimum.
3. Audio: enable system audio + microphone.
4. Start recording, then switch to Claude Desktop and run through the script.
5. Stop with the hotkey when you finish the outro.
6. Save as **`docs/mcp_walkthrough.mp4`** in the project.

### OBS Studio (alternative)

1. Set up a single scene with two sources: **Display Capture** (full screen) and **Audio Input Capture** (mic).
2. Settings → Output → Recording → Format **MP4**, encoder **x264**, CRF 23.
3. File → Recording Path → set to `docs/`.
4. Run through the script, then stop.

### Post-recording (optional, ≤10 min of work)

- Trim head/tail with **ShotCut** (free, cross-platform) or any editor of your choice.
- Optionally add 1-2 captions to call out the tool names as they're invoked.
- Compress to ≤ 30 MB so it fits comfortably in a GitHub release or PR.

---

## 5. Where to put the final file

| File | Path |
|---|---|
| Recorded video | `docs/mcp_walkthrough.mp4` |
| This script | `docs/12_video_walkthrough.md` (already here) |
| Architecture diagram | embedded in this file (section §3) |

Then update `README.md` Part-4 section with a link to the video.

---

## 6. Quick FAQ

**Q: What if Claude Desktop doesn't show the 8 tools?**
A: Verify the absolute path in `claude_desktop_config.json` is correct, that the venv Python exists, that `dbt build` ran, and restart Claude Desktop fully (System tray → Quit, not just Close).

**Q: What if a tool errors during the live demo?**
A: The recorded `mcp_server/smoke_test.py` already validates 5/5 tools end-to-end. If a tool fails live, re-run `dbt build`, then `mcp_server/smoke_test.py`, then restart Claude Desktop.

**Q: Should the video be in French?**
A: No — the rest of the project documentation is in English, so the video stays in English for consistency with the panel.

---

## 7. Acceptance check against the brief

| Brief requirement | Covered in this video |
|---|---|
| *"MCP server or equivalent tool layer"* | ✅ Architecture slide at 0:20 |
| *"AI assistant can use it"* | ✅ Claude Desktop end-to-end |
| *"Structured + ≥1 unstructured source"* | ✅ Question 3 (KPIs + raw feedback) |
| *"Demonstrate a few grounded questions"* | ✅ Q1 + Q2 + Q3 (= the 3 brief examples) |
| *"Explain the architecture briefly"* | ✅ 15-second slide + voice-over |
