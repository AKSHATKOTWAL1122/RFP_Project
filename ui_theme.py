"""Visual layer for the Streamlit UI — CSS injection and a few HTML renderers.

Design direction: an *evaluation dossier*. The tool exists to produce a defensible,
explainable supplier ranking, so the interface is built like an assessor's
worksheet — hairline rules, a strict type scale, monospaced figures for anything
the arithmetic produced, and one signature device: the leaderboard's
"distance-from-the-frontier" bar, where 100 is the peer benchmark every criterion
is measured against.

Nothing here computes anything. It only formats values already produced upstream.
"""
from __future__ import annotations

import html

# --------------------------------------------------------------------------- #
# Tokens — the whole palette, named. Keep every colour decision here.
# --------------------------------------------------------------------------- #
INK = "#16202B"        # primary text, dark surfaces
PAPER = "#F7F6F2"      # app background (low-chroma, not the cream trend)
SURFACE = "#FFFFFF"    # cards, tables
RULE = "#DAD6CB"       # hairlines
SLATE = "#5B6673"      # secondary text
SIGNAL = "#1D6A6A"     # interface accent — actions, the measured bar
PAR = "#C99A2E"        # the benchmark frontier marker — used nowhere else
CRIT = "#9B2C2C"       # failure / exclusion

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {{
  --ink:{INK}; --paper:{PAPER}; --surface:{SURFACE}; --rule:{RULE};
  --slate:{SLATE}; --signal:{SIGNAL}; --par:{PAR}; --crit:{CRIT};
}}

/* ---- base ------------------------------------------------------------- */
.stApp {{ background:var(--paper); }}
html, body, .stApp, [class*="css"] {{
  font-family:'Inter', system-ui, -apple-system, sans-serif;
  color:var(--ink);
}}
.block-container {{ padding-top:2.4rem; max-width:1180px; }}

/* ---- headings ------------------------------------------------------- */
h1, h2, h3, h4 {{
  font-family:'Space Grotesk', sans-serif;
  letter-spacing:-0.015em; color:var(--ink);
}}
h1 {{ font-weight:700; }}
h2 {{ font-weight:600; font-size:1.28rem; margin-top:2.2rem; }}
h3 {{ font-weight:600; font-size:1.05rem; }}

/* ---- screen header device ----------------------------------------- */
.dossier-head {{ margin:0 0 1.6rem; }}
.dossier-eyebrow {{
  font-family:'IBM Plex Mono', monospace;
  font-size:0.72rem; font-weight:500; letter-spacing:0.18em;
  text-transform:uppercase; color:var(--signal);
  display:flex; align-items:center; gap:0.6rem;
}}
.dossier-eyebrow::after {{
  content:""; flex:1; height:1px; background:var(--rule);
}}
.dossier-title {{
  font-family:'Space Grotesk', sans-serif; font-weight:700;
  font-size:2rem; line-height:1.1; margin:0.5rem 0 0.35rem;
  letter-spacing:-0.02em;
}}
.dossier-purpose {{ color:var(--slate); font-size:0.95rem; max-width:60ch; }}

