"""Crake — Bioluminescence theme CSS injection."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Fira+Code:wght@300;400;500;600&display=swap');

/* ══════════════════════════════════════════════════════════════
   CRAKE  ·  BIOLUMINESCENCE
   ─────────────────────────────────────────────────────────────
   Deep-ocean aesthetic: abyss black, glowing teal like
   dinoflagellates at midnight.
   ─────────────────────────────────────────────────────────────
   --bg:      #03050A   abyss
   --s1:      #070D15   deep surface
   --s2:      #0D1825   raised surface
   --b1:      #112030   subtle border
   --b2:      #1A3040   visible border
   --muted:   #3A7080   ocean muted
   --dim:     #1A3040   very dim
   --glow:    #00E5A0   bioluminescent teal
   --blue:    #0098FF   electric blue
   --amber:   #FFA43C   warm amber
   --text:    #C8E8F0   cold white
   --body:    #7AAAB8   body text
══════════════════════════════════════════════════════════════ */

/* ── Base typography ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"], .stApp {
    font-family: 'Outfit', 'DM Sans', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ── Kill Streamlit chrome ── */
[data-testid="stDecoration"],
#MainMenu, footer { display: none !important; }
/* Hide toolbar actions (Deploy, menu) but NOT the toolbar itself — expand button lives there */
[data-testid="stToolbarActions"],
[data-testid="stAppDeployButton"],
[data-testid="stMainMenuButton"] { display: none !important; }
/* Keep toolbar invisible but rendered so the fixed expand button can escape */
[data-testid="stToolbar"] {
    background: transparent !important;
    pointer-events: none !important;
}
[data-testid="stExpandSidebarButton"] {
    pointer-events: auto !important;
}

/* stHeader: invisible but keep it in flow so expand button can be rescued */
[data-testid="stHeader"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    height: 0px !important;
    min-height: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
}
/* "Expand sidebar" button — lives in stHeader (0-height), rescue with fixed positioning */
[data-testid="stExpandSidebarButton"] {
    position: fixed !important;
    top: 14px !important;
    left: 12px !important;
    z-index: 10000 !important;
    min-width: 32px !important;
    min-height: 32px !important;
    width: 32px !important;
    height: 32px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 6px !important;
    border-radius: 6px !important;
    color: #00E5A0 !important;
    background: rgba(0,229,160,0.06) !important;
    border: 1px solid rgba(0,229,160,0.15) !important;
    cursor: pointer !important;
    transition: color 0.15s, background 0.15s, border-color 0.15s !important;
    overflow: visible !important;
}
[data-testid="stExpandSidebarButton"]:hover {
    color: #C8E8F0 !important;
    background: rgba(0,229,160,0.14) !important;
    border-color: rgba(0,229,160,0.3) !important;
}
[data-testid="stExpandSidebarButton"] span,
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
    color: #00E5A0 !important;
    font-size: 18px !important;
    line-height: 1 !important;
}
/* Collapse button inside the sidebar */
[data-testid="stSidebarCollapseButton"] button {
    color: #00E5A0 !important;
    background: rgba(0,229,160,0.06) !important;
    border: 1px solid rgba(0,229,160,0.15) !important;
    border-radius: 6px !important;
    transition: color 0.15s, background 0.15s, border-color 0.15s !important;
}
[data-testid="stSidebarCollapseButton"] button:hover {
    color: #C8E8F0 !important;
    background: rgba(0,229,160,0.14) !important;
    border-color: rgba(0,229,160,0.3) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #070D15 !important;
    border-right: 1px solid #1E3A50 !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 16px 8px !important;
}

/* ── Main columns layout: fill viewport height ── */
/* Force the top-level two-column block to fill the remaining viewport */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
    min-height: calc(100vh - 66px) !important;
}
/* Chat column inner block: flex column so messages can grow */
[data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child > [data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlock"] {
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
}
/* Messages box: grow to fill remaining space in the column */
[data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stVerticalBlockBorderWrapper"] {
    flex: 1 1 0 !important;
    height: auto !important;
    min-height: 200px !important;
}

/* ── Right column: sticky ── */
[data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2),
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
    position: sticky;
    top: 58px;
    align-self: flex-start;
    max-height: calc(100vh - 66px);
    overflow-y: auto;
}

/* ── App background with bioluminescent dot grid ── */
.stApp {
    background: #03050A !important;
    background-image: radial-gradient(rgba(0,229,160,0.045) 1px, transparent 1px) !important;
    background-size: 28px 28px !important;
}
.main .block-container,
[data-testid="stMainBlockContainer"] {
    background: transparent !important;
    padding: 0 !important;
    padding-bottom: 8px !important;
    max-width: 100% !important;
}
/* Kill any residual Streamlit top gap */
[data-testid="stAppViewContainer"] > .main > .block-container > div:first-child {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

/* ── Keyframe animations ── */
@keyframes breathe {
    0%,100% { box-shadow: 0 0 12px rgba(0,229,160,.35), 0 0 28px rgba(0,229,160,.12); }
    50%      { box-shadow: 0 0 22px rgba(0,229,160,.55), 0 0 48px rgba(0,229,160,.2); }
}
@keyframes msgIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes glowPulse {
    0%,100% { opacity:.6; }
    50%     { opacity:1; }
}

/* ══════════════════════════════════════════════════════════════
   HEADER BAR
══════════════════════════════════════════════════════════════ */
.crake-header {
    background: rgba(3,5,10,0.94);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-bottom: 1px solid rgba(0,229,160,0.08);
    padding: 0 24px 0 48px;
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 999;
}
.crake-logo-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
}
.crake-logo-mark {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    background: linear-gradient(145deg, #00E5A0 0%, #00A870 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
    animation: breathe 3.5s ease-in-out infinite;
}
.crake-wordmark {
    font-size: 18px;
    font-weight: 700;
    color: #C8E8F0;
    letter-spacing: -0.03em;
    font-family: 'Outfit', sans-serif;
}
.crake-wordmark b { color: #00E5A0; font-weight: 800; }
.crake-header-status {
    display: flex;
    align-items: center;
    gap: 8px;
}
.crake-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(0,229,160,0.04);
    border: 1px solid rgba(0,229,160,0.14);
    border-radius: 100px;
    padding: 4px 12px 4px 8px;
    font-size: 12px;
    color: #6AADC0;
    white-space: nowrap;
    max-width: 240px;
    overflow: hidden;
    text-overflow: ellipsis;
    font-family: 'Outfit', sans-serif;
}
.crake-pip {
    width: 6px; height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}
.pip-green  { background: #00E5A0; box-shadow: 0 0 6px rgba(0,229,160,.9); }
.pip-amber  { background: #FFA43C; box-shadow: 0 0 6px rgba(255,164,60,.9); }
.pip-blue   { background: #0098FF; box-shadow: 0 0 6px rgba(0,152,255,.9); }
.pip-red    { background: #FF5C5C; box-shadow: 0 0 6px rgba(255,92,92,.9); }

/* ══════════════════════════════════════════════════════════════
   INTRO PAGE
══════════════════════════════════════════════════════════════ */
.crake-intro-wrap {
    position: relative;
    overflow: hidden;
    padding: 48px 40px 32px;
}
.crake-intro-glow {
    pointer-events: none;
    position: absolute;
    top: -100px;
    left: 50%;
    transform: translateX(-50%);
    width: 1000px;
    height: 600px;
    background: radial-gradient(
        ellipse at 50% 0%,
        rgba(0,229,160,0.07) 0%,
        rgba(0,152,255,0.04) 45%,
        transparent 70%
    );
}
.crake-intro-hero {
    text-align: center;
    position: relative;
    z-index: 1;
    margin-bottom: 40px;
}
.crake-intro-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(0,229,160,0.05);
    border: 1px solid rgba(0,229,160,0.15);
    border-radius: 100px;
    padding: 4px 14px;
    font-size: 11px;
    font-weight: 600;
    color: #00E5A0;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 22px;
    font-family: 'Outfit', sans-serif;
}
.crake-intro-title {
    font-size: 54px;
    font-weight: 800;
    letter-spacing: -0.045em;
    line-height: 1.07;
    margin-bottom: 20px;
    background: linear-gradient(155deg, #C8E8F0 0%, #6AADC0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-family: 'Outfit', sans-serif;
}
.crake-intro-title span {
    background: linear-gradient(135deg, #00E5A0 0%, #00CFFF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.crake-intro-sub {
    display: block;
    width: 100%;
    font-size: 16px;
    color: #3A7080;
    line-height: 1.68;
    max-width: 560px;
    margin: 8px auto 0;
    text-align: center !important;
    font-family: 'Outfit', sans-serif;
}

/* ── Intro command table ── */
.crake-cmd-table {
    width: 100%;
    max-width: 560px;
    margin: 0 auto;
    border-collapse: collapse;
}
.crake-cmd-table td {
    padding: 9px 0;
    vertical-align: middle;
    border-bottom: 1px solid #112030;
}
.crake-cmd-table tr:last-child td { border-bottom: none; }
.crake-cmd-table .cmd-key {
    font-family: 'Fira Code', monospace;
    font-size: 14px;
    color: #00E5A0;
    white-space: nowrap;
    padding-right: 32px;
    width: 1%;
}
.crake-cmd-table .cmd-desc {
    font-family: 'Outfit', sans-serif;
    font-size: 15px;
    color: #3A7080;
    padding-left: 28px;
    border-left: 1px solid #112030;
}
.crake-step-card {
    background: #070D15;
    border: 1px solid #112030;
    border-radius: 14px;
    padding: 20px 16px;
    height: 100%;
    transition: border-color 0.25s, box-shadow 0.25s, transform 0.2s;
    position: relative;
    overflow: hidden;
}
.crake-step-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,229,160,0.45), transparent);
    opacity: 0;
    transition: opacity 0.25s;
}
.crake-step-card:hover {
    border-color: rgba(0,229,160,0.2);
    box-shadow: 0 8px 40px rgba(0,0,0,0.5), 0 0 20px rgba(0,229,160,0.05);
    transform: translateY(-2px);
}
.crake-step-card:hover::before { opacity: 1; }
.crake-step-num {
    font-size: 10px;
    font-weight: 700;
    color: #00E5A0;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 10px;
    font-family: 'Fira Code', monospace;
}
.crake-step-icon {
    font-size: 26px;
    margin-bottom: 10px;
    display: block;
}
.crake-step-title {
    font-size: 15px;
    font-weight: 600;
    color: #C8E8F0;
    margin-bottom: 8px;
    letter-spacing: -0.01em;
    font-family: 'Outfit', sans-serif;
}
.crake-step-desc {
    font-size: 13px;
    color: #3A7080;
    line-height: 1.6;
    margin-bottom: 16px;
    font-family: 'Outfit', sans-serif;
}
.crake-step-cmd {
    font-family: 'Fira Code', monospace;
    font-size: 11.5px;
    color: #00E5A0;
    background: rgba(0,229,160,0.05);
    border: 1px solid rgba(0,229,160,0.12);
    border-radius: 6px;
    padding: 3px 8px;
    display: inline-block;
}
.crake-section-label {
    font-size: 10px;
    font-weight: 700;
    color: #3A7080;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 14px;
    font-family: 'Fira Code', monospace;
}
.crake-example-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #070D15;
    border: 1px solid #112030;
    border-radius: 100px;
    padding: 7px 16px;
    font-size: 13px;
    color: #3A7080;
    margin: 4px 6px 4px 0;
    transition: border-color 0.2s, color 0.2s, box-shadow 0.2s;
    cursor: pointer;
    font-family: 'Outfit', sans-serif;
}
.crake-example-chip:hover {
    border-color: rgba(0,229,160,0.25);
    color: #C8E8F0;
    box-shadow: 0 0 14px rgba(0,229,160,0.06);
}
.crake-example-chip code {
    font-family: 'Fira Code', monospace;
    font-size: 11.5px;
    color: #00E5A0;
    background: transparent;
    border: none;
    padding: 0;
}
.crake-intro-footer {
    text-align: center;
    font-size: 12.5px;
    color: #3A7080;
    margin-top: 36px;
    padding-bottom: 8px;
    font-family: 'Outfit', sans-serif;
}
.crake-intro-footer span { color: #3A7080; }

/* ══════════════════════════════════════════════════════════════
   CHAT PANEL
══════════════════════════════════════════════════════════════ */
.crake-msg-user-row {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    margin: 10px 0;
    animation: msgIn 0.2s ease-out;
}
.crake-msg-ai-row {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    margin: 10px 0;
    animation: msgIn 0.2s ease-out;
}
.crake-role-user {
    font-size: 9px;
    font-weight: 700;
    color: #3A7080;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 4px;
    padding-right: 4px;
    font-family: 'Fira Code', monospace;
}
.crake-role-ai {
    font-size: 9px;
    font-weight: 700;
    color: rgba(0,229,160,0.6);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 4px;
    padding-left: 4px;
    font-family: 'Fira Code', monospace;
}
.crake-msg-user {
    background: rgba(0,152,255,0.07);
    border: 1px solid rgba(0,152,255,0.16);
    color: #C8E8F0;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 16px;
    max-width: 86%;
    font-size: 14.5px;
    line-height: 1.65;
    word-break: break-word;
    font-family: 'Outfit', sans-serif;
}
.crake-msg-ai {
    background: #070D15;
    border: 1px solid #112030;
    border-left: none;
    border-radius: 4px 18px 18px 18px;
    padding: 12px 16px 12px 16px;
    max-width: 92%;
    font-size: 14.5px;
    line-height: 1.68;
    color: #7AAAB8;
    word-break: break-word;
    position: relative;
    font-family: 'Outfit', sans-serif;
}
.crake-msg-ai::before {
    content: "";
    position: absolute;
    left: 0;
    top: 8px; bottom: 8px;
    width: 2px;
    background: linear-gradient(180deg, #00E5A0 0%, rgba(0,229,160,0.08) 100%);
    border-radius: 0 2px 2px 0;
}
.crake-tool-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(0,229,160,0.05);
    border: 1px solid rgba(0,229,160,0.12);
    border-radius: 6px;
    padding: 2px 9px 2px 7px;
    font-size: 11px;
    color: #00E5A0;
    font-family: 'Fira Code', monospace;
    margin: 1px 3px 1px 0;
}
.crake-chat-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48px 24px 32px;
    text-align: center;
}
.crake-chat-empty-icon { font-size: 40px; margin-bottom: 14px; opacity: 0.25; }
.crake-chat-empty-text { font-size: 14px; color: #3A7080; font-family: 'Outfit', sans-serif; }

/* ── Command hints ── */
.crake-cmd-wrap {
    padding: 6px 2px 12px;
    border-top: 1px solid #112030;
    margin-top: 8px;
}
.crake-cmd-label {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #3A7080;
    margin-bottom: 8px;
    padding: 8px 0 4px;
    font-family: 'Fira Code', monospace;
}

/* ── Hide old sticky chat input (replaced by embedded form) ── */
[data-testid="stBottom"] { display: none !important; }

/* ── Chat window card ── */
.crake-chat-win-header {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #3A7080;
    padding: 8px 4px 10px;
    font-family: 'Fira Code', monospace;
}

/* ── Embedded text input (chat form) ── */
[data-testid="stForm"] [data-testid="stTextInput"] input {
    background: #070D15 !important;
    border: 1px solid #1A3040 !important;
    border-radius: 12px !important;
    color: #C8E8F0 !important;
    font-size: 14px !important;
    caret-color: #00E5A0 !important;
    font-family: 'Outfit', sans-serif !important;
    padding: 10px 16px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
[data-testid="stForm"] [data-testid="stTextInput"] input:focus {
    border-color: rgba(0,229,160,0.35) !important;
    box-shadow: 0 0 0 3px rgba(0,229,160,0.06) !important;
    outline: none !important;
}
[data-testid="stForm"] [data-testid="stTextInput"] input::placeholder {
    color: #3A7080 !important;
}

/* ── Send button (the ↑ submit) ── */
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
    background: #00E5A0 !important;
    color: #03050A !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    height: 42px !important;
    transition: background 0.15s, box-shadow 0.15s !important;
}
[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
    background: #00CFAA !important;
    box-shadow: 0 0 16px rgba(0,229,160,0.4) !important;
}

/* ── Remove form border/padding ── */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* ══════════════════════════════════════════════════════════════
   DATA PANEL
══════════════════════════════════════════════════════════════ */
.crake-data-divider {
    width: 1px;
    background: #112030;
    align-self: stretch;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid #112030;
    gap: 0;
    padding: 0 2px;
}
.stTabs [data-baseweb="tab"] {
    color: #3A7080;
    font-size: 12.5px;
    font-weight: 500;
    padding: 8px 14px;
    border-radius: 0;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: color 0.15s;
    font-family: 'Outfit', sans-serif;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #6AADC0;
    background: rgba(0,229,160,0.02) !important;
}
.stTabs [aria-selected="true"] {
    color: #C8E8F0 !important;
    background: transparent !important;
    border-bottom: 2px solid #00E5A0 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: transparent;
    padding: 16px 8px;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #070D15;
    border: 1px solid #112030;
    border-radius: 10px;
    padding: 12px 16px;
    transition: border-color 0.2s, box-shadow 0.2s;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(0,229,160,0.15);
    box-shadow: 0 0 20px rgba(0,229,160,0.04);
}
[data-testid="stMetricLabel"] {
    color: #3A7080;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-family: 'Outfit', sans-serif;
}
[data-testid="stMetricValue"] {
    color: #C8E8F0;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.025em;
    font-family: 'Outfit', sans-serif;
}

/* ── Code blocks ── */
.stCode, code, pre {
    font-family: 'Fira Code', 'JetBrains Mono', monospace !important;
    font-size: 12.5px;
    background: #03050A !important;
    border: 1px solid #112030 !important;
    border-radius: 8px;
}

/* ── DataFrames ── */
[data-testid="stDataFrame"] {
    border: 1px solid #112030;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Buttons ── */
.stDownloadButton > button, .stButton > button {
    background: #070D15;
    color: #6AADC0;
    border: 1px solid #1A3040;
    border-radius: 8px;
    font-size: 13.5px;
    font-weight: 500;
    transition: all 0.15s;
    padding: 8px 18px;
    font-family: 'Outfit', sans-serif;
}
.stDownloadButton > button:hover, .stButton > button:hover {
    background: #0D1825;
    border-color: rgba(0,229,160,0.3);
    color: #00E5A0;
    box-shadow: 0 0 16px rgba(0,229,160,0.1);
}

/* ── Alerts ── */
.stAlert { border-radius: 10px; font-size: 13.5px; }

/* ── Hide Streamlit exception dialog search links ── */
[data-testid="stException"] + [data-testid="stHorizontalBlock"],
[data-testid="stException"] + div > [data-testid="stHorizontalBlock"] {
    display: none !important;
}
[data-testid="stException"] {
    background: #070D15 !important;
    border: 1px solid rgba(255,92,92,0.2) !important;
    border-radius: 10px !important;
}

/* ── Caption ── */
.stCaption, small, [data-testid="stCaptionContainer"] p {
    color: #3A7080 !important;
    font-family: 'Outfit', sans-serif;
}

/* ── Divider ── */
hr { border-color: #112030 !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] { color: #00E5A0; }

/* ── Global text ── */
p, li, .stMarkdown p { color: #7AAAB8; font-family: 'Outfit', sans-serif; }
h1, h2, h3 { color: #C8E8F0; letter-spacing: -0.025em; font-family: 'Outfit', sans-serif; }
strong, b { color: #C8E8F0; }

/* ── Scrollbars ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1A3040; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #2A4050; }

/* ── Bar chart ── */
[data-testid="stVegaLiteChart"] { border-radius: 8px; overflow: hidden; }

/* ── Organism link ── */
a[href*="ncbi.nlm.nih.gov"]:hover {
    color: #00E5A0 !important;
    border-bottom-color: #00E5A0 !important;
}

/* ── Tooltip cursor ── */
[title] { cursor: help; }
.crake-pill[title] { cursor: default; }

/* ══════════════════════════════════════════════════════════════
   HEADER STATS (top-right)
══════════════════════════════════════════════════════════════ */
.crake-header-stats {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 180px;
    justify-content: flex-end;
}
.crake-stat {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: #3A7080;
    font-variant-numeric: tabular-nums;
    transition: color .15s;
    font-family: 'Fira Code', monospace;
}
.crake-stat:hover { color: #3A7080; }
.crake-kbd-hint {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: default;
}
.crake-kbd {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(0,229,160,0.04);
    border: 1px solid rgba(0,229,160,0.12);
    border-bottom: 2px solid rgba(0,229,160,0.2);
    border-radius: 5px;
    padding: 1px 7px;
    font-family: 'Fira Code', monospace;
    font-size: 11px;
    color: #00E5A0;
    font-style: normal;
    line-height: 1.6;
}
.crake-kbd-label {
    font-size: 11.5px;
    color: #3A7080;
    white-space: nowrap;
    font-family: 'Outfit', sans-serif;
}

/* ══════════════════════════════════════════════════════════════
   SIDEBAR — saved conversations
══════════════════════════════════════════════════════════════ */
.crake-sb-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .12em;
    color: #3A7080;
    padding: 0 0 10px;
    border-bottom: 1px solid #112030;
    margin-bottom: 12px;
    font-family: 'Fira Code', monospace;
}
.crake-sb-empty {
    font-size: 13px;
    color: #3A7080;
    padding: 4px;
    line-height: 1.6;
    font-family: 'Outfit', sans-serif;
}
.crake-sb-item {
    padding: 8px 0;
    border-bottom: 1px solid #112030;
    cursor: pointer;
    transition: background .15s;
}
.crake-sb-item:hover { background: #070D15; }
.crake-sb-item-name {
    font-size: 13px;
    color: #6AADC0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 3px;
    font-family: 'Outfit', sans-serif;
}
.crake-sb-item-meta {
    font-size: 11px;
    color: #3A7080;
    font-family: 'Fira Code', monospace;
}

/* ══════════════════════════════════════════════════════════════
   FEATURED PIPELINE CARD (intro page)
══════════════════════════════════════════════════════════════ */
.crake-pipeline-card {
    background: linear-gradient(135deg, rgba(0,229,160,0.05) 0%, rgba(0,152,255,0.04) 100%);
    border: 1px solid rgba(0,229,160,0.2);
    border-radius: 14px;
    padding: 20px 24px;
    max-width: 560px;
    margin: 0 auto 32px;
    position: relative;
    z-index: 1;
}
.crake-pipeline-badge {
    display: inline-block;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #00E5A0;
    background: rgba(0,229,160,0.08);
    border: 1px solid rgba(0,229,160,0.2);
    border-radius: 100px;
    padding: 2px 10px;
    margin-bottom: 10px;
    font-family: 'Fira Code', monospace;
}
.crake-pipeline-title {
    font-size: 18px;
    font-weight: 700;
    color: #C8E8F0;
    letter-spacing: -0.02em;
    margin-bottom: 12px;
    font-family: 'Outfit', sans-serif;
}
.crake-pipeline-steps {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 12px;
}
.crake-pipeline-step {
    background: rgba(0,229,160,0.06);
    border: 1px solid rgba(0,229,160,0.15);
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    color: #6AADC0;
    font-family: 'Outfit', sans-serif;
    white-space: nowrap;
}
.crake-pipeline-arrow {
    color: rgba(0,229,160,0.4);
    font-size: 14px;
    font-weight: 300;
}
.crake-pipeline-desc {
    font-size: 13px;
    color: #3A7080;
    line-height: 1.6;
    margin-bottom: 12px;
    font-family: 'Outfit', sans-serif;
}
.crake-pipeline-desc b { color: #6AADC0; }
.crake-pipeline-desc code {
    font-family: 'Fira Code', monospace;
    font-size: 12px;
    color: #00E5A0;
    background: rgba(0,229,160,0.06);
    border: 1px solid rgba(0,229,160,0.12);
    border-radius: 4px;
    padding: 1px 6px;
}
.crake-pipeline-example {
    display: block;
    font-family: 'Fira Code', monospace;
    font-size: 12px;
    color: rgba(0,229,160,0.7);
    background: rgba(0,229,160,0.04);
    border: 1px solid rgba(0,229,160,0.1);
    border-radius: 8px;
    padding: 8px 12px;
    word-break: break-all;
}

/* ══════════════════════════════════════════════════════════════
   INDUCIBLE PROMOTER CALLOUT (inline in chat)
══════════════════════════════════════════════════════════════ */
.crake-inducible-callout {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    background: rgba(255,164,60,0.06);
    border: 1px solid rgba(255,164,60,0.2);
    border-left: 3px solid #FFA43C;
    border-radius: 0 8px 8px 0;
    padding: 8px 12px;
    margin-top: 10px;
    font-size: 12.5px;
    line-height: 1.55;
}
.crake-inducible-icon {
    color: #FFA43C;
    font-size: 13px;
    flex-shrink: 0;
    margin-top: 1px;
}
.crake-inducible-text {
    color: #7AAAB8;
    font-family: 'Outfit', sans-serif;
}
.crake-inducible-text b { color: #FFA43C; }

/* ══════════════════════════════════════════════════════════════
   INLINE VALIDATION WARNINGS (in chat)
══════════════════════════════════════════════════════════════ */
.crake-val-warning-block {
    background: rgba(255,164,60,0.05);
    border: 1px solid rgba(255,164,60,0.18);
    border-radius: 10px;
    padding: 12px 16px;
    margin: 6px 0 4px;
    max-width: 92%;
}
.crake-val-warning-title {
    font-size: 11.5px;
    font-weight: 700;
    color: #FFA43C;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
    font-family: 'Fira Code', monospace;
}
.crake-val-warning-list {
    margin: 0;
    padding-left: 18px;
}
.crake-val-warning-item {
    font-size: 13px;
    color: #7AAAB8;
    line-height: 1.6;
    margin-bottom: 4px;
    font-family: 'Outfit', sans-serif;
}
</style>
"""


