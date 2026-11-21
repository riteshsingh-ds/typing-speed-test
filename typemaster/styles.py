"""Global CSS injected into the Streamlit page."""
from __future__ import annotations

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700;12..96,800&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {
  --ink: #0d1016; --panel: #141922; --panel-2: #1a202b; --line: #252c3a;
  --text: #e9e6de; --muted: #8089a0;
  --amber: #ffb454; --mint: #5ee3a1; --coral: #ff6b6b; --sky: #6bc7ff;
  --display: 'Bricolage Grotesque', 'Segoe UI', system-ui, sans-serif;
  --mono: 'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace;
}

html, body, [data-testid="stAppViewContainer"], .stApp {
  font-family: var(--display);
  background: radial-gradient(900px 380px at 10% -8%, rgba(255,180,84,0.10), transparent 60%), var(--ink);
  color: var(--text);
}
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stAppDeployButton"], [data-testid="stToolbar"] { visibility: hidden; height: 0; }
.block-container { max-width: 1560px; padding: 1.4rem 1.2rem 4rem; }
h1, h2, h3, h4 { font-family: var(--display); letter-spacing: -0.01em; }

/* ---- brand header ---- */
.tm-brand { display: flex; align-items: center; gap: 14px; padding: 4px 0 10px; }
.tm-logo {
  width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center;
  background: var(--amber); color: #1a1205; font-family: var(--mono); font-weight: 700; font-size: 17px;
  box-shadow: 0 3px 0 #b87a1f, 0 8px 18px rgba(255,180,84,0.22);
}
.tm-title { font-size: 1.75rem; font-weight: 800; line-height: 1.05; margin: 0; }
.tm-tagline { color: var(--muted); font-size: 0.95rem; margin-top: 2px; }

/* ---- cards ---- */
.tm-grid { display: grid; gap: 12px; margin: 6px 0 18px; }
.tm-grid.cols-2 { grid-template-columns: repeat(2, 1fr); }
.tm-grid.cols-3 { grid-template-columns: repeat(3, 1fr); }
.tm-grid.cols-4 { grid-template-columns: repeat(4, 1fr); }
.tm-card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; min-width: 0; }
.tm-card .tm-label { color: var(--muted); font-size: 0.82rem; font-weight: 500; }
.tm-card .tm-value { font-family: var(--mono); font-size: 1.85rem; font-weight: 700; line-height: 1.2; margin-top: 4px; font-variant-numeric: tabular-nums; }
.tm-card .tm-sub { color: var(--muted); font-size: 0.78rem; margin-top: 2px; }
.tm-card.amber .tm-value { color: var(--amber); }
.tm-card.mint .tm-value { color: var(--mint); }
.tm-card.coral .tm-value { color: var(--coral); }
.tm-card.sky .tm-value { color: var(--sky); }

.tm-section { display: flex; align-items: baseline; gap: 12px; margin: 20px 0 8px; }
.tm-section h3 { margin: 0; font-size: 1.15rem; font-weight: 700; }
.tm-hint { color: var(--muted); font-size: 0.85rem; }

.tm-badge { display: inline-block; padding: 4px 11px; border-radius: 999px; font-size: 0.8rem; font-weight: 600;
  background: var(--panel-2); border: 1px solid var(--line); color: var(--text); }
.tm-badge.good { background: rgba(94,227,161,0.12); border-color: rgba(94,227,161,0.4); color: var(--mint); }
.tm-badge.amber { background: rgba(255,180,84,0.12); border-color: rgba(255,180,84,0.4); color: var(--amber); }
.tm-chips { display: flex; gap: 8px; flex-wrap: wrap; margin: 2px 0 10px; }

/* ---- empty / error ---- */
.tm-empty, .tm-error { text-align: center; border: 1px dashed var(--line); border-radius: 16px; padding: 38px 20px; margin: 10px 0; background: rgba(255,255,255,0.015); }
.tm-error { border-color: rgba(255,107,107,0.5); background: rgba(255,107,107,0.06); }
.tm-empty-icon { font-size: 2rem; margin-bottom: 6px; }
.tm-empty-title { font-weight: 700; font-size: 1.1rem; }
.tm-empty-body { color: var(--muted); margin-top: 4px; font-size: 0.95rem; }

/* ---- result hero ---- */
.tm-result { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; flex-wrap: wrap;
  background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 22px 26px; margin-bottom: 14px; }
