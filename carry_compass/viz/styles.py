import streamlit as st

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&display=swap');

:root {
    --bg-main: #0a0a0a;
    --bg-panel: #141414;
    --bg-panel-alt: #111111;
    --border: #2a2a2a;
    --text-primary: #e8e8e8;
    --text-secondary: #888888;
    --grid: #1f1f1f;
    --positive: #22c55e;
    --negative: #ef4444;
    --warning: #d99521;
    --mono: "IBM Plex Mono", monospace;
    --sans: "IBM Plex Mono", monospace;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background: var(--bg-main);
    color: var(--text-primary);
    font-family: var(--sans);
    font-weight: 400;
}

body, p, div, span, label, input {
    font-family: var(--sans);
    font-weight: 400;
}

[data-testid="stHeader"] {
    display: none;
}

[data-testid="stSidebar"] {
    background: var(--bg-main);
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: var(--text-primary);
}

.block-container {
    padding-top: 1.5rem;
    padding-left: 1.35rem;
    padding-right: 1.35rem;
    max-width: 100%;
}

#MainMenu, footer {
    visibility: hidden;
}

h1, h2, h3, p {
    color: var(--text-primary);
}

h1, h2, h3 {
    font-family: var(--mono);
    font-weight: 600;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.85rem;
}

button[kind="secondary"], button[kind="primary"] {
    background: transparent;
    border: 1px solid var(--text-primary);
    color: var(--text-primary);
    border-radius: 4px;
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

button[kind="secondary"]:hover, button[kind="primary"]:hover {
    background: var(--grid);
    border-color: var(--text-primary);
    color: var(--text-primary);
}

hr {
    border-color: var(--border);
}

.crc-topbar {
    position: sticky;
    top: 0;
    z-index: 999;
    display: grid;
    grid-template-columns: minmax(220px, 1fr) auto minmax(220px, 1fr);
    align-items: center;
    min-height: 60px;
    margin: -1.5rem -1.35rem 1rem -1.35rem;
    padding: 0 1.35rem;
    background: rgba(10, 10, 10, 0.96);
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(10px);
}

.crc-brand {
    font-family: var(--mono);
    font-size: 22px;
    font-weight: 600;
    letter-spacing: 0.06em;
    color: var(--text-primary);
    white-space: nowrap;
}

.crc-clock {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-secondary);
    text-align: center;
}

.crc-status {
    justify-self: end;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: var(--mono);
    font-size: 12px;
    letter-spacing: 0.08em;
    color: var(--text-primary);
}

.crc-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 0 3px rgba(255,255,255,0.04);
}

.crc-page-caption {
    color: var(--text-secondary);
    font-size: 12px;
    margin: -0.2rem 0 0.7rem 0;
}

.crc-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 0.15rem;
}

.crc-panel, .crc-kpi, .crc-section {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 6px;
}

.crc-kpi {
    min-height: 104px;
    padding: 16px;
}

.crc-label, .crc-section-title, .crc-table thead th {
    color: var(--text-secondary);
    font-family: var(--sans);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

.crc-value {
    margin-top: 9px;
    color: var(--text-primary);
    font-family: var(--mono);
    font-size: 29px;
    font-weight: 500;
    line-height: 1.05;
}

.crc-value-small {
    font-size: 18px;
    line-height: 1.25;
}

.crc-subvalue {
    margin-top: 8px;
    color: var(--text-secondary);
    font-size: 12px;
}

.crc-regime-value {
    display: flex;
    align-items: center;
    gap: 10px;
}

.crc-section {
    padding: 14px 14px 10px 14px;
}

.crc-section-title {
    margin-bottom: 10px;
}

.crc-ranking-wrap {
    max-height: 540px;
    overflow-y: auto;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg-main);
}

.crc-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--mono);
    font-weight: 500;
    font-size: 12px;
}

.crc-table thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: var(--bg-panel);
    border-bottom: 1px solid var(--border);
    padding: 9px 8px;
    text-align: left;
}

.crc-table tbody tr:nth-child(odd) {
    background: var(--bg-main);
}

.crc-table tbody tr:nth-child(even) {
    background: var(--bg-panel-alt);
}

.crc-table td {
    border-bottom: 1px solid rgba(42,42,42,0.72);
    color: var(--text-primary);
    padding: 8px;
    white-space: nowrap;
}

.crc-num, .crc-table th.crc-num {
    text-align: right;
}

.crc-class {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--text-secondary);
}

.crc-mini-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    display: inline-block;
}