def inject_css() -> None:
    """Inject the Crake Obsidian theme CSS into the Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)


_PALETTE_SCRIPT = """
<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:transparent;">
<script>
(function() {
  var doc = window.parent.document;

  var CMDS = [
    {cmd:'/introduce-gene', usage:'/introduce-gene <gene> in <org> into <host>', desc:'End-to-end gene introduction pipeline'},
    {cmd:'/genesearch', usage:'/genesearch <query>',      desc:'Search for a gene by natural language'},
    {cmd:'/fetch',      usage:'/fetch <accession>',       desc:'Retrieve a sequence by NCBI accession'},
    {cmd:'/load',       usage:'/load <path>',             desc:'Import a local .dna / .gb / .fasta file'},
    {cmd:'/suggest',    usage:'/suggest <host>',          desc:'Recommend vector parts for a host'},
    {cmd:'/targets',    usage:'/targets <method>',        desc:'Find CRISPR or restriction edit sites'},
    {cmd:'/optimize',   usage:'/optimize <host>',         desc:'Codon-optimise sequence for a host'},
    {cmd:'/primers',    usage:'/primers [fwd] [rev]',     desc:'Design PCR primers (optional overhangs)'},
    {cmd:'/assemble',   usage:'/assemble <method>',       desc:'Simulate Gibson or restriction-ligation'},
    {cmd:'/validate',   usage:'/validate',                desc:'Check the current construct for issues'},
    {cmd:'/export',     usage:'/export <name>',           desc:'Write GenBank, FASTA, map & protocol'},
    {cmd:'/help',       usage:'/help',                    desc:'Show full command reference'},
  ];

  var palette = null;
  var ta = null;
  var idx = -1;
  var originalQuery = '/';   /* text user actually typed, before arrow navigation */
  var navigating = false;    /* true while arrow-key navigation is changing input */

  /* ── palette DOM ── */
  function mkPalette(){
    if(palette && doc.body.contains(palette)) return palette;
    if(palette){ try{ palette.remove(); }catch(e){} }
    palette = doc.createElement('div');
    palette.id = 'crake-pal';
    palette.style.cssText =
      'position:fixed;z-index:2147483647;display:none;' +
      'background:#070D15;border:1px solid #1A3040;border-radius:14px;' +
      'box-shadow:0 20px 60px rgba(0,0,0,.8),0 0 0 1px rgba(0,229,160,.06);' +
      'overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,Inter,sans-serif;';
    doc.body.appendChild(palette);
    return palette;
  }

  /* ── filter commands ── */
  function matches(q){
    var lower = q.toLowerCase();
    if(lower === '/') return CMDS;
    return CMDS.filter(function(c){ return c.cmd.indexOf(lower) === 0; });
  }

  /* ── position palette to span the full chat-input bar ── */
  function getPosRect(){
    var container = doc.querySelector('[data-testid="stChatInput"]');
    return container ? container.getBoundingClientRect()
                     : (ta ? ta.getBoundingClientRect() : null);
  }

  /* ── render palette ─────────────────────────────────────── */
  function renderPal(filterQuery){
    var m = matches(filterQuery);
    var p = mkPalette();
    if(!m.length){ p.style.display = 'none'; return; }

    var r = getPosRect();
    if(!r){ p.style.display = 'none'; return; }

    /* align exactly with the input bar */
    p.style.left     = r.left + 'px';
    p.style.width    = r.width + 'px';
    p.style.bottom   = (doc.documentElement.clientHeight - r.top + 6) + 'px';
    p.style.top      = 'auto';
    p.style.maxHeight = Math.min(r.top - 20, 420) + 'px';
    p.style.overflowY = 'auto';

    var html =
      '<div style="padding:8px 16px 7px;font-size:10px;font-weight:700;' +
      'color:#3A7080;text-transform:uppercase;letter-spacing:.12em;' +
      'border-bottom:1px solid #112030;position:sticky;top:0;background:#070D15;z-index:1;">' +
      'Commands — <span style="color:#3A7080;font-weight:400;text-transform:none;letter-spacing:0;">' +
      '↑↓ navigate · Tab confirm · Esc close</span></div>';

    m.forEach(function(c, i){
      var active = (i === idx);
      html +=
        '<div class="crake-pi" data-cmd="' + c.cmd + '" style="' +
        'display:flex;align-items:baseline;gap:12px;padding:10px 16px;cursor:pointer;' +
        'background:' + (active ? 'rgba(0,229,160,.07)' : 'transparent') + ';' +
        'border-left:2px solid ' + (active ? '#00E5A0' : 'transparent') + ';' +
        'transition:background .08s,border-color .08s;">' +
        '<code style="font-family:JetBrains Mono,Fira Mono,monospace;font-size:12px;' +
        'color:#00E5A0;background:rgba(0,229,160,.08);border:1px solid rgba(0,229,160,.16);' +
        'border-radius:5px;padding:2px 9px;white-space:nowrap;flex-shrink:0;">' + c.usage + '</code>' +
        '<span style="font-size:13px;color:#3A7080;line-height:1.4;">' + c.desc + '</span>' +
        '</div>';
    });

    p.innerHTML = html;
    p.style.display = 'block';

    p.querySelectorAll('.crake-pi').forEach(function(item, i){
      item.addEventListener('mousedown', function(e){
        e.preventDefault();
        confirmVal(item.getAttribute('data-cmd') + ' ');
      });
      item.addEventListener('mouseenter', function(){
        idx = i;
        renderPal(filterQuery);
      });
    });
  }

  /* ── set textarea value (React-safe, no submit) ── */
  function setVal(val){
    if(!ta) return;
    var proto = Object.getPrototypeOf(ta);
    var desc  = Object.getOwnPropertyDescriptor(proto, 'value');
    if(desc && desc.set){ desc.set.call(ta, val); }
    else { ta.value = val; }
    ta.dispatchEvent(new Event('input', {bubbles:true}));
    ta.selectionStart = ta.selectionEnd = val.length;
  }

  /* ── fill input and hide palette ── */
  function confirmVal(val){
    setVal(val);
    ta.focus();
    hide();
  }

  /* ── hide ── */
  function hide(){
    var p = mkPalette();
    p.style.display = 'none';
    idx = -1;
  }

  /* ── attach to textarea ── */
  function attachTo(el){
    if(el === ta) return;
    ta = el;

    el.addEventListener('input', function(){
      if(navigating) return;          /* ignore our own setVal() calls */
      idx = -1;
      originalQuery = el.value;
      if(el.value.startsWith('/')) renderPal(el.value);
      else hide();
    });

    el.addEventListener('keydown', function(e){
      var p = mkPalette();
      if(p.style.display === 'none') return;
      var items = p.querySelectorAll('.crake-pi');

      if(e.key === 'ArrowDown'){
        e.preventDefault(); e.stopPropagation();
        idx = Math.min(idx + 1, items.length - 1);
        /* fill the input with the highlighted command so user can see it */
        if(idx >= 0 && items[idx]){
          navigating = true;
          setVal(items[idx].getAttribute('data-cmd') + ' ');
          navigating = false;
        }
        renderPal(originalQuery);

      } else if(e.key === 'ArrowUp'){
        e.preventDefault(); e.stopPropagation();
        if(idx > 0){
          idx -= 1;
          navigating = true;
          setVal(items[idx].getAttribute('data-cmd') + ' ');
          navigating = false;
        } else {
          idx = -1;
          navigating = true;
          setVal(originalQuery);   /* restore what the user typed */
          navigating = false;
        }
        renderPal(originalQuery);

      } else if(e.key === 'Tab'){
        e.preventDefault(); e.stopPropagation();
        var target = idx >= 0 ? items[idx] : items[0];
        if(target) confirmVal(target.getAttribute('data-cmd') + ' ');

      } else if(e.key === 'Enter'){
        /* only intercept Enter if the user has navigated to an item;
           otherwise let Streamlit submit the form as usual */
        if(idx >= 0 && items[idx]){
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          confirmVal(items[idx].getAttribute('data-cmd') + ' ');
        }

      } else if(e.key === 'Escape'){
        e.preventDefault();
        navigating = true;
        setVal(originalQuery);     /* restore original typed text */
        navigating = false;
        hide();
      }
    });

    el.addEventListener('blur', function(){ setTimeout(hide, 200); });
  }

  /* ── click intro example chips ── */
  function attachChipClicks(){
    doc.querySelectorAll('.crake-example-chip').forEach(function(chip){
      if(chip.dataset.crakeClick) return;
      chip.dataset.crakeClick = '1';
      chip.style.cursor = 'pointer';
      chip.addEventListener('click', function(){
        if(!ta) return;
        var codeEl = chip.querySelector('code');
        if(codeEl){
          confirmVal(codeEl.textContent.trim());
          ta.focus();
        }
      });
    });
  }

  /* ── find & attach ── */
  function findAndAttach(){
    var el = doc.querySelector('[data-testid="stChatInput"] textarea');
    if(el){ attachTo(el); }
    else { setTimeout(findAndAttach, 300); }
    attachChipClicks();
  }

  findAndAttach();

  var obs = new MutationObserver(function(){
    var el = doc.querySelector('[data-testid="stChatInput"] textarea');
    if(el && el !== ta){ ta = null; attachTo(el); }
    attachChipClicks();
  });
  obs.observe(doc.body, {childList:true, subtree:true});

  /* ── fit the chat messages container to fill available column height ── */
  function fitContainers(){
    try {
      var hBlocks = doc.querySelectorAll('[data-testid="stHorizontalBlock"]');
      var chatCol = null;
      for (var i = 0; i < hBlocks.length; i++) {
        /* handle both "column" (older Streamlit) and "stColumn" (newer) */
        var cols = hBlocks[i].querySelectorAll(
          ':scope > [data-testid="column"], :scope > [data-testid="stColumn"]'
        );
        if (cols.length === 2) { chatCol = cols[0]; break; }
      }
      if (!chatCol) return;

      var msgBox = chatCol.querySelector('[data-testid="stVerticalBlockBorderWrapper"]');
      var formEl = chatCol.querySelector('[data-testid="stForm"]');
      if (!msgBox || !formEl) return;

      var msgTop = msgBox.getBoundingClientRect().top;
      /* use the form element's own height — no wrapper traversal that can return null */
      var formH  = formEl.getBoundingClientRect().height;
      var viewH  = window.parent.innerHeight;
      var newH   = Math.floor(viewH - msgTop - formH - 16);

      if (newH > 200) {
        msgBox.style.height    = newH + 'px';
        msgBox.style.maxHeight = 'none';
      }
    } catch(e) { /* layout not ready — next timeout will retry */ }
  }
  fitContainers();
  window.parent.addEventListener('resize', fitContainers);
  setTimeout(fitContainers, 400);
  setTimeout(fitContainers, 1200);
  setTimeout(fitContainers, 3000);

  /* inject dark background into seqviz iframes — keep hover/tooltip styles untouched */
  var SEQVIZ_CSS =
    'body, #root { background: #070D15 !important; }' +
    /* tooltip popup — make it readable on dark */
    '[class*="tooltip"], [class*="Tooltip"], [class*="popup"], [class*="Popup"] {' +
    '  background: #0D1825 !important; color: #C8E8F0 !important;' +
    '  border: 1px solid rgba(0,229,160,0.25) !important;' +
    '  border-radius: 6px !important; padding: 6px 10px !important;' +
    '  font-size: 12px !important; z-index: 9999 !important; }';

  function injectSeqvizDark(){
    doc.querySelectorAll('iframe').forEach(function(frame){
      try {
        var fdoc = frame.contentDocument || frame.contentWindow.document;
        if(!fdoc || fdoc.querySelector('#crake-seqviz-dark')) return;
        var style = fdoc.createElement('style');
        style.id = 'crake-seqviz-dark';
        style.textContent = SEQVIZ_CSS;
        (fdoc.head || fdoc.documentElement).appendChild(style);
      } catch(e) {}
    });
  }

  /* run after initial render and watch for new iframes */
  setTimeout(injectSeqvizDark, 1200);
  setTimeout(injectSeqvizDark, 3000);
  var seqvizObs = new MutationObserver(function(){ injectSeqvizDark(); });
  seqvizObs.observe(doc.body, {childList:true, subtree:true});
})();
</script>
</body></html>
"""


def inject_command_palette() -> None:
    """Inject the slash-command autocomplete palette via a 0-height component iframe."""
    import streamlit.components.v1 as components
    components.html(_PALETTE_SCRIPT, height=0, scrolling=False)