.tm-bigwpm { font-family: var(--mono); font-size: 5rem; font-weight: 700; line-height: 1; color: var(--amber); }
.tm-bigwpm small { font-size: 1.2rem; color: var(--muted); margin-left: 10px; font-weight: 500; }
.tm-tier { font-size: 1.3rem; font-weight: 700; margin-top: 6px; }
.tm-result-note { color: var(--muted); font-size: 0.92rem; text-align: right; max-width: 320px; }

/* ---- podium ---- */
.tm-podium { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 6px 0 16px; }
.tm-podium .tm-card { text-align: center; }
.tm-podium .tm-medal { font-size: 1.6rem; }
.tm-podium .tm-name { font-weight: 700; font-size: 1.05rem; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ---- streamlit widgets ---- */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); overflow-x: auto; }
.stTabs button[data-baseweb="tab"] { font-family: var(--display); font-weight: 600; padding: 10px 16px; color: var(--muted); }
.stTabs button[data-baseweb="tab"][aria-selected="true"] { color: var(--amber); }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--amber); }

.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 12px; font-family: var(--display); font-weight: 600; border: 1px solid var(--line);
  background: var(--panel-2); color: var(--text); padding: 0.55rem 1rem; transition: transform .08s ease, border-color .15s;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--amber); color: var(--amber); }
.stButton > button:active { transform: translateY(1px); }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"], [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
  background: var(--amber); color: #1a1205; border: 0; box-shadow: 0 3px 0 #b87a1f; font-weight: 700;
}
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover { color: #1a1205; filter: brightness(1.06); }

/* radio group styled as segmented pills */
[data-testid="stRadio"] [role="radiogroup"] { gap: 8px; flex-wrap: wrap; }
[data-testid="stRadio"] [role="radiogroup"] > label {
  background: var(--panel); border: 1px solid var(--line); border-radius: 999px; padding: 6px 18px; cursor: pointer; margin: 0;
}
[data-testid="stRadio"] [role="radiogroup"] > label > div:first-of-type:not([data-testid="stMarkdownContainer"]) { display: none; }
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) { background: rgba(255,180,84,0.14); border-color: var(--amber); }
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p { color: var(--amber); font-weight: 700; }

.stTextInput input, .stSelectbox [data-baseweb="select"] > div { border-radius: 12px; background: var(--panel); border-color: var(--line); }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: 14px; background: var(--panel); }
iframe { color-scheme: dark; }