/* ---- sidebar ------------------------------------------------------- */
section[data-testid="stSidebar"] {{
  background:var(--ink); border-right:1px solid #0d151d;
}}
section[data-testid="stSidebar"] * {{ color:#E9E7E0; }}
section[data-testid="stSidebar"] h1 {{
  font-size:0.82rem; font-weight:600; letter-spacing:0.16em;
  text-transform:uppercase; color:#8FB6B6 !important;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label {{
  padding:0.34rem 0; font-size:0.95rem;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ color:#fff; }}

/* ---- tables ------------------------------------------------------- */
[data-testid="stTable"] table, .stDataFrame {{
  font-family:'Inter', sans-serif; font-size:0.9rem;
}}
[data-testid="stTable"] thead th {{
  background:var(--ink) !important; color:#fff !important;
  font-family:'IBM Plex Mono', monospace; font-weight:500;
  font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase;
}}
[data-testid="stTable"] tbody td {{ border-color:var(--rule) !important; }}
[data-testid="stTable"] tbody tr:nth-child(even) {{ background:#FBFAF7; }}

/* ---- metrics ----------------------------------------------------- */
[data-testid="stMetric"] {{
  background:var(--surface); border:1px solid var(--rule);
  border-left:3px solid var(--signal);
  padding:0.85rem 1rem; border-radius:2px;
}}
[data-testid="stMetricLabel"] {{
  font-family:'IBM Plex Mono', monospace; font-size:0.68rem !important;
  letter-spacing:0.1em; text-transform:uppercase; color:var(--slate);
}}
[data-testid="stMetricValue"] {{
  font-family:'IBM Plex Mono', monospace; font-weight:600;
  font-size:1.5rem; color:var(--ink);
}}

/* ---- buttons --------------------------------------------------- */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {{
  font-family:'Space Grotesk', sans-serif; font-weight:600;
  border-radius:2px; border:1px solid var(--ink);
  letter-spacing:0.01em; transition:transform .04s ease;
}}
.stButton button:active {{ transform:translateY(1px); }}
.stButton button[kind="primary"], .stFormSubmitButton button {{
  background:var(--signal); border-color:var(--signal); color:#fff;
}}
.stButton button[kind="primary"]:hover {{ background:#175656; border-color:#175656; }}

/* ---- expanders / inputs -------------------------------------- */
[data-testid="stExpander"] {{ border:1px solid var(--rule); border-radius:2px; }}
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {{
  border-radius:2px !important;
}}
.stAlert {{ border-radius:2px; }}

/* ---- leaderboard signature --------------------------------- */
.lb-list {{ margin:0.4rem 0 1.2rem; }}
.lb-row {{
  display:grid; grid-template-columns:56px 1fr 300px;
  gap:1.1rem; align-items:center;
  padding:0.95rem 0.2rem; border-bottom:1px solid var(--rule);
}}
.lb-row:first-child {{ border-top:1px solid var(--rule); }}
.lb-rank {{
  font-family:'IBM Plex Mono', monospace; font-weight:600;
  font-size:1.9rem; color:var(--ink); text-align:right; line-height:1;
}}
.lb-lead .lb-rank {{ color:var(--par); }}
.lb-name {{
  font-family:'Space Grotesk', sans-serif; font-weight:600;
  font-size:1.05rem; line-height:1.2;
}}
.lb-meta {{
  font-family:'IBM Plex Mono', monospace; font-size:0.73rem;
  color:var(--slate); margin-top:0.2rem; letter-spacing:0.02em;
}}
.lb-bar-wrap {{ position:relative; }}
.lb-bar-track {{
  position:relative; height:10px; background:#EAE7DD;
  border:1px solid var(--rule); border-radius:1px; overflow:hidden;
}}
.lb-bar-fill {{ position:absolute; left:0; top:0; bottom:0; background:var(--signal); }}
.lb-bar-mark {{
  position:absolute; top:-3px; bottom:-3px; width:2px;
  background:var(--par); right:0;
}}
.lb-bar-label {{
  display:flex; justify-content:space-between; margin-top:0.35rem;
  font-family:'IBM Plex Mono', monospace; font-size:0.72rem; color:var(--slate);
}}
.lb-bar-label b {{ color:var(--ink); font-weight:600; }}

@media (max-width:720px) {{
  .lb-row {{ grid-template-columns:44px 1fr; }}
  .lb-bar-wrap {{ grid-column:1 / -1; }}
}}
@media (prefers-reduced-motion:reduce) {{
  * {{ transition:none !important; }}
}}
</style>
"""


def inject(st) -> None:
    """Apply the global stylesheet. Call once, right after set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


def screen_header(st, *, step: str, kicker: str, title: str, purpose: str) -> None:
    """The dossier header device.

    `step` names the brief's real pipeline step(s) this screen covers — the
    numbering carries information (where you are in the assessment), it isn't
    decoration.
    """
    st.markdown(
        f'<div class="dossier-head">'
        f'<div class="dossier-eyebrow">{html.escape(step)} &nbsp;·&nbsp; {html.escape(kicker)}</div>'
        f'<div class="dossier-title">{html.escape(title)}</div>'
        f'<div class="dossier-purpose">{html.escape(purpose)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def leaderboard(st, ranked: list) -> None:
    """Render the ranked suppliers as the signature 'distance-from-frontier' list.

    The bar fills to each supplier's PPI; the ochre tick at the right edge is the
    peer benchmark (PPI 100) — the frontier the top supplier sets on the
    criteria mix. Everyone else reads as their distance back from it.
    """
    # Streamlit's markdown parser turns any indented HTML line into a code block,
    # so every row must be emitted as one unbroken line.
    rows = []
    for i, r in enumerate(ranked):
        ppi = r["ppi"] or 0.0
        pct = max(0.0, min(100.0, ppi))
        absc = r["absolute_score"]
        absc_s = f"{absc:.1f}" if absc is not None else "—"
        exp = r["experience_rating"]
        exp_s = f"{exp:g}" if exp is not None else "—"
        lead = " lb-lead" if i == 0 else ""
        name = html.escape(str(r["supplier_name"]))
        sub = html.escape(str(r["submission_date"]))
        rows.append(
            f'<div class="lb-row{lead}">'
            f'<div class="lb-rank">{r["final_rank"]}</div>'
            f'<div><div class="lb-name">{name}</div>'
            f'<div class="lb-meta">SUBMITTED {sub} &nbsp;·&nbsp; '
            f'EXP {exp_s}/5 &nbsp;·&nbsp; ABS {absc_s}</div></div>'
            f'<div class="lb-bar-wrap"><div class="lb-bar-track">'
            f'<div class="lb-bar-fill" style="width:{pct:.1f}%"></div>'
            f'<div class="lb-bar-mark"></div></div>'
            f'<div class="lb-bar-label"><span>PPI</span><b>{ppi:.1f}</b>'
            f'<span>frontier 100</span></div></div>'
            f"</div>"
        )
    st.markdown(f'<div class="lb-list">{"".join(rows)}</div>', unsafe_allow_html=True)