.crc-ratio-cell {
    position: relative;
    min-width: 86px;
    text-align: right;
}

.crc-sparkbar {
    position: absolute;
    top: 50%;
    right: 6px;
    height: 18px;
    transform: translateY(-50%);
    border-radius: 2px;
    opacity: 0.26;
}

.crc-ratio-text {
    position: relative;
    z-index: 1;
}

.crc-pos {
    color: var(--positive) !important;
}

.crc-neg {
    color: var(--negative) !important;
}

.crc-method {
    color: #cfcfcf;
    font-size: 13px;
    line-height: 1.55;
}

.crc-sidebar-section {
    border-top: 1px solid var(--border);
    padding-top: 12px;
    margin-top: 12px;
}

.crc-sidebar-title {
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.crc-sidebar-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--text-secondary);
    font-size: 12px;
    padding: 4px 0;
}

.crc-sidebar-row strong {
    color: var(--text-primary);
    font-family: var(--mono);
    font-weight: 500;
}

.crc-universe-row {
    display: grid;
    grid-template-columns: 74px 1fr auto;
    gap: 7px;
    align-items: center;
    padding: 4px 0;
    color: var(--text-secondary);
    font-family: var(--mono);
    font-weight: 500;
    font-size: 11px;
}

.crc-universe-row span:last-child {
    color: var(--text-primary);
    text-align: right;
}

div[data-testid="stExpander"] {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 6px;
}

div[data-testid="stExpander"] details summary p {
    color: var(--text-primary);
    font-family: var(--mono);
    letter-spacing: 0.06em;
}

/* ---- headline call card ---- */

.crc-headline-card {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px 28px;
    margin-bottom: 0.6rem;
}

.crc-headline-regime-row {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 10px;
}

.crc-headline-label {
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.crc-headline-regime {
    font-family: var(--mono);
    font-size: 38px;
    font-weight: 600;
    line-height: 1.0;
}

.crc-headline-meaning {
    color: var(--text-secondary);
    font-size: 14px;
    line-height: 1.55;
    margin-bottom: 14px;
    max-width: 680px;
}

.crc-headline-rec-label {
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

.crc-headline-rec {
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 500;
    line-height: 1.45;
    margin-bottom: 18px;
}

.crc-headline-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 24px;
}

.crc-headline-meta-item {
    display: flex;
    flex-direction: column;
    gap: 3px;
}

.crc-headline-meta-label {
    color: var(--text-secondary);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
}

.crc-headline-meta-value {
    font-family: var(--mono);
    font-size: 17px;
    font-weight: 500;
    color: var(--text-primary);
}

.crc-conf-bar-wrap {
    width: 120px;
    height: 5px;
    background: var(--border);
    border-radius: 3px;
    overflow: hidden;
    margin-top: 5px;
}

.crc-conf-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: var(--positive);
}

/* ---- alert banner ---- */

.crc-alert-banner {
    display: flex;
    align-items: center;
    gap: 14px;
    background: rgba(217, 149, 33, 0.10);
    border: 1px solid rgba(217, 149, 33, 0.40);
    border-radius: 6px;
    padding: 12px 18px;
    margin-bottom: 0.6rem;
    font-size: 13px;
    line-height: 1.4;
}

.crc-alert-icon {
    font-size: 18px;
    flex-shrink: 0;
}

.crc-alert-text {
    color: var(--text-primary);
}

.crc-alert-from {
    color: var(--text-secondary);
    font-size: 12px;
    margin-top: 2px;
}

/* ---- how to read ---- */

.crc-how-to-read {
    color: #cfcfcf;
    font-size: 13px;
    line-height: 1.6;
}

.crc-how-to-read h4 {
    color: var(--text-primary);
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 14px 0 4px;
}

.crc-how-to-read p {
    margin: 0 0 8px;
}

/* ---- export button area ---- */

.crc-export-row {
    display: flex;
    justify-content: flex-end;
    margin-top: 4px;
}

@media (max-width: 900px) {
    .crc-topbar {
        grid-template-columns: 1fr;
        gap: 4px;
        padding: 10px 1rem;
    }
    .crc-clock {
        text-align: left;
    }
    .crc-status {
        justify-self: start;
    }
    .crc-kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .crc-headline-regime {
        font-size: 28px;
    }
    .crc-headline-meta {
        gap: 14px;
    }
}
</style>
"""


def inject_global_css() -> None:
    """Inject the global Streamlit CSS overrides for the dark dashboard."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