/* ---- mobile ---- */
@media (max-width: 720px) {
  .block-container { padding: 0.8rem 0.7rem 3rem; }
  .tm-title { font-size: 1.4rem; }
  .tm-grid.cols-4, .tm-grid.cols-3 { grid-template-columns: repeat(2, 1fr); }
  .tm-card .tm-value { font-size: 1.5rem; }
  .tm-bigwpm { font-size: 3.6rem; }
  .tm-result { padding: 16px 18px; }
  .tm-result-note { text-align: left; max-width: none; }
  .tm-podium { grid-template-columns: 1fr; }
}
</style>
"""


def _inject_base() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

CSS_V2 = """
<style>
/* ---------- boot splash ---------- */
.tm-splash { position: fixed; inset: 0; z-index: 999999; display: grid; place-items: center;
  background: radial-gradient(700px 400px at 50% 35%, rgba(255,180,84,0.14), transparent 65%), #0d1016; }
.tm-splash-inner { text-align: center; width: min(420px, 86vw); animation: tmFade .5s ease both; }
.tm-logo.big { width: 76px; height: 76px; font-size: 28px; border-radius: 20px; margin: 0 auto 18px; animation: tmPop .7s cubic-bezier(.2,1.4,.4,1) both; }
.tm-splash-title { font-size: 2.3rem; font-weight: 800; letter-spacing: -0.02em; }
.tm-splash-tag { color: var(--muted); margin: 4px 0 26px; }
.tm-splash-bar { height: 4px; border-radius: 99px; background: rgba(255,255,255,0.08); overflow: hidden; }
.tm-splash-bar i { display: block; height: 100%; width: 0; background: var(--amber); border-radius: 99px; animation: tmLoad var(--splash, 3s) cubic-bezier(.4,.1,.2,1) forwards; }
.tm-splash-steps { position: relative; height: 22px; margin-top: 14px; color: var(--muted); font-size: 0.9rem; }
.tm-splash-steps span { position: absolute; inset: 0; opacity: 0; animation: tmStep var(--step, 1s) ease both; }
.tm-splash-steps span:nth-child(2) { animation-delay: var(--step, 1s); }
.tm-splash-steps span:nth-child(3) { animation-delay: calc(var(--step, 1s) * 2); }
.tm-splash-by { position: absolute; bottom: 28px; left: 0; right: 0; text-align: center; color: var(--muted); font-size: 0.85rem; }
.tm-splash-by b { color: var(--text); font-weight: 600; }
@keyframes tmLoad { to { width: 100%; } }
@keyframes tmStep { 0% { opacity: 0; transform: translateY(6px); } 18%, 82% { opacity: 1; transform: none; } 100% { opacity: 0; } }
@keyframes tmFade { from { opacity: 0; transform: translateY(8px); } }
@keyframes tmPop { from { opacity: 0; transform: scale(.7); } }

/* ---------- navigation ---------- */
.st-key-nav { position: sticky; top: 0; z-index: 50; background: rgba(13,16,22,0.88); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line); margin: 0 -1.2rem 12px; padding: 8px 1.2rem; }
.st-key-nav [role="radiogroup"] { gap: 4px !important; flex-wrap: nowrap !important; overflow-x: auto; scrollbar-width: none; }
.st-key-nav [role="radiogroup"] > label { border: 0 !important; background: transparent !important; padding: 7px 14px !important; white-space: nowrap; }
.st-key-nav [role="radiogroup"] > label p { color: var(--muted); font-weight: 600; font-size: 0.95rem; }
.st-key-nav [role="radiogroup"] > label:hover p { color: var(--text); }
.st-key-nav [role="radiogroup"] > label:has(input:checked) { background: rgba(255,180,84,0.13) !important; }
.st-key-nav [role="radiogroup"] > label:has(input:checked) p { color: var(--amber); }

/* ---------- hero ---------- */
.tm-hero { display: grid; grid-template-columns: 1.35fr 1fr; gap: 22px; align-items: stretch; margin: 6px 0 14px; }
.tm-hero-main { padding: 34px 34px 28px; border-radius: 22px; border: 1px solid var(--line);
  background: radial-gradient(500px 240px at 0% 0%, rgba(255,180,84,0.10), transparent 70%), var(--panel); }
.tm-eyebrow { color: var(--amber); font-weight: 600; font-size: 0.92rem; margin-bottom: 10px; }
.tm-hero h1 { font-size: clamp(2rem, 4.6vw, 3.3rem); line-height: 1.04; margin: 0 0 14px; font-weight: 800; letter-spacing: -0.03em; }
.tm-hero h1 em { font-style: normal; color: var(--amber); }
.tm-hero p { color: #b7b4ab; font-size: 1.05rem; line-height: 1.55; margin: 0; max-width: 46ch; }
.tm-demo { margin-top: 22px; padding: 14px 16px; border-radius: 14px; background: var(--ink); border: 1px solid var(--line);
  font-family: var(--mono); font-size: 0.95rem; color: var(--muted); }
.tm-demo .ok { color: var(--mint); } .tm-demo .bad { color: var(--coral); background: rgba(255,107,107,0.16); border-radius: 3px; }
.tm-demo .caret { display: inline-block; width: 2px; height: 1.05em; background: var(--amber); vertical-align: -2px; animation: tmBlink 1s steps(1) infinite; }
@keyframes tmBlink { 50% { opacity: 0; } }
.tm-hero-side { padding: 24px; border-radius: 22px; border: 1px solid var(--line); background: var(--panel); display: flex; flex-direction: column; gap: 10px; }
.tm-hero-side h4 { margin: 0; font-size: 1.05rem; }
.tm-mini { display: flex; justify-content: space-between; align-items: baseline; padding: 9px 0; border-bottom: 1px solid var(--line); }
.tm-mini:last-child { border-bottom: 0; }
.tm-mini b { font-family: var(--mono); color: var(--amber); }

.tm-features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 8px 0 18px; }
.tm-feature { padding: 20px; border-radius: 16px; background: var(--panel); border: 1px solid var(--line); transition: border-color .15s, transform .15s; }
.tm-feature:hover { border-color: rgba(255,180,84,0.55); transform: translateY(-2px); }
.tm-feature .tag { display: inline-block; font-size: 0.74rem; font-weight: 700; color: #1a1205; background: var(--amber); border-radius: 6px; padding: 2px 8px; margin-bottom: 10px; }
.tm-feature h4 { margin: 0 0 6px; font-size: 1.05rem; }
.tm-feature p { margin: 0; color: var(--muted); font-size: 0.92rem; line-height: 1.5; }
.tm-steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 8px 0 18px; }
.tm-step { padding: 18px 20px; border-radius: 16px; border: 1px dashed var(--line); }
.tm-step .n { font-family: var(--mono); color: var(--amber); font-weight: 700; }
.tm-step h4 { margin: 4px 0; } .tm-step p { margin: 0; color: var(--muted); font-size: 0.92rem; }
.tm-footer { margin-top: 36px; padding: 22px 0 6px; border-top: 1px solid var(--line); display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; color: var(--muted); font-size: 0.9rem; }
.tm-footer b { color: var(--text); }

.tm-page-head h2 { margin: 6px 0 2px; font-size: 1.7rem; font-weight: 800; }
.tm-page-sub { margin: 0 0 14px; color: var(--muted); }

/* ---------- progress / xp / badges ---------- */
.tm-level { display: flex; gap: 18px; align-items: center; padding: 20px 22px; border-radius: 18px; background: var(--panel); border: 1px solid var(--line); margin-bottom: 14px; }
.tm-level-badge { min-width: 70px; height: 70px; border-radius: 18px; display: grid; place-items: center; font-family: var(--mono); font-size: 1.9rem; font-weight: 700; color: #1a1205; background: var(--amber); box-shadow: 0 3px 0 #b87a1f; }
.tm-level-body { flex: 1; min-width: 0; }
.tm-level-title { font-weight: 800; font-size: 1.25rem; }
.tm-xpbar { height: 8px; background: rgba(255,255,255,0.08); border-radius: 99px; overflow: hidden; margin: 8px 0 4px; }
.tm-xpbar i { display: block; height: 100%; background: var(--amber); border-radius: 99px; }
.tm-badges { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 6px 0 16px; }
.tm-ach { padding: 14px 16px; border-radius: 14px; border: 1px solid var(--line); background: var(--panel); }
.tm-ach.off { opacity: .45; }
.tm-ach.on { border-color: rgba(94,227,161,0.5); }
.tm-ach b { display: block; } .tm-ach span { color: var(--muted); font-size: 0.85rem; }
.tm-ach .state { float: right; font-size: 0.72rem; font-weight: 700; color: var(--mint); }
.tm-ach.off .state { color: var(--muted); }

/* ---------- key doctor keyboard ---------- */
.tm-keyboard { --key: 52px; padding: 18px; border-radius: 18px; background: var(--panel); border: 1px solid var(--line); overflow-x: auto; margin: 6px 0 14px; }
.tm-key-row { display: flex; gap: 6px; margin-bottom: 6px; width: max-content; }
.tm-key { width: calc(var(--key) - 6px); height: calc(var(--key) - 6px); display: grid; place-items: center; border-radius: 10px;
  background: var(--panel-2); border: 1px solid var(--line); box-shadow: 0 3px 0 rgba(0,0,0,0.35); font-family: var(--mono); font-size: 0.85rem; font-weight: 700; cursor: default; }
.tm-key.space { width: calc(var(--key) * 5); }
.tm-legend { display: flex; gap: 14px; align-items: center; color: var(--muted); font-size: 0.82rem; margin: 0 4px 10px; }
.tm-legend i { display: inline-block; width: 60px; height: 8px; border-radius: 99px; background: linear-gradient(90deg, rgba(94,227,161,.6), rgba(255,107,107,.8)); }

/* ---------- side rails ---------- */
.tm-rcard { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px; margin-bottom: 12px; }
.tm-rcard.founder { border-color: rgba(255,180,84,0.45); background: linear-gradient(180deg, rgba(255,180,84,0.07), var(--panel)); }
.tm-rtitle { color: var(--muted); font-size: 0.82rem; font-weight: 600; margin-bottom: 8px; }
.tm-rname { font-weight: 700; font-size: 1.02rem; overflow-wrap: anywhere; }
.tm-rsub { color: var(--muted); font-size: 0.84rem; margin-top: 3px; }
.tm-rbig { font-family: var(--mono); font-size: 1.9rem; font-weight: 700; color: var(--amber); line-height: 1.2; }
.tm-rbig small { font-size: 0.85rem; color: var(--muted); font-weight: 500; }
.tm-ravatar { width: 54px; height: 54px; border-radius: 16px; background: var(--amber); color: #1a1205; display: grid; place-items: center; font-weight: 800; font-size: 1.5rem; margin-bottom: 10px; box-shadow: 0 3px 0 #b87a1f; }
.tm-rrow { display: flex; justify-content: space-between; gap: 8px; padding: 7px 0; border-bottom: 1px solid var(--line); font-size: 0.92rem; }
.tm-rrow:last-child { border-bottom: 0; } .tm-rrow b { font-family: var(--mono); color: var(--amber); }
.st-key-rail_left, .st-key-rail_right { position: sticky; top: 74px; }

/* ---------- rewards ---------- */
.tm-feature-card { display: grid; grid-template-columns: 1.3fr 1fr; gap: 18px; align-items: center; padding: 22px 26px; border-radius: 20px; margin: 4px 0 10px;
  border: 1px solid rgba(255,180,84,0.5); background: radial-gradient(400px 200px at 0% 0%, rgba(255,180,84,0.14), transparent 70%), var(--panel); }
.tm-feature-card h3 { margin: 2px 0 6px; font-size: 1.6rem; font-weight: 800; }
.tm-feature-card p { margin: 0; color: #b7b4ab; line-height: 1.5; }
.tm-days { display: flex; gap: 8px; flex-wrap: wrap; }
.tm-day { width: 46px; height: 46px; border-radius: 12px; display: grid; place-items: center; font-family: var(--mono); font-weight: 700;
  background: var(--panel-2); border: 1px solid var(--line); color: var(--muted); }
.tm-day.on { background: var(--amber); color: #1a1205; border-color: var(--amber); box-shadow: 0 3px 0 #b87a1f; }
.tm-cert { padding: 16px 18px; border-radius: 14px; border: 1px solid var(--line); background: var(--panel); margin-bottom: 8px; }
.tm-cert.on { border-color: rgba(94,227,161,0.5); } .tm-cert.off { opacity: .5; }
.tm-cert b { display: block; font-size: 1.05rem; } .tm-cert .what { display: block; color: var(--muted); font-size: 0.88rem; margin-top: 2px; }
.tm-cert .code { display: block; color: var(--muted); font-family: var(--mono); font-size: 0.74rem; margin-top: 8px; overflow-wrap: anywhere; }
.tm-cert .state { float: right; font-size: 0.72rem; font-weight: 700; color: var(--mint); } .tm-cert.off .state { color: var(--muted); }
.tm-ach.tier-bronze.on { border-color: rgba(205,127,50,0.7); } .tm-ach.tier-silver.on { border-color: rgba(190,202,216,0.7); }
.tm-ach.tier-gold.on { border-color: rgba(242,193,78,0.75); } .tm-ach.tier-platinum.on { border-color: rgba(130,214,245,0.8); }
.tm-ach.on .state { color: var(--text); }

.tm-gain { display: flex; gap: 8px; flex-wrap: wrap; margin: 0 0 14px; }

@media (max-width: 1180px) {
  [data-testid="stColumn"]:has(.st-key-rail_left), [data-testid="stColumn"]:has(.st-key-rail_right) { display: none; }
}
@media (max-width: 860px) {
  .tm-feature-card { grid-template-columns: 1fr; }
  .tm-hero { grid-template-columns: 1fr; }
  .tm-features, .tm-steps, .tm-badges { grid-template-columns: 1fr 1fr; }
  .tm-hero-main { padding: 24px 20px; }
}
@media (max-width: 560px) {
  .tm-features, .tm-steps, .tm-badges { grid-template-columns: 1fr; }
  .st-key-nav { margin: 0 -0.7rem 10px; padding: 6px 0.7rem; }
  .tm-keyboard { --key: 40px; }
  .tm-level { flex-direction: column; align-items: flex-start; }
}
@media (prefers-reduced-motion: reduce) { .tm-splash-bar i, .tm-splash-steps span, .tm-logo.big { animation-duration: .01s; } }
</style>
"""


def inject_css() -> None:
    _inject_base()
    st.markdown(CSS_V2, unsafe_allow_html=True)
