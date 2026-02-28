from __future__ import annotations

import streamlit as st
import pandas as pd
import shutil
import os
from datetime import datetime, date, timedelta
import database as db
import report_parser
import doc_generator
import coc_parser
import entitlements

ACTIVE_CASES_DIR = os.path.join(os.path.dirname(__file__), "..", "Active Cases")

# Site list — will be replaced with user-provided names
SITE_LIST = ["-- Select --", "Other"]

st.set_page_config(
    page_title="ClaimTrack Pro",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Professional CSS Styling ---
st.markdown("""
<style>
    /* Hide Streamlit branding only — keep header for sidebar toggle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Top nav bar — single connected strip with dropdowns */
    .topnav-bar {
        display: flex;
        align-items: stretch;
        background: #F4F6F9;
        border-bottom: 1px solid #DEE2E6;
        padding: 0;
        margin: -1rem -1rem 0.75rem -1rem;
        overflow: visible;
        white-space: nowrap;
        gap: 0;
        position: relative;
        z-index: 999;
    }
    .topnav-bar > a {
        display: inline-flex;
        align-items: center;
        padding: 8px 14px;
        font-size: 0.8rem;
        font-weight: 500;
        color: #4A5568;
        text-decoration: none;
        border-right: 1px solid #DEE2E6;
        transition: background 0.15s;
    }
    .topnav-bar > a:hover { background: #E2E8F0; color: #1E3A5F; }
    .topnav-bar > a.active { background: #1E3A5F; color: #FFFFFF; font-weight: 600; }
    .topnav-bar > a.disabled { color: #B0B8C4; pointer-events: none; }
    .topnav-bar > a.new-btn { background: #27AE60; color: #FFFFFF; font-weight: 600; }
    .topnav-bar > a.new-btn:hover { background: #219A52; }

    /* Dropdown container */
    .nav-dropdown {
        position: relative;
        display: inline-flex;
        align-items: stretch;
        border-right: 1px solid #DEE2E6;
    }
    .nav-dropdown > .nav-drop-label {
        display: inline-flex;
        align-items: center;
        padding: 8px 14px;
        font-size: 0.8rem;
        font-weight: 500;
        color: #4A5568;
        text-decoration: none;
        cursor: pointer;
        transition: background 0.15s;
        gap: 4px;
    }
    .nav-dropdown > .nav-drop-label:hover { background: #E2E8F0; color: #1E3A5F; }
    .nav-dropdown > .nav-drop-label.has-active { background: #1E3A5F; color: #FFFFFF; font-weight: 600; }
    .nav-drop-arrow { font-size: 0.6rem; margin-left: 2px; }

    /* Dropdown menu */
    .nav-dropdown-menu {
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        background: #FFFFFF;
        border: 1px solid #DEE2E6;
        border-top: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        min-width: 180px;
        z-index: 1000;
    }
    .nav-dropdown:hover .nav-dropdown-menu { display: block; }
    .nav-dropdown-menu a {
        display: block;
        padding: 8px 16px;
        font-size: 0.8rem;
        font-weight: 500;
        color: #4A5568;
        text-decoration: none;
        transition: background 0.15s;
        border-bottom: 1px solid #F0F0F0;
    }
    .nav-dropdown-menu a:last-child { border-bottom: none; }
    .nav-dropdown-menu a:hover { background: #E2E8F0; color: #1E3A5F; }
    .nav-dropdown-menu a.active { background: #1E3A5F; color: #FFFFFF; font-weight: 600; }

    /* Root variables */
    :root {
        --primary: #1E3A5F;
        --primary-light: #2C5F8A;
        --accent: #4A90D9;
        --success: #27AE60;
        --warning: #F39C12;
        --danger: #E74C3C;
        --bg-light: #F8F9FA;
        --border: #E0E4E8;
        --text-primary: #2C3E50;
        --text-secondary: #6C757D;
    }

    /* Sidebar styling — light neutral for readability */
    [data-testid="stSidebar"] {
        background: #F4F6F9;
        border-right: 1px solid #DEE2E6;
    }
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] .stCaption {
        color: #2C3E50 !important;
    }
    [data-testid="stSidebar"] .stRadio label span {
        color: #4A5568 !important;
    }
    [data-testid="stSidebar"] .stRadio label[data-checked="true"] span {
        color: var(--primary) !important;
        font-weight: 600;
    }

    /* Main content area — compact */
    .main .block-container {
        padding-top: 1rem;
        max-width: 1200px;
    }
    .main .block-container p,
    .main .block-container li,
    .main .block-container span {
        font-size: 0.875rem;
    }

    /* Reduce vertical spacing globally */
    .main [data-testid="stVerticalBlock"] > div {
        margin-bottom: 0 !important;
        padding-top: 0.15rem !important;
        padding-bottom: 0.15rem !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 8px 12px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    [data-testid="stMetric"] label {
        color: var(--text-secondary) !important;
        font-size: 0.7rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-weight: 600;
        font-size: 1rem !important;
        white-space: normal !important;
        word-break: break-word !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {
        font-size: 0.7rem !important;
    }

    /* Tabs styling — compact */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background: var(--bg-light);
        border-radius: 6px;
        padding: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 500;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: var(--primary) !important;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }

    /* Bordered containers */
    [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 6px;
        border-color: var(--border) !important;
    }

    /* Buttons — compact */
    .stButton > button {
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.85rem !important;
        padding: 4px 12px !important;
        min-height: 0 !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--primary) !important;
        border-color: var(--primary) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--primary-light) !important;
        border-color: var(--primary-light) !important;
    }

    /* Case card buttons (full-width clickable rows) */
    .stButton > button[data-testid="stBaseButton-secondary"] {
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 10px 14px !important;
        border: 1px solid var(--border) !important;
        background: #FFFFFF !important;
        color: var(--text-primary) !important;
        border-radius: 6px !important;
        cursor: pointer !important;
        min-height: 0 !important;
        line-height: 1.4 !important;
        font-size: 0.85rem !important;
    }
    .stButton > button[data-testid="stBaseButton-secondary"]:hover {
        border-color: var(--accent) !important;
        box-shadow: 0 2px 6px rgba(74,144,217,0.12) !important;
        background: #F5F8FF !important;
    }

    /* DataFrames */
    [data-testid="stDataFrame"] {
        border-radius: 6px;
        overflow: hidden;
    }

    /* Progress bars */
    .stProgress > div > div {
        background-color: var(--accent) !important;
    }

    /* Dividers — tighter */
    hr {
        border-color: var(--border) !important;
        margin: 0.5rem 0 !important;
    }

    /* Compact headings */
    h1 { font-size: 1.5rem !important; margin-bottom: 0.3rem !important; }
    h2 { font-size: 1.15rem !important; margin-bottom: 0.2rem !important; }
    h3 { font-size: 1rem !important; margin-bottom: 0.1rem !important; }
    h4 { font-size: 0.9rem !important; margin-bottom: 0.1rem !important; }

    /* Compact form inputs */
    [data-testid="stForm"] {
        border-radius: 6px;
        border-color: var(--border);
        padding: 1.2rem;
    }

    /* Title styling */
    h1 {
        color: var(--primary) !important;
        font-weight: 700 !important;
    }
    h2, h3 {
        color: var(--text-primary) !important;
    }

    /* ── Landing Page Styles ───────────────────────────────────── */

    /* Animations */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-40px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(40px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    @keyframes progressFill {
        from { width: 0%; }
        to { width: 100%; }
    }
    @keyframes countPulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; transform: scale(1.02); }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-6px); }
    }
    @keyframes shimmer {
        0% { background-position: -200% center; }
        100% { background-position: 200% center; }
    }
    @keyframes typewriter {
        from { width: 0; }
        to { width: 100%; }
    }
    @keyframes blink {
        50% { border-color: transparent; }
    }
    @keyframes docAppear1 { 0%,30% { opacity:0; transform:scale(0.5);} 40%,100% { opacity:1; transform:scale(1);} }
    @keyframes docAppear2 { 0%,50% { opacity:0; transform:scale(0.5);} 60%,100% { opacity:1; transform:scale(1);} }
    @keyframes docAppear3 { 0%,70% { opacity:0; transform:scale(0.5);} 80%,100% { opacity:1; transform:scale(1);} }
    @keyframes checkAppear1 { 0%,40% { opacity:0; } 50%,100% { opacity:1; } }
    @keyframes checkAppear2 { 0%,55% { opacity:0; } 65%,100% { opacity:1; } }
    @keyframes checkAppear3 { 0%,70% { opacity:0; } 80%,100% { opacity:1; } }
    @keyframes checkAppear4 { 0%,85% { opacity:0; } 95%,100% { opacity:1; } }

    /* Hero */
    .landing-hero {
        background: linear-gradient(135deg, #1E3A5F 0%, #2C5F8A 50%, #1E3A5F 100%);
        color: #FFFFFF;
        padding: 3rem 2rem;
        margin: -1rem -1rem 0 -1rem;
        text-align: center;
        animation: fadeInUp 0.8s ease-out;
    }
    .landing-hero h1 {
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        margin-bottom: 0.8rem !important;
        letter-spacing: -0.5px;
    }
    .landing-hero p {
        font-size: 1.1rem;
        color: #D0DCE8;
        max-width: 650px;
        margin: 0 auto 1.5rem auto;
        line-height: 1.6;
    }
    .hero-buttons { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
    .hero-btn {
        display: inline-block;
        padding: 12px 28px;
        border-radius: 6px;
        font-size: 0.95rem;
        font-weight: 600;
        text-decoration: none;
        transition: all 0.2s;
    }
    .hero-btn-primary { background: #27AE60; color: #FFF; }
    .hero-btn-primary:hover { background: #219A52; transform: translateY(-2px); color: #FFF; }
    .hero-btn-secondary { background: transparent; color: #FFF; border: 2px solid rgba(255,255,255,0.4); }
    .hero-btn-secondary:hover { border-color: #FFF; transform: translateY(-2px); color: #FFF; }
    .hero-btn-login { background: #FFFFFF; color: #1E3A5F; font-weight: 700; border: 2px solid #FFFFFF; }
    .hero-btn-login:hover { background: #E2E8F0; transform: translateY(-2px); color: #1E3A5F; }

    /* Section containers */
    .landing-section {
        padding: 2rem 0;
        animation: fadeInUp 0.7s ease-out both;
    }
    .landing-section:nth-child(2) { animation-delay: 0.1s; }
    .landing-section:nth-child(3) { animation-delay: 0.2s; }
    .landing-section:nth-child(4) { animation-delay: 0.3s; }
    .landing-section:nth-child(5) { animation-delay: 0.4s; }
    .landing-section-title {
        text-align: center;
        font-size: 1.6rem !important;
        color: #1E3A5F !important;
        font-weight: 700 !important;
        margin-bottom: 0.4rem !important;
    }
    .landing-section-sub {
        text-align: center;
        color: #6C757D;
        font-size: 0.95rem;
        margin-bottom: 2rem;
    }

    /* Pain point cards */
    .pain-card {
        background: #FFFFFF;
        border: 1px solid #E0E4E8;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s;
        height: 100%;
        animation: fadeInUp 0.6s ease-out both;
    }
    .pain-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); border-color: #2C5F8A; }
    .pain-card .pain-icon { font-size: 2rem; margin-bottom: 0.5rem; animation: float 3s ease-in-out infinite; }
    .pain-card h4 { color: #E74C3C !important; font-size: 1rem !important; margin-bottom: 0.5rem !important; font-weight: 700 !important; }
    .pain-card p { color: #4A5568; font-size: 0.85rem; line-height: 1.5; }
    .pain-card .solution { color: #27AE60; font-weight: 600; font-size: 0.85rem; margin-top: 0.5rem; }

    /* Workflow steps */
    .workflow-container { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; margin: 1.5rem 0; }
    .workflow-step {
        background: #FFFFFF;
        border: 1px solid #E0E4E8;
        border-radius: 10px;
        padding: 1.5rem;
        flex: 1;
        min-width: 220px;
        max-width: 300px;
        text-align: center;
        position: relative;
    }
    .workflow-step:nth-child(1) { animation: slideInLeft 0.7s ease-out both; animation-delay: 0.3s; }
    .workflow-step:nth-child(2) { animation: fadeInUp 0.7s ease-out both; animation-delay: 0.5s; }
    .workflow-step:nth-child(3) { animation: slideInRight 0.7s ease-out both; animation-delay: 0.7s; }
    .step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px; height: 36px;
        background: #1E3A5F;
        color: #FFF;
        border-radius: 50%;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 0.7rem;
    }
    .workflow-step h4 { color: #1E3A5F !important; font-size: 0.95rem !important; margin-bottom: 0.5rem !important; }
    .workflow-step p { color: #6C757D; font-size: 0.82rem; line-height: 1.5; }

    /* Animated progress bar */
    .anim-progress { background: #E0E4E8; border-radius: 4px; height: 8px; margin-top: 0.8rem; overflow: hidden; }
    .anim-progress-fill { height: 100%; background: linear-gradient(90deg, #27AE60, #2C5F8A); border-radius: 4px; animation: progressFill 2s ease-out both; animation-delay: 1s; }

    /* Animated doc icons */
    .doc-icons { display: flex; gap: 10px; justify-content: center; margin-top: 0.8rem; }
    .doc-icon {
        display: inline-flex; align-items: center; gap: 4px;
        background: #F0F7FF; border: 1px solid #D0DCE8; border-radius: 6px;
        padding: 4px 8px; font-size: 0.7rem; color: #1E3A5F; font-weight: 600;
    }
    .doc-icon:nth-child(1) { animation: docAppear1 2.5s ease-out both; }
    .doc-icon:nth-child(2) { animation: docAppear2 2.5s ease-out both; }
    .doc-icon:nth-child(3) { animation: docAppear3 2.5s ease-out both; }

    /* Animated checklist */
    .anim-checklist { text-align: left; margin-top: 0.8rem; }
    .anim-check { font-size: 0.78rem; color: #4A5568; padding: 2px 0; }
    .anim-check:nth-child(1) { animation: checkAppear1 3s ease-out both; }
    .anim-check:nth-child(2) { animation: checkAppear2 3s ease-out both; }
    .anim-check:nth-child(3) { animation: checkAppear3 3s ease-out both; }
    .anim-check:nth-child(4) { animation: checkAppear4 3s ease-out both; }

    /* Feature cards */
    .feature-card {
        background: #FFFFFF;
        border: 1px solid #E0E4E8;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        transition: all 0.3s;
        height: 100%;
    }
    .feature-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.07); border-color: #4A90D9; }
    .feature-card .feat-icon { font-size: 1.8rem; margin-bottom: 0.4rem; }
    .feature-card h4 { color: #1E3A5F !important; font-size: 0.9rem !important; margin-bottom: 0.3rem !important; }
    .feature-card p { color: #6C757D; font-size: 0.8rem; line-height: 1.4; }

    /* Pricing card */
    .pricing-card {
        background: #FFFFFF;
        border: 2px solid #27AE60;
        border-radius: 14px;
        padding: 2.5rem 2rem;
        max-width: 420px;
        margin: 0 auto;
        text-align: center;
        box-shadow: 0 8px 32px rgba(39,174,96,0.15);
        animation: fadeInUp 0.8s ease-out both;
    }
    .pricing-old {
        font-size: 1.4rem;
        color: #999;
        text-decoration: line-through;
        text-decoration-color: #E74C3C;
        text-decoration-thickness: 2px;
    }
    .pricing-new {
        font-size: 2.8rem;
        font-weight: 800;
        color: #27AE60;
        line-height: 1.1;
    }
    .pricing-new span { font-size: 1rem; font-weight: 500; color: #6C757D; }
    .pricing-badge {
        display: inline-block;
        background: #E74C3C;
        color: #FFF;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        margin: 0.8rem 0;
        animation: pulse 2s ease-in-out infinite;
    }
    .pricing-features { text-align: left; margin: 1.2rem 0; }
    .pricing-features div { padding: 4px 0; font-size: 0.88rem; color: #4A5568; }
    .pricing-cta {
        display: inline-block;
        padding: 14px 36px;
        background: #27AE60;
        color: #FFF;
        border-radius: 8px;
        font-size: 1.05rem;
        font-weight: 700;
        text-decoration: none;
        transition: all 0.2s;
        margin-top: 0.8rem;
    }
    .pricing-cta:hover { background: #219A52; transform: translateY(-2px); color: #FFF; }
    .pricing-note { font-size: 0.8rem; color: #999; margin-top: 0.7rem; }

    /* Stats row */
    .stats-row { display: flex; justify-content: center; gap: 40px; flex-wrap: wrap; margin: 1.5rem 0; }
    .stat-item { text-align: center; animation: fadeInUp 0.7s ease-out both; }
    .stat-item:nth-child(1) { animation-delay: 0.1s; }
    .stat-item:nth-child(2) { animation-delay: 0.2s; }
    .stat-item:nth-child(3) { animation-delay: 0.3s; }
    .stat-number { font-size: 2rem; font-weight: 800; color: #1E3A5F; }
    .stat-label { font-size: 0.85rem; color: #6C757D; }

    /* Testimonial cards */
    .testimonial-card {
        background: #F8F9FA;
        border: 1px solid #E0E4E8;
        border-radius: 10px;
        padding: 1.2rem;
        font-style: italic;
        color: #4A5568;
        font-size: 0.88rem;
        line-height: 1.5;
    }
    .testimonial-card .author { font-style: normal; font-weight: 600; color: #1E3A5F; margin-top: 0.6rem; font-size: 0.82rem; }

    /* ROI calculator results */
    .roi-result {
        background: #FFFFFF;
        border: 1px solid #E0E4E8;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
    }
    .roi-big-number { font-size: 2rem; font-weight: 800; line-height: 1.2; }
    .roi-big-number.savings { color: #27AE60; }
    .roi-big-number.cost { color: #E74C3C; }
    .roi-label { font-size: 0.82rem; color: #6C757D; margin-top: 0.2rem; }
    .roi-comparison {
        background: #F0FFF4;
        border: 2px solid #27AE60;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .roi-multiplier { font-size: 1.8rem; font-weight: 800; color: #27AE60; }

    /* Logout button in nav */
    .topnav-bar > a.logout-btn {
        margin-left: auto;
        color: #6C757D;
        border-right: none;
        border-left: 1px solid #DEE2E6;
    }
    .topnav-bar > a.logout-btn:hover { background: #FDE8E8; color: #E74C3C; }

    /* Landing footer */
    .landing-footer {
        background: #1E3A5F;
        color: #D0DCE8;
        padding: 2rem;
        margin: 2rem -1rem -1rem -1rem;
        text-align: center;
    }
    .landing-footer h3 { color: #FFFFFF !important; font-size: 1.3rem !important; }
    .landing-footer p { color: #A0B4C8; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

db.init_db()
db.seed_data()
db.seed_default_admin()

# --- Helpers ---

def calculate_days_lost(case_row):
    """Calculate days lost for a single case based on DOI and capacity.
    Total incapacity = all days since DOI.
    Modified duty = 50% of days since DOI.
    Full capacity / cleared = 0 days lost.
    """
    doi = case_row.get("date_of_injury")
    cap = case_row.get("current_capacity", "")
    if not doi or not cap:
        return 0
    try:
        doi_date = datetime.strptime(str(doi), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return 0
    days_since = (date.today() - doi_date).days
    if days_since < 0:
        return 0
    cap_lower = str(cap).lower()
    if "no capacity" in cap_lower:
        return days_since
    elif "modified" in cap_lower:
        return int(days_since * 0.5)
    elif "full" in cap_lower or "cleared" in cap_lower or "clearance" in cap_lower:
        return 0
    return int(days_since * 0.5)  # default: partial


def get_cases_df():
    conn = db.get_connection()
    df = pd.read_sql_query("SELECT * FROM cases ORDER BY state, worker_name", conn)
    conn.close()
    return df


def get_latest_cocs():
    conn = db.get_connection()
    df = pd.read_sql_query("""
        SELECT c.case_id, c.cert_from, c.cert_to, c.capacity, c.days_per_week, c.hours_per_day,
               cs.worker_name
        FROM certificates c
        JOIN cases cs ON c.case_id = cs.id
        WHERE c.id IN (
            SELECT id FROM certificates c2
            WHERE c2.case_id = c.case_id
            ORDER BY c2.cert_to DESC
            LIMIT 1
        )
        ORDER BY c.cert_to ASC
    """, conn)
    conn.close()
    return df


def get_terminations():
    conn = db.get_connection()
    df = pd.read_sql_query("""
        SELECT t.*, c.worker_name, c.state, c.site
        FROM terminations t
        JOIN cases c ON t.case_id = c.id
        ORDER BY t.status, c.worker_name
    """, conn)
    conn.close()
    return df


def get_documents(case_id):
    conn = db.get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM documents WHERE case_id = ? ORDER BY doc_type", conn, params=(case_id,)
    )
    conn.close()
    return df


def get_activity_log(case_id=None, limit=50):
    conn = db.get_connection()
    if case_id:
        df = pd.read_sql_query(
            """SELECT a.*, c.worker_name FROM activity_log a
               LEFT JOIN cases c ON a.case_id = c.id
               WHERE a.case_id = ? ORDER BY a.created_at DESC LIMIT ?""",
            conn, params=(case_id, limit)
        )
    else:
        df = pd.read_sql_query(
            """SELECT a.*, c.worker_name FROM activity_log a
               LEFT JOIN cases c ON a.case_id = c.id
               ORDER BY a.created_at DESC LIMIT ?""",
            conn, params=(limit,)
        )
    conn.close()
    return df


def log_activity(case_id, action, details=""):
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO activity_log (case_id, action, details) VALUES (?, ?, ?)",
        (case_id, action, details)
    )
    conn.commit()
    conn.close()


def log_audit(action, table_name=None, record_id=None, case_id=None,
              field_changed=None, old_value=None, new_value=None, details=None):
    """Log an audit trail entry."""
    user = st.session_state.get("current_user", "system")
    conn = db.get_connection()
    conn.execute(
        """INSERT INTO audit_log (user, action, table_name, record_id, case_id,
           field_changed, old_value, new_value, details)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user, action, table_name, record_id, case_id,
         field_changed, str(old_value) if old_value is not None else None,
         str(new_value) if new_value is not None else None, details)
    )
    conn.commit()
    conn.close()


def coc_status(cert_to_str):
    if not cert_to_str:
        return "No COC", "red"
    try:
        cert_to = datetime.strptime(cert_to_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return "Invalid Date", "gray"
    today = date.today()
    delta = (cert_to - today).days
    if delta < 0:
        return f"EXPIRED ({abs(delta)}d ago)", "red"
    elif delta <= 7:
        return f"EXPIRING ({delta}d)", "orange"
    else:
        return f"Current ({delta}d left)", "green"


def capacity_emoji(cap):
    if not cap:
        return "⚪"
    cap_lower = cap.lower()
    if "no capacity" in cap_lower:
        return "🔴"
    elif "full" in cap_lower or "clearance" in cap_lower or "cleared" in cap_lower:
        return "🟢"
    elif "modified" in cap_lower:
        return "🟠"
    return "⚪"


def priority_emoji(p):
    return {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟢"}.get(p, "⚪")


def coc_status_emoji(color):
    return {"red": "🔴", "orange": "🟠", "green": "🟢"}.get(color, "⚪")


def row_to_dict(conn, table, row):
    """Convert a sqlite3.Row to a dict using table column names."""
    cols = [desc[0] for desc in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]
    return dict(zip(cols, row))


def save_coc_to_onedrive(worker_name: str, file_bytes: bytes, filename: str) -> str | None:
    """Save a COC PDF to the worker's Active Cases folder. Returns saved path or None."""
    if not os.path.isdir(ACTIVE_CASES_DIR):
        return None
    # Find matching worker folder
    best_folder = None
    for folder in os.listdir(ACTIVE_CASES_DIR):
        folder_path = os.path.join(ACTIVE_CASES_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        if worker_name.upper() in folder.upper() or folder.upper() in worker_name.upper():
            best_folder = folder_path
            break
        # Match on last name
        last = worker_name.split()[-1].upper() if worker_name.split() else ""
        if last and last in folder.upper():
            best_folder = folder_path
            break
    if not best_folder:
        return None
    # Create Medical/COC/ if needed
    coc_dir = os.path.join(best_folder, "Medical", "COC")
    os.makedirs(coc_dir, exist_ok=True)
    dest = os.path.join(coc_dir, filename)
    # Avoid overwriting
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        dest = os.path.join(coc_dir, f"{base}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}")
    with open(dest, 'wb') as f:
        f.write(file_bytes)
    return dest


def get_worker_names_list():
    """Get list of worker names for COC matching."""
    conn = db.get_connection()
    rows = conn.execute("SELECT worker_name FROM cases ORDER BY worker_name").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_processed_coc_paths():
    """Get set of already-processed COC file paths."""
    conn = db.get_connection()
    rows = conn.execute("SELECT file_path FROM processed_coc_files").fetchall()
    conn.close()
    return {r[0] for r in rows}


def mark_coc_processed(file_path: str, case_id: int | None = None):
    """Mark a COC file as processed in the database."""
    conn = db.get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO processed_coc_files (file_path, case_id) VALUES (?, ?)",
            (file_path, case_id)
        )
        conn.commit()
    except Exception:
        pass
    conn.close()


# --- Session State Init ---
if "page" not in st.session_state:
    st.session_state.page = "Landing"
if "selected_case_id" not in st.session_state:
    st.session_state.selected_case_id = None
if "prev_page" not in st.session_state:
    st.session_state.prev_page = "Dashboard"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_display_name" not in st.session_state:
    st.session_state.user_display_name = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# Helper: check if user is logged in
def require_auth():
    """Returns True if authenticated, False otherwise (redirects to login)."""
    if not st.session_state.authenticated:
        st.session_state.page = "Login"
        st.rerun()
        return False
    return True

def user_has_role(*roles):
    """Check if the current user has one of the given roles."""
    return st.session_state.user_role in roles

# Role-based page access
ADMIN_PAGES = ["Activity Log"]
MANAGER_PAGES = ["Dashboard", "All Cases", "Incident Report", "COC Tracker",
                 "Calendar", "Correspondence"]
VIEWER_PAGES = ["Dashboard", "All Cases"]

# All nav items
NAV_ITEMS = ["Dashboard", "All Cases", "Entitlements", "Calendar",
             "COC Tracker", "Correspondence", "Terminations",
             "Injury Analytics", "Site Analysis",
             "PIAWE Calculator", "Payroll", "Activity Log",
             "Incident Report", "Incidents Review", "Manage Users"]

page = st.session_state.page

# --- Navigation: query params handled FIRST ---
_nav_param = st.query_params.get("nav")
if _nav_param:
    st.query_params.clear()
    _on_dash = (page == "Dashboard")
    if _nav_param == "back" and not _on_dash:
        st.session_state.page = st.session_state.get("prev_page", "Dashboard")
        st.session_state.selected_case_id = None
        st.rerun()
    elif _nav_param == "home":
        st.session_state.page = "Dashboard"
        st.session_state.selected_case_id = None
        st.rerun()
    elif _nav_param == "new":
        st.session_state.prev_page = page
        st.session_state.page = "New Case"
        st.rerun()
    elif _nav_param == "login":
        st.session_state.page = "Login"
        st.rerun()
    elif _nav_param == "logout":
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.session_state.user_role = None
        st.session_state.user_display_name = None
        st.session_state.user_id = None
        st.session_state.page = "Landing"
        st.session_state.selected_case_id = None
        st.rerun()
    elif _nav_param == "landing":
        st.session_state.page = "Landing"
        st.rerun()
    elif _nav_param in NAV_ITEMS and _nav_param != page:
        st.session_state.prev_page = page
        st.session_state.page = _nav_param
        st.session_state.selected_case_id = None
        st.rerun()

# --- Top Navigation Bar + Sidebar (hidden on Landing and Login pages) ---

# Default filter values
filter_state = ["VIC", "NSW", "QLD"]
filter_capacity = ["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"]
filter_priority = ["HIGH", "MEDIUM", "LOW"]

if page not in ("Landing", "Login"):
    # Redirect to login if not authenticated
    if not st.session_state.authenticated:
        st.session_state.page = "Login"
        st.rerun()

    _role = st.session_state.user_role or "viewer"

    # Build nav groups based on role
    if _role == "admin":
        NAV_GROUPS = [
            ("Cases", ["Dashboard", "All Cases"]),
            ("Tracking", ["COC Tracker", "Calendar", "Correspondence", "Terminations"]),
            ("Reports", ["Injury Analytics", "Site Analysis", "Entitlements"]),
            ("Tools", ["PIAWE Calculator", "Payroll"]),
            ("Admin", ["Activity Log", "Incidents Review", "Manage Users"]),
        ]
    elif _role == "manager":
        NAV_GROUPS = [
            ("Cases", ["Dashboard", "All Cases"]),
            ("Tracking", ["COC Tracker", "Calendar", "Correspondence"]),
            ("Report", ["Incident Report"]),
        ]
    else:  # viewer
        NAV_GROUPS = [
            ("Cases", ["Dashboard", "All Cases"]),
        ]

    _on_dashboard = (page == "Dashboard")

    # Render the connected HTML nav bar with dropdowns
    _T = ' target="_parent"'  # prevent new-tab in Streamlit iframe
    _back_class = "disabled" if _on_dashboard else ""
    _nav_html = f'<a class="{_back_class}" href="?nav=back"{_T}>← Back</a>'
    _nav_html += f'<a class="{_back_class}" href="?nav=home"{_T}>Home</a>'
    if _role == "admin":
        _nav_html += f'<a class="new-btn" href="?nav=new"{_T}>+ New Case</a>'

    for group_label, group_items in NAV_GROUPS:
        group_has_active = page in group_items
        label_cls = "nav-drop-label has-active" if group_has_active else "nav-drop-label"
        items_html = ""
        for item in group_items:
            cls = "active" if page == item else ""
            items_html += f'<a class="{cls}" href="?nav={item}"{_T}>{item}</a>'
        _nav_html += (
            f'<div class="nav-dropdown">'
            f'<span class="{label_cls}">{group_label}<span class="nav-drop-arrow">▼</span></span>'
            f'<div class="nav-dropdown-menu">{items_html}</div>'
            f'</div>'
        )

    # Logout button (pushed to right via CSS margin-left: auto)
    _nav_html += f'<a class="logout-btn" href="?nav=logout"{_T}>Logout</a>'

    st.markdown(f'<div class="topnav-bar">{_nav_html}</div>', unsafe_allow_html=True)

    # --- Sidebar ---
    st.sidebar.title("🛡️ ClaimTrack Pro")
    st.sidebar.caption(f"Today: {date.today().strftime('%d %b %Y')}")
    _disp = st.session_state.user_display_name or st.session_state.current_user or ""
    _role_label = (st.session_state.user_role or "").title()
    st.sidebar.markdown(f"**{_disp}** ({_role_label})")
    st.sidebar.divider()
    st.sidebar.caption("Filters")

    _all_states = ["VIC", "NSW", "QLD"]
    _all_caps = ["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"]
    _all_pris = ["HIGH", "MEDIUM", "LOW"]

    _sel_state = st.sidebar.selectbox("State", ["All"] + _all_states)
    _sel_cap = st.sidebar.selectbox("Capacity", ["All"] + _all_caps)
    _sel_pri = st.sidebar.selectbox("Priority", ["All"] + _all_pris)

    filter_state = _all_states if _sel_state == "All" else [_sel_state]
    filter_capacity = _all_caps if _sel_cap == "All" else [_sel_cap]
    filter_priority = _all_pris if _sel_pri == "All" else [_sel_pri]

# ============================================================
# LANDING / ADVERTISING PAGE
# ============================================================
if page == "Landing":
    # --- Hero Banner ---
    st.markdown("""
    <div class="landing-hero">
        <h1>ClaimTrack Pro</h1>
        <p style="font-size:1.3rem; color:#FFFFFF; margin-bottom:0.3rem; font-weight:600;">Take Control of Your Workcover Claims</p>
        <p>The all-in-one platform that saves time, reduces premiums, and ensures you never miss a deadline.</p>
        <div class="hero-buttons">
            <a class="hero-btn hero-btn-primary" href="#roi-calc">Calculate Your Savings</a>
            <a class="hero-btn hero-btn-login" href="?nav=login" target="_parent">Login →</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit button fallback for login (HTML links may not work on all hosts)
    _hero_c1, _hero_c2, _hero_c3 = st.columns([2, 1, 2])
    with _hero_c2:
        if st.button("Login / Get Started", type="primary", use_container_width=True):
            st.session_state.page = "Login"
            st.rerun()

    st.markdown("")  # spacer

    # --- Pain Points ---
    st.markdown('<h2 class="landing-section-title">Sound Familiar?</h2>', unsafe_allow_html=True)
    st.markdown('<p class="landing-section-sub">These problems cost Australian businesses millions every year</p>', unsafe_allow_html=True)

    _pp1, _pp2, _pp3 = st.columns(3)
    with _pp1:
        st.markdown("""
        <div class="pain-card" style="animation-delay: 0.1s;">
            <div class="pain-icon">⏰</div>
            <h4>Missing Deadlines?</h4>
            <p>COC expiries, review dates, and insurer responses slip through the cracks. Every missed deadline extends claims and costs you money.</p>
            <div class="solution">→ Automated alerts for every deadline</div>
        </div>
        """, unsafe_allow_html=True)
    with _pp2:
        st.markdown("""
        <div class="pain-card" style="animation-delay: 0.2s;">
            <div class="pain-icon">📄</div>
            <h4>Drowning in Paperwork?</h4>
            <p>RTW plans, toolbox talks, registers of injury, correspondence logs — all manually created, scattered across folders.</p>
            <div class="solution">→ One-click document generation</div>
        </div>
        """, unsafe_allow_html=True)
    with _pp3:
        st.markdown("""
        <div class="pain-card" style="animation-delay: 0.3s;">
            <div class="pain-icon">📈</div>
            <h4>Premiums Rising?</h4>
            <p>Poor claims management leads to higher experience ratings. Every open claim and missed step-down drives your premium up.</p>
            <div class="solution">→ Track costs and reduce premiums</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown("---")

    # --- Pricing Card (prominent, early on page) ---
    st.markdown('<h2 class="landing-section-title">Simple, Transparent Pricing</h2>', unsafe_allow_html=True)
    st.markdown('<p class="landing-section-sub">No hidden fees. No lock-in contracts. Cancel anytime.</p>', unsafe_allow_html=True)

    _pr1, _pr2, _pr3 = st.columns([1, 2, 1])
    with _pr2:
        st.markdown("""
        <div class="pricing-card">
            <div class="pricing-old">$599 / month</div>
            <div class="pricing-new">$299<span> / month</span></div>
            <div class="pricing-badge">🔥 First 20 Subscribers Only</div>
            <div class="pricing-features">
                <div>✅ Unlimited active cases</div>
                <div>✅ All document generation (RTW, Toolbox, Register)</div>
                <div>✅ All 6 Australian states</div>
                <div>✅ Entitlement &amp; step-down calculator</div>
                <div>✅ Premium savings tracking</div>
                <div>✅ Certificate of Capacity tracking &amp; alerts</div>
                <div>✅ Insurer correspondence log</div>
                <div>✅ Days lost to injury reporting</div>
                <div>✅ Audit trail &amp; activity logging</div>
                <div>✅ Email support</div>
            </div>
            <div style="font-size:0.88rem; color:#4A5568; margin-bottom:1rem;">For businesses up to 50 employees</div>
            <div class="pricing-note" style="margin-top:1rem;">Enterprise (50+ employees)? <a href="mailto:hello@claimtrackpro.com.au">Contact us</a></div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Get Started →", type="primary", use_container_width=True, key="pricing_login"):
            st.session_state.page = "Login"
            st.rerun()

    st.markdown("")
    st.markdown("---")

    # --- Animated Workflow ---
    st.markdown('<h2 class="landing-section-title">How It Works — 3 Simple Steps</h2>', unsafe_allow_html=True)
    st.markdown('<p class="landing-section-sub" style="font-size:1.1rem; font-weight:600; color:#1E3A5F;">Never miss documentation again.</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="workflow-container">
        <div class="workflow-step">
            <div class="step-number">1</div>
            <h4>Add a Case in Seconds</h4>
            <p>Upload an incident report and watch the form auto-fill. Worker details, injury info, and dates — extracted instantly.</p>
            <div class="anim-progress"><div class="anim-progress-fill" style="width:100%"></div></div>
        </div>
        <div class="workflow-step">
            <div class="step-number">2</div>
            <h4>Auto-Generate Documents</h4>
            <p>RTW Plans, Toolbox Talks, and Registers of Injury — generated with one click, pre-filled with case data.</p>
            <div class="doc-icons">
                <div class="doc-icon">📋 RTW Plan</div>
                <div class="doc-icon">🔧 Toolbox Talk</div>
                <div class="doc-icon">📝 Register</div>
            </div>
        </div>
        <div class="workflow-step">
            <div class="step-number">3</div>
            <h4>Track Every Milestone</h4>
            <p>COC expiries, entitlement step-downs, insurer follow-ups — nothing slips through. Ever.</p>
            <div class="anim-checklist">
                <div class="anim-check">✅ COC tracked &amp; alerts set</div>
                <div class="anim-check">✅ Step-downs calculated</div>
                <div class="anim-check">✅ Documents complete</div>
                <div class="anim-check">✅ Premiums monitored</div>
            </div>
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Feature Grid ---
    st.markdown('<h2 class="landing-section-title">Everything You Need in One Place</h2>', unsafe_allow_html=True)
    st.markdown('<p class="landing-section-sub">Built specifically for Australian workcover claim management</p>', unsafe_allow_html=True)

    _f1, _f2, _f3 = st.columns(3)
    with _f1:
        st.markdown("""
        <div class="feature-card">
            <div class="feat-icon">📊</div>
            <h4>Claims Dashboard</h4>
            <p>Real-time overview of all active claims with priority alerts and status tracking</p>
        </div>
        """, unsafe_allow_html=True)
    with _f2:
        st.markdown("""
        <div class="feature-card">
            <div class="feat-icon">📜</div>
            <h4>Certificate Tracking</h4>
            <p>Never miss a COC expiry again — automated alerts and full history per worker</p>
        </div>
        """, unsafe_allow_html=True)
    with _f3:
        st.markdown("""
        <div class="feature-card">
            <div class="feat-icon">🧮</div>
            <h4>Entitlement Calculator</h4>
            <p>VIC, NSW &amp; QLD step-down rules calculated automatically from date of injury</p>
        </div>
        """, unsafe_allow_html=True)

    _f4, _f5, _f6 = st.columns(3)
    with _f4:
        st.markdown("""
        <div class="feature-card">
            <div class="feat-icon">📁</div>
            <h4>Document Generation</h4>
            <p>RTW Plans, Toolbox Talks, Registers of Injury — one click, fully pre-filled</p>
        </div>
        """, unsafe_allow_html=True)
    with _f5:
        st.markdown("""
        <div class="feature-card">
            <div class="feat-icon">📧</div>
            <h4>Correspondence Log</h4>
            <p>Track every insurer email, phone call, and letter with follow-up reminders</p>
        </div>
        """, unsafe_allow_html=True)
    with _f6:
        st.markdown("""
        <div class="feature-card">
            <div class="feat-icon">💰</div>
            <h4>Premium Savings Tracker</h4>
            <p>See exactly how better claim management reduces your workcover premiums</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown("---")

    # --- ROI Calculator ---
    st.markdown('<a name="roi-calc"></a>', unsafe_allow_html=True)
    st.markdown('<h2 class="landing-section-title">See How Much You Could Save</h2>', unsafe_allow_html=True)
    st.markdown('<p class="landing-section-sub">Enter your details below — most businesses save 5-15x the software cost</p>', unsafe_allow_html=True)

    _roi_left, _roi_right = st.columns([1, 1])
    with _roi_left:
        st.markdown("##### Your Details")
        _roi_state = st.selectbox("State", ["VIC", "NSW", "QLD", "SA", "TAS", "WA"], key="roi_state")
        _roi_employees = st.number_input("Number of employees", min_value=1, max_value=10000, value=30, key="roi_emp")
        _roi_wages = st.number_input("Total annual wages ($)", min_value=0, max_value=100_000_000, value=2_000_000, step=100_000, key="roi_wages")
        _roi_rate = st.number_input("Current premium rate (%)", min_value=0.1, max_value=20.0, value=2.5, step=0.1, key="roi_rate")
        _roi_claims = st.number_input("Claims per year", min_value=0, max_value=200, value=3, key="roi_claims")
        _roi_avg_cost = st.number_input("Average cost per claim ($)", min_value=0, max_value=1_000_000, value=25_000, step=1_000, key="roi_avg")

    with _roi_right:
        st.markdown("##### Your Potential Savings")
        _roi_result = entitlements.calculate_premium_savings(
            annual_wages=_roi_wages,
            current_rate=_roi_rate,
            num_claims=_roi_claims,
            avg_claim_cost=_roi_avg_cost,
            state=_roi_state,
        )
        _software_annual = 299 * 12  # $3,588/yr

        st.markdown(f"""
        <div class="roi-result" style="margin-bottom:12px;">
            <div class="roi-label">Your Current Annual Premium</div>
            <div class="roi-big-number cost">${_roi_result.current_premium:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="roi-result" style="margin-bottom:12px;">
            <div class="roi-label">Potential Annual Savings (Moderate Scenario)</div>
            <div class="roi-big-number savings">${_roi_result.annual_savings:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

        if _roi_result.annual_savings > 0:
            _roi_multiplier = _roi_result.annual_savings / _software_annual if _software_annual > 0 else 0
            st.markdown(f"""
            <div class="roi-comparison">
                <div style="font-size:0.85rem; color:#4A5568; margin-bottom:4px;">Software Cost: <strong>${_software_annual:,}/yr</strong> vs Savings: <strong>${_roi_result.annual_savings:,.0f}/yr</strong></div>
                <div class="roi-multiplier">Every $1 spent saves you ${_roi_multiplier:.2f}</div>
                <div style="font-size:0.85rem; color:#6C757D; margin-top:6px;">5-year savings: <strong style="color:#27AE60;">${_roi_result.savings_5yr:,.0f}</strong></div>
            </div>
            """, unsafe_allow_html=True)

        # Show all 3 scenarios
        st.markdown("")
        for _sc in _roi_result.scenarios:
            _sc_label = _sc["label"].split("(")[0].strip()
            st.markdown(
                f"**{_sc_label}**: save **${_sc['annual_savings']:,.0f}/yr** "
                f"(rate {_sc['new_rate_pct']}, reduction {_sc['reduction_pct']:.0f}%)"
            )

    st.markdown("")
    st.markdown("---")

    # --- Social Proof / Stats ---
    st.markdown("""
    <div class="stats-row">
        <div class="stat-item">
            <div class="stat-number">500+</div>
            <div class="stat-label">Claims Managed</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">6</div>
            <div class="stat-label">States Covered</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">$2M+</div>
            <div class="stat-label">Premium Savings Tracked</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # Testimonials
    _t1, _t2 = st.columns(2)
    with _t1:
        st.markdown("""
        <div class="testimonial-card">
            "We used to track everything in spreadsheets and constantly missed COC expiry dates. This system has completely changed how we manage claims — nothing falls through the cracks now."
            <div class="author">— Operations Manager, Facilities Services Company</div>
        </div>
        """, unsafe_allow_html=True)
    with _t2:
        st.markdown("""
        <div class="testimonial-card">
            "The premium savings calculator alone justified the cost. We reduced our experience rating within the first year and saved over $15,000 in annual premiums."
            <div class="author">— Finance Director, Cleaning Services Group</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown("---")

    # --- Footer CTA ---
    st.markdown("""
    <div class="landing-footer">
        <h3>Ready to Get Started with ClaimTrack Pro?</h3>
        <p style="margin-bottom: 1.2rem;">Join Australian businesses already saving time and money with smarter claim management.</p>
        <p style="margin-top:1.5rem; font-size:0.8rem;">Questions? Contact us at hello@claimtrackpro.com.au</p>
    </div>
    """, unsafe_allow_html=True)
    _fc1, _fc2, _fc3 = st.columns([2, 1, 2])
    with _fc2:
        if st.button("Get Started →", type="primary", use_container_width=True, key="footer_login"):
            st.session_state.page = "Login"
            st.rerun()


# ============================================================
# LOGIN PAGE
# ============================================================
elif page == "Login":
    st.markdown("")
    _lc1, _lc2, _lc3 = st.columns([1, 1.5, 1])
    with _lc2:
        st.markdown("""
        <div style="text-align:center; margin-bottom:1.5rem;">
            <h2 style="color:#1E3A5F !important;">🛡️ ClaimTrack Pro</h2>
            <p style="color:#6C757D;">Sign in to your account</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            _login_user = st.text_input("Username")
            _login_pass = st.text_input("Password", type="password")
            _login_btn = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if _login_btn:
                if _login_user and _login_pass:
                    _auth_result = db.authenticate_user(_login_user.strip(), _login_pass)
                    if _auth_result:
                        st.session_state.authenticated = True
                        st.session_state.current_user = _auth_result["username"]
                        st.session_state.user_role = _auth_result["role"]
                        st.session_state.user_display_name = _auth_result["display_name"]
                        st.session_state.user_id = _auth_result["id"]
                        st.session_state.page = "Dashboard"
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter both username and password")

        st.markdown("")
        if st.button("← Back to home", use_container_width=True, key="login_back_home"):
            st.session_state.page = "Landing"
            st.rerun()

        st.markdown("")
        st.info("**Demo login:** username `admin` / password `admin123`")


# ============================================================
# INCIDENT REPORT PAGE (for managers/supervisors)
# ============================================================
elif page == "Incident Report":
    require_auth()
    st.title("📋 Lodge Incident Report")
    st.caption("Submit an incident report for review by the admin team.")

    with st.form("incident_form"):
        st.markdown("##### Worker Details")
        _ic1, _ic2 = st.columns(2)
        with _ic1:
            _inc_worker = st.text_input("Worker Name *")
            _inc_site = st.text_input("Site / Location")
            _inc_entity = st.text_input("Entity / Company")
        with _ic2:
            _inc_state = st.selectbox("State", ["VIC", "NSW", "QLD", "SA", "TAS", "WA"])
            _inc_date = st.date_input("Date of Incident *", format="DD/MM/YYYY")
            _inc_time = st.text_input("Time of Incident (e.g. 10:30 AM)")

        st.markdown("##### Incident Details")
        _inc_location = st.text_input("Specific location (e.g. warehouse floor, bathroom, loading dock)")
        _inc_desc = st.text_area("Description of incident and injury *", height=120)
        _id1, _id2 = st.columns(2)
        with _id1:
            _inc_body = st.text_input("Body part injured")
            _inc_type = st.selectbox("Injury type", ["-- Select --", "Manual Handling / Back",
                "Laceration / Cut", "Crush / Fracture", "Sprain / Strain", "Chemical",
                "Slip / Trip / Fall", "Disease / Illness", "Burns", "Other"])
        with _id2:
            _inc_firstaid = st.selectbox("First aid given?", ["Yes", "No"])
            _inc_firstaid_detail = st.text_input("First aid details (if applicable)")

        st.markdown("##### Additional Information")
        _inc_witnesses = st.text_area("Witnesses (names and contact details)", height=60)
        _inc_action = st.text_area("Immediate action taken", height=60)
        _ia1, _ia2 = st.columns(2)
        with _ia1:
            _inc_super_name = st.text_input("Supervisor name", value=st.session_state.user_display_name or "")
        with _ia2:
            _inc_super_phone = st.text_input("Supervisor contact phone")

        _inc_notes = st.text_area("Additional notes", height=60)

        _inc_submit = st.form_submit_button("Submit Incident Report", use_container_width=True, type="primary")

        if _inc_submit:
            if not _inc_worker or not _inc_desc:
                st.error("Worker name and incident description are required.")
            else:
                conn = db.get_connection()
                conn.execute("""
                    INSERT INTO incidents (submitted_by, worker_name, date_of_incident, time_of_incident,
                        site, entity, state, location_detail, injury_description, body_part, injury_type,
                        first_aid_given, first_aid_details, witnesses, immediate_action,
                        supervisor_name, supervisor_phone, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    st.session_state.user_id,
                    _inc_worker, str(_inc_date), _inc_time,
                    _inc_site, _inc_entity, _inc_state, _inc_location,
                    _inc_desc, _inc_body,
                    _inc_type if _inc_type != "-- Select --" else None,
                    _inc_firstaid, _inc_firstaid_detail,
                    _inc_witnesses, _inc_action,
                    _inc_super_name, _inc_super_phone, _inc_notes,
                ))
                conn.commit()
                conn.close()
                st.success("Incident report submitted successfully! The admin team will review it shortly.")
                log_activity(None, "Incident submitted", f"Worker: {_inc_worker}, by {st.session_state.current_user}")


# ============================================================
# INCIDENTS REVIEW PAGE (admin only)
# ============================================================
elif page == "Incidents Review":
    require_auth()
    if not user_has_role("admin"):
        st.error("You don't have permission to access this page.")
    else:
        st.title("📋 Incident Reports — Review Queue")

        conn = db.get_connection()
        incidents = pd.read_sql_query("""
            SELECT i.*, u.display_name as submitted_by_name
            FROM incidents i
            LEFT JOIN users u ON i.submitted_by = u.id
            ORDER BY
                CASE i.status WHEN 'Pending' THEN 0 WHEN 'Reviewed' THEN 1 ELSE 2 END,
                i.created_at DESC
        """, conn)
        conn.close()

        if len(incidents) == 0:
            st.info("No incident reports yet.")
        else:
            _pending = incidents[incidents["status"] == "Pending"]
            _reviewed = incidents[incidents["status"] != "Pending"]

            if len(_pending) > 0:
                st.markdown(f"### Pending Review ({len(_pending)})")
                for _, inc in _pending.iterrows():
                    with st.container(border=True):
                        _c1, _c2, _c3 = st.columns([3, 2, 1])
                        with _c1:
                            st.markdown(f"**{inc['worker_name']}** — {inc['injury_description'][:80]}...")
                            st.caption(f"Site: {inc['site'] or 'N/A'} | State: {inc['state'] or 'N/A'} | Date: {inc['date_of_incident']}")
                        with _c2:
                            st.caption(f"Submitted by: {inc['submitted_by_name'] or 'Unknown'}")
                            st.caption(f"Body part: {inc['body_part'] or 'N/A'} | Type: {inc['injury_type'] or 'N/A'}")
                        with _c3:
                            if st.button("Convert to Case", key=f"convert_{inc['id']}", type="primary"):
                                # Create case from incident
                                _conn = db.get_connection()
                                _conn.execute("""
                                    INSERT INTO cases (worker_name, state, entity, site, date_of_injury,
                                        injury_description, injury_type, current_capacity, status, priority,
                                        notes)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Unknown', 'Active', 'MEDIUM', ?)
                                """, (
                                    inc["worker_name"], inc["state"] or "VIC",
                                    inc["entity"], inc["site"], inc["date_of_incident"],
                                    inc["injury_description"], inc["injury_type"],
                                    f"From incident report. First aid: {inc['first_aid_given']}. Witnesses: {inc['witnesses'] or 'None'}",
                                ))
                                _new_case_id = _conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                                # Mark incident as reviewed
                                _conn.execute("""
                                    UPDATE incidents SET status = 'Converted', reviewed_by = ?,
                                        reviewed_at = ?, converted_case_id = ?
                                    WHERE id = ?
                                """, (st.session_state.user_id, datetime.now().isoformat(), _new_case_id, inc["id"]))
                                _conn.commit()
                                # Seed document checklist for new case
                                _doc_types = ["Incident Report", "Claim Form", "Payslips (12 months)",
                                    "PIAWE Calculation", "Certificate of Capacity (Current)",
                                    "RTW Plan (Current)", "Suitable Duties Plan", "Medical Certificates",
                                    "Insurance Correspondence", "Wage Records"]
                                for _dt in _doc_types:
                                    _is_present = 1 if _dt == "Incident Report" else 0
                                    _conn.execute("INSERT INTO documents (case_id, doc_type, is_present) VALUES (?, ?, ?)",
                                                  (_new_case_id, _dt, _is_present))
                                _conn.commit()
                                _conn.close()
                                log_activity(_new_case_id, "Case created from incident", f"Incident #{inc['id']} by {st.session_state.current_user}")
                                st.success(f"Case created for {inc['worker_name']}! (Case #{_new_case_id})")
                                st.rerun()

                            if st.button("Dismiss", key=f"dismiss_{inc['id']}"):
                                _conn = db.get_connection()
                                _conn.execute("UPDATE incidents SET status = 'Dismissed', reviewed_by = ?, reviewed_at = ? WHERE id = ?",
                                              (st.session_state.user_id, datetime.now().isoformat(), inc["id"]))
                                _conn.commit()
                                _conn.close()
                                st.rerun()

            if len(_reviewed) > 0:
                st.markdown(f"### Processed ({len(_reviewed)})")
                for _, inc in _reviewed.iterrows():
                    with st.container(border=True):
                        _status_icon = "✅" if inc["status"] == "Converted" else "❌"
                        st.markdown(f"{_status_icon} **{inc['worker_name']}** — {inc['status']} — {inc['date_of_incident']}")
                        if inc["converted_case_id"]:
                            st.caption(f"Converted to Case #{int(inc['converted_case_id'])}")


# ============================================================
# MANAGE USERS PAGE (admin only)
# ============================================================
elif page == "Manage Users":
    require_auth()
    if not user_has_role("admin"):
        st.error("You don't have permission to access this page.")
    else:
        st.title("👥 Manage Users")

        # Show existing users
        users = db.get_all_users()
        if users:
            st.markdown("### Current Users")
            _user_df = pd.DataFrame(users)
            _user_df["is_active"] = _user_df["is_active"].map({1: "✅ Active", 0: "❌ Inactive"})
            st.dataframe(_user_df[["username", "display_name", "role", "email", "entity", "site", "is_active"]],
                         use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### Add New User")

        with st.form("add_user_form"):
            _au1, _au2 = st.columns(2)
            with _au1:
                _new_username = st.text_input("Username *")
                _new_password = st.text_input("Password *", type="password")
                _new_display = st.text_input("Display Name *")
            with _au2:
                _new_role = st.selectbox("Role", ["manager", "viewer", "admin"])
                _new_email = st.text_input("Email")
                _new_entity = st.text_input("Entity (optional)")
            _new_site = st.text_input("Site (optional — restricts manager to this site)")

            st.markdown("")
            st.caption("**Roles:** Admin = full access | Manager = dashboard + incident reports + tracking | Viewer = read-only dashboard")

            if st.form_submit_button("Create User", type="primary"):
                if not _new_username or not _new_password or not _new_display:
                    st.error("Username, password, and display name are required.")
                else:
                    _uid = db.create_user(
                        _new_username.strip().lower(),
                        _new_password,
                        _new_display.strip(),
                        role=_new_role,
                        email=_new_email or None,
                        entity=_new_entity or None,
                        site=_new_site or None,
                    )
                    if _uid:
                        st.success(f"User '{_new_username}' created successfully!")
                        log_audit("create_user", "users", _uid, details=f"Created user {_new_username} with role {_new_role}")
                        st.rerun()
                    else:
                        st.error(f"Username '{_new_username}' already exists.")


# ============================================================
# NEW CASE PAGE (standalone — from sidebar button)
# ============================================================
elif page == "New Case":
    st.title("➕ New Case")

    # --- Step 1: Incident Report Upload ---
    st.markdown("#### Step 1: Upload Incident Report")
    st.caption("Upload a PDF or DOCX incident report to auto-fill the form below. Fields extracted from the report will be highlighted in green.")

    uploaded_file = st.file_uploader(
        "Drag & drop or browse",
        type=["pdf", "docx"],
        key="incident_upload"
    )

    if uploaded_file is not None and "prefill_data" not in st.session_state:
        file_bytes = uploaded_file.read()
        ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
        try:
            parsed = report_parser.parse_uploaded_report(file_bytes, ext)
            st.session_state.prefill_data = parsed
            st.session_state.has_incident_report = True
            if parsed:
                st.success(f"✅ Extracted {len(parsed)} field(s) from report!")
                # Show what was extracted
                with st.expander("View extracted fields", expanded=True):
                    for field, value in parsed.items():
                        st.markdown(f"**{field.replace('_', ' ').title()}:** {value}")
            else:
                st.warning("Could not extract fields from the uploaded file. Please fill in the form manually.")
        except Exception as e:
            st.error(f"Error parsing file: {e}")
            st.session_state.prefill_data = {}

    elif uploaded_file is not None and "prefill_data" in st.session_state:
        pre_display = st.session_state.get("prefill_data", {})
        if pre_display:
            with st.expander("View extracted fields"):
                for field, value in pre_display.items():
                    st.markdown(f"**{field.replace('_', ' ').title()}:** {value}")

    pre = st.session_state.get("prefill_data", {})
    has_report = st.session_state.get("has_incident_report", False)

    if pre:
        if st.button("🔄 Clear pre-filled data & re-upload"):
            st.session_state.pop("prefill_data", None)
            st.session_state.pop("has_incident_report", None)
            st.rerun()

    st.divider()

    # --- Step 2: Case Details Form ---
    st.markdown("#### Step 2: Review & Complete Case Details")
    if pre:
        st.caption("Fields marked with ✅ were auto-filled from the incident report. Please review and complete the remaining fields.")

    # Parse date of injury from prefill
    doi_value = None
    if pre.get("date_of_injury"):
        try:
            doi_value = datetime.strptime(pre["date_of_injury"], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            doi_value = None

    with st.form("new_case_wizard"):
        ac1, ac2 = st.columns(2)
        new_name = ac1.text_input(
            f"Worker Name*{' ✅' if pre.get('worker_name') else ''}",
            value=pre.get("worker_name", ""))
        new_state = ac2.selectbox("State*", ["VIC", "NSW", "QLD", "TAS", "SA", "WA"],
                                  index=["VIC", "NSW", "QLD", "TAS", "SA", "WA"].index(pre["state"]) if pre.get("state") in ["VIC", "NSW", "QLD", "TAS", "SA", "WA"] else 0)
        new_entity = ac1.text_input(
            f"Entity{' ✅' if pre.get('entity') else ''}",
            value=pre.get("entity", ""))
        pre_site = pre.get("site", "")
        site_idx = SITE_LIST.index(pre_site) if pre_site in SITE_LIST else 0
        new_site_sel = ac2.selectbox(
            f"Site{' ✅' if pre.get('site') else ''}",
            SITE_LIST, index=site_idx)
        new_site_other = ""
        if new_site_sel == "Other":
            new_site_other = ac2.text_input("Site (specify)", value=pre.get("site", ""))
        new_site = new_site_other if new_site_sel == "Other" else (new_site_sel if new_site_sel != "-- Select --" else "")
        new_email = ac1.text_input(
            f"Employee Email{' ✅' if pre.get('email') else ''}",
            value=pre.get("email", ""))
        new_phone = ac2.text_input(
            f"Employee Phone{' ✅' if pre.get('phone') else ''}",
            value=pre.get("phone", ""))
        new_doi = ac1.date_input(
            f"Date of Injury{' ✅' if doi_value else ''}",
            value=doi_value, format="DD/MM/YYYY")
        new_capacity = ac2.selectbox("Current Capacity",
                                     ["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"])
        injury_types = ["Manual Handling / Back", "Crush / Fracture", "Laceration / Cut",
                        "Sprain / Strain", "Chemical", "Disease / Illness", "Burns",
                        "Slip / Trip / Fall", "Psychological", "Other", "Unknown"]
        new_injury_type = ac1.selectbox("Injury Type", injury_types,
                                         index=injury_types.index(pre["injury_type"]) if pre.get("injury_type") in injury_types else len(injury_types) - 1)
        new_injury = st.text_area(
            f"Injury Description{' ✅' if pre.get('injury_description') else ''}",
            value=pre.get("injury_description", ""))
        new_shift = ac1.text_input(
            f"Shift Structure{' ✅' if pre.get('shift_structure') else ''}",
            value=pre.get("shift_structure", ""))
        new_piawe = ac2.number_input("PIAWE ($)", min_value=0.0, value=0.0, step=0.01)
        new_reduction = ac1.selectbox("Reduction Rate", ["95%", "80%", "N/A"])
        new_claim = ac2.text_input("Claim Number")
        new_priority = ac1.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"])
        new_strategy = st.text_area("Strategy")
        new_next = st.text_area("Next Action Required")
        new_notes = st.text_area("Notes")

        submitted = st.form_submit_button("Create Case", type="primary")
        if submitted and new_name:
            conn = db.get_connection()
            conn.execute("""
                INSERT INTO cases (worker_name, state, entity, site, date_of_injury,
                    injury_description, current_capacity, shift_structure, piawe,
                    reduction_rate, claim_number, priority, strategy, next_action, notes,
                    email, phone, injury_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_name, new_state, new_entity, new_site,
                  new_doi.isoformat() if new_doi else None,
                  new_injury, new_capacity, new_shift,
                  new_piawe if new_piawe > 0 else None,
                  new_reduction, new_claim or None, new_priority,
                  new_strategy, new_next, new_notes,
                  new_email or None, new_phone or None, new_injury_type))
            conn.commit()
            new_case_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Create document checklist — auto-mark incident report if uploaded
            doc_types = [
                "Incident Report", "Claim Form", "Payslips (12 months)",
                "PIAWE Calculation", "Certificate of Capacity (Current)",
                "RTW Plan (Current)", "Suitable Duties Plan", "Medical Certificates",
                "Insurance Correspondence", "Wage Records"
            ]
            for dt in doc_types:
                is_present = 1 if dt == "Incident Report" and has_report else 0
                conn.execute("INSERT INTO documents (case_id, doc_type, is_present) VALUES (?, ?, ?)",
                             (new_case_id, dt, is_present))
            conn.commit()
            conn.close()
            log_activity(new_case_id, "Case Created", f"New case added for {new_name}")

            # Generate Register of Injury for download
            incident_data = {
                "worker_name": new_name, "email": new_email, "phone": new_phone,
                "entity": new_entity, "site": new_site, "state": new_state,
                "date_of_injury": new_doi.isoformat() if new_doi else "",
                "injury_description": new_injury, "shift_structure": new_shift,
            }
            incident_data.update({k: v for k, v in pre.items() if k not in incident_data or not incident_data[k]})

            roi_bytes = doc_generator.generate_register_of_injury(incident_data)

            st.success(f"✅ Case created for {new_name}!")
            dl_col, nav_col = st.columns(2)
            dl_col.download_button(
                label="📥 Download Register of Injury",
                data=roi_bytes,
                file_name=f"Register_of_Injury_{new_name.replace(' ', '_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

            # Navigate to the new case
            st.session_state.pop("prefill_data", None)
            st.session_state.pop("has_incident_report", None)
            if nav_col.button("📂 Open Case Detail", type="primary"):
                st.session_state.selected_case_id = new_case_id
                st.session_state.prev_page = "Dashboard"
                st.session_state.page = "Case Detail"
                st.rerun()



# ============================================================
# CASE DETAIL PAGE
# ============================================================
elif page == "Case Detail":
    case_id = st.session_state.selected_case_id
    if case_id is None:
        st.warning("No case selected. Use the Back or Home button above.")
    else:
        # Fetch all data up front
        conn = db.get_connection()
        case_row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()

        if case_row is None:
            conn.close()
            st.error("Case not found.")
        else:
            case = row_to_dict(conn, "cases", case_row)

            # Fetch latest COC
            latest_coc_row = conn.execute(
                "SELECT * FROM certificates WHERE case_id = ? ORDER BY cert_to DESC LIMIT 1",
                (case_id,)
            ).fetchone()
            latest_coc = row_to_dict(conn, "certificates", latest_coc_row) if latest_coc_row else None

            # Fetch termination
            term_row = conn.execute(
                "SELECT * FROM terminations WHERE case_id = ?", (case_id,)
            ).fetchone()
            termination = row_to_dict(conn, "terminations", term_row) if term_row else None

            conn.close()

            # === HEADER ===
            back_col, spacer = st.columns([1, 5])
            if back_col.button("← Back to " + st.session_state.prev_page):
                st.session_state.page = st.session_state.prev_page
                st.rerun()

            st.title(case['worker_name'])
            cap_e = capacity_emoji(case["current_capacity"])
            pri_e = priority_emoji(case["priority"])
            st.caption(
                f"Case #{case['id']} · {case['state']} · "
                f"{case['entity'] or 'Unknown'} – {case['site'] or 'Unknown'} · "
                f"Status: {case['status']} · {pri_e} {case['priority']}"
            )

            # Key metrics row
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Capacity", f"{cap_e} {case['current_capacity']}")

            if latest_coc:
                coc_st, coc_col = coc_status(latest_coc['cert_to'])
                m2.metric("COC Status", coc_st)
            else:
                m2.metric("COC Status", "No COC")

            if case['piawe']:
                rate_str = case['reduction_rate']
                rate = 0.95 if rate_str == "95%" else (0.80 if rate_str == "80%" else 0)
                entitled = case['piawe'] * rate if rate else case['piawe']
                m3.metric("Entitlement", f"${entitled:,.2f}/wk",
                          delta=f"PIAWE ${case['piawe']:,.2f} @ {rate_str}")
            else:
                m3.metric("PIAWE", "Not recorded")

            if case['date_of_injury']:
                try:
                    doi = datetime.strptime(case['date_of_injury'], "%Y-%m-%d").date()
                    days = (date.today() - doi).days
                    m4.metric("Days Since Injury", f"{days}")
                except ValueError:
                    m4.metric("Days Since Injury", "N/A")
            else:
                m4.metric("Days Since Injury", "N/A")

            if case['claim_start_date']:
                try:
                    csd = datetime.strptime(case['claim_start_date'], "%Y-%m-%d").date()
                    weeks = (date.today() - csd).days // 7
                    m5.metric("Claim Duration", f"{weeks} weeks")
                except ValueError:
                    m5.metric("Claim Duration", "N/A")
            else:
                m5.metric("Claim Duration", "N/A")

            # Alert banners
            if latest_coc:
                s, c = coc_status(latest_coc['cert_to'])
                if c in ("red", "orange"):
                    st.warning(f"🚨 COC {s} — action required")
            else:
                st.warning("⚠️ No COC on record for this case")

            if termination and termination.get('status') == 'Pending':
                st.info(f"📋 Termination pending — {termination['termination_type']}")

            if not case['piawe'] and case['reduction_rate'] not in ('N/A', None):
                st.info("ℹ️ PIAWE not recorded — needed for payroll calculations")

            # Status toggle
            st.divider()
            _status_col1, _status_col2 = st.columns([6, 1])
            current_status = case.get("status", "Active")
            with _status_col2:
                if current_status == "Active":
                    if st.button("Mark Inactive", key="cd_mark_inactive"):
                        conn2 = db.get_connection()
                        conn2.execute("UPDATE cases SET status = 'Inactive' WHERE id = ?", (case_id,))
                        conn2.commit()
                        conn2.close()
                        log_activity(case_id, "Status Changed", f"Case marked as Inactive")
                        st.rerun()
                else:
                    if st.button("Mark Active", key="cd_mark_active"):
                        conn2 = db.get_connection()
                        conn2.execute("UPDATE cases SET status = 'Active' WHERE id = ?", (case_id,))
                        conn2.commit()
                        conn2.close()
                        log_activity(case_id, "Status Changed", f"Case marked as Active")
                        st.rerun()

            # === TABBED INTERFACE ===
            tab_overview, tab_coc, tab_payroll, tab_term, tab_docs, tab_edit, tab_log = st.tabs([
                "📋 Overview", "📄 Certificates", "💰 Payroll",
                "⚖️ Termination", "📁 Documents", "✏️ Edit Case", "📜 Activity"
            ])

            # --- Overview Tab ---
            with tab_overview:
                left, right = st.columns([1, 1])

                with left:
                    st.markdown("#### Case Details")
                    info_pairs = [
                        ("Entity", case['entity'] or 'N/A'),
                        ("Site", case['site'] or 'N/A'),
                        ("Injury Type", case.get('injury_type') or 'N/A'),
                        ("Date of Injury", case['date_of_injury'] or 'N/A'),
                        ("Claim Number", case['claim_number'] or 'N/A'),
                        ("Claim Start Date", case['claim_start_date'] or 'N/A'),
                        ("Current Capacity", f"{capacity_emoji(case['current_capacity'])} {case['current_capacity']}"),
                        ("Shift Structure", case['shift_structure'] or 'N/A'),
                        ("PIAWE", f"${case['piawe']:,.2f}" if case['piawe'] else 'Not recorded'),
                        ("Reduction Rate", case['reduction_rate'] or 'N/A'),
                    ]
                    for label, value in info_pairs:
                        st.markdown(f"**{label}:** {value}")

                    st.markdown("---")
                    st.markdown("#### Contact")
                    st.markdown(f"**Email:** {case['email'] or 'N/A'}")
                    st.markdown(f"**Phone:** {case['phone'] or 'N/A'}")

                with right:
                    st.markdown("#### Injury Description")
                    st.info(case['injury_description'] or 'N/A')

                    st.markdown("#### Strategy")
                    st.success(case['strategy'] or 'N/A')

                    st.markdown("#### Next Action Required")
                    st.warning(case['next_action'] or 'N/A')

                    st.markdown("#### Notes")
                    st.markdown(case['notes'] or '*No notes*')

                # Document downloads
                st.divider()
                dl1, dl2, dl3 = st.columns(3)
                injury_label = case.get("injury_type") or "General"
                worker_slug = case['worker_name'].replace(' ', '_')
                with dl1:
                    tbt_bytes = doc_generator.generate_toolbox_talk(case)
                    st.download_button(
                        label=f"Toolbox Talk ({injury_label})",
                        data=tbt_bytes,
                        file_name=f"Toolbox_Talk_{worker_slug}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
                with dl2:
                    coc_dict = dict(latest_coc) if latest_coc else None
                    rtw_bytes = doc_generator.generate_rtw_plan(case, coc_dict)
                    st.download_button(
                        label="RTW Plan",
                        data=rtw_bytes,
                        file_name=f"RTW_Plan_{worker_slug}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
                with dl3:
                    roi_bytes = doc_generator.generate_register_of_injury(case)
                    st.download_button(
                        label="Register of Injury",
                        data=roi_bytes,
                        file_name=f"Register_of_Injury_{worker_slug}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )

            # --- Certificates Tab ---
            with tab_coc:
                conn = db.get_connection()
                all_cocs = pd.read_sql_query(
                    "SELECT * FROM certificates WHERE case_id = ? ORDER BY cert_to DESC",
                    conn, params=(case_id,)
                )
                conn.close()

                # Latest COC summary
                if len(all_cocs) > 0:
                    latest = all_cocs.iloc[0]
                    status_text, color = coc_status(latest['cert_to'])
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Current Status", status_text)
                        c2.metric("Capacity", latest['capacity'] or 'N/A')
                        c3.metric("Valid From", latest['cert_from'])
                        c4.metric("Valid To", latest['cert_to'])
                        if latest['days_per_week'] or latest['hours_per_day']:
                            st.caption(f"Schedule: {latest['days_per_week'] or '?'} days/week, "
                                      f"{latest['hours_per_day'] or '?'} hrs/day")
                else:
                    st.warning("No certificates of capacity on record.")

                st.divider()

                # COC History
                st.markdown("#### Certificate History")
                if len(all_cocs) > 0:
                    display_df = all_cocs.copy()
                    display_df['status'] = display_df['cert_to'].apply(lambda x: coc_status(x)[0])
                    st.dataframe(
                        display_df[['cert_from', 'cert_to', 'capacity', 'days_per_week',
                                    'hours_per_day', 'status', 'notes']],
                        use_container_width=True, hide_index=True,
                        column_config={
                            "cert_from": "From", "cert_to": "To",
                            "capacity": "Capacity", "days_per_week": "Days/Week",
                            "hours_per_day": "Hours/Day", "status": "Status", "notes": "Notes",
                        }
                    )
                    st.caption(f"Total certificates on record: {len(all_cocs)}")
                else:
                    st.info("No certificate history.")

                st.divider()

                # Add New COC — Upload or Manual
                st.markdown("#### Add New Certificate")
                add_method = st.radio("How would you like to add?",
                    ["Upload COC PDF", "Enter manually"], horizontal=True, key="cd_coc_method")

                if add_method == "Upload COC PDF":
                    coc_upload = st.file_uploader("Upload Certificate of Capacity PDF",
                        type=["pdf"], key=f"cd_coc_upload_{case_id}")

                    coc_pre = st.session_state.get("coc_prefill", {})

                    if coc_upload is not None and "coc_prefill" not in st.session_state:
                        coc_bytes = coc_upload.read()
                        st.session_state["coc_upload_bytes"] = coc_bytes
                        st.session_state["coc_upload_name"] = coc_upload.name
                        with st.spinner("Scanning COC with OCR... this may take a moment"):
                            try:
                                parsed = coc_parser.parse_coc_pdf(coc_bytes, coc_upload.name)
                                st.session_state["coc_prefill"] = parsed
                                coc_pre = parsed
                                extracted = {k: v for k, v in parsed.items()
                                             if not k.startswith("_") and k != "template" and v}
                                if extracted:
                                    st.success(f"✅ Extracted {len(extracted)} field(s) from COC!")
                                    with st.expander("View extracted fields", expanded=True):
                                        for field, value in extracted.items():
                                            st.markdown(f"**{field.replace('_', ' ').title()}:** {value}")
                                else:
                                    st.warning("Could not extract fields from OCR. Please fill in manually below.")
                            except Exception as e:
                                st.error(f"Error parsing COC: {e}")
                                st.session_state["coc_prefill"] = {}
                                coc_pre = {}

                    elif coc_upload is not None and coc_pre:
                        extracted = {k: v for k, v in coc_pre.items()
                                     if not k.startswith("_") and k != "template" and v}
                        if extracted:
                            with st.expander("View extracted fields"):
                                for field, value in extracted.items():
                                    st.markdown(f"**{field.replace('_', ' ').title()}:** {value}")

                    if coc_pre:
                        if st.button("🔄 Clear & re-upload", key="cd_coc_clear"):
                            st.session_state.pop("coc_prefill", None)
                            st.session_state.pop("coc_upload_bytes", None)
                            st.session_state.pop("coc_upload_name", None)
                            st.rerun()

                    # Pre-fill dates from parser
                    coc_from_val = None
                    coc_to_val = None
                    if coc_pre.get("cert_from"):
                        try:
                            coc_from_val = datetime.strptime(coc_pre["cert_from"], "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            pass
                    if coc_pre.get("cert_to"):
                        try:
                            coc_to_val = datetime.strptime(coc_pre["cert_to"], "%Y-%m-%d").date()
                        except (ValueError, TypeError):
                            pass

                    cap_options = ["No Capacity", "Modified Duties", "Full Capacity", "Clearance"]
                    cap_idx = 0
                    if coc_pre.get("capacity") in cap_options:
                        cap_idx = cap_options.index(coc_pre["capacity"])

                    with st.form("cd_add_coc_upload"):
                        st.caption("Review and confirm the extracted details below:")
                        cc1, cc2 = st.columns(2)
                        coc_from = cc1.date_input(f"Certificate From{' ✅' if coc_from_val else ''}",
                            value=coc_from_val, key="cd_coc_from_u")
                        coc_to = cc2.date_input(f"Certificate To{' ✅' if coc_to_val else ''}",
                            value=coc_to_val, key="cd_coc_to_u")
                        coc_capacity = st.selectbox(f"Capacity{' ✅' if coc_pre.get('capacity') else ''}",
                            cap_options, index=cap_idx, key="cd_coc_cap_u")
                        cc1b, cc2b = st.columns(2)
                        coc_days = cc1b.number_input("Days Per Week", min_value=0, max_value=7,
                            value=int(coc_pre.get("days_per_week", 0) or 0), key="cd_coc_days_u")
                        coc_hours = cc2b.number_input("Hours Per Day", min_value=0.0, max_value=24.0,
                            value=float(coc_pre.get("hours_per_day", 0.0) or 0.0), step=0.5, key="cd_coc_hours_u")
                        coc_notes = st.text_area("Notes",
                            value=coc_pre.get("diagnosis", ""), key="cd_coc_notes_u")

                        if st.form_submit_button("Save Certificate", type="primary"):
                            conn = db.get_connection()
                            conn.execute("""
                                INSERT INTO certificates (case_id, cert_from, cert_to, capacity,
                                                         days_per_week, hours_per_day, notes)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (case_id, coc_from.isoformat(), coc_to.isoformat(),
                                  coc_capacity, coc_days if coc_days > 0 else None,
                                  coc_hours if coc_hours > 0 else None, coc_notes))
                            conn.commit()
                            conn.execute(
                                "UPDATE cases SET current_capacity=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                (coc_capacity, case_id))
                            conn.commit()
                            conn.close()

                            # Save PDF to OneDrive folder
                            coc_bytes = st.session_state.get("coc_upload_bytes")
                            coc_name = st.session_state.get("coc_upload_name", "COC.pdf")
                            if coc_bytes:
                                saved_path = save_coc_to_onedrive(case['worker_name'], coc_bytes, coc_name)
                                if saved_path:
                                    mark_coc_processed(saved_path, case_id)

                            # Mark COC document as present
                            conn2 = db.get_connection()
                            conn2.execute(
                                "UPDATE documents SET is_present=1 WHERE case_id=? AND doc_type LIKE '%Certificate of Capacity%'",
                                (case_id,))
                            conn2.commit()
                            conn2.close()

                            log_activity(case_id, "COC Added (Upload)",
                                        f"COC {coc_from} to {coc_to} — {coc_capacity}. Saved to OneDrive.")
                            st.session_state.pop("coc_prefill", None)
                            st.session_state.pop("coc_upload_bytes", None)
                            st.session_state.pop("coc_upload_name", None)
                            st.success("✅ Certificate added and saved to OneDrive!")
                            st.rerun()

                else:
                    # Manual entry
                    with st.form("cd_add_coc"):
                        cc1, cc2 = st.columns(2)
                        coc_from = cc1.date_input("Certificate From", key="cd_coc_from")
                        coc_to = cc2.date_input("Certificate To", key="cd_coc_to")
                        coc_capacity = st.selectbox("Capacity",
                            ["No Capacity", "Modified Duties", "Full Capacity", "Clearance"],
                            key="cd_coc_cap")
                        cc1b, cc2b = st.columns(2)
                        coc_days = cc1b.number_input("Days Per Week", min_value=0, max_value=7,
                                                      value=0, key="cd_coc_days")
                        coc_hours = cc2b.number_input("Hours Per Day", min_value=0.0, max_value=24.0,
                                                       value=0.0, step=0.5, key="cd_coc_hours")
                        coc_notes = st.text_area("Notes", key="cd_coc_notes")

                        if st.form_submit_button("Add Certificate", type="primary"):
                            conn = db.get_connection()
                            conn.execute("""
                                INSERT INTO certificates (case_id, cert_from, cert_to, capacity,
                                                         days_per_week, hours_per_day, notes)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (case_id, coc_from.isoformat(), coc_to.isoformat(),
                                  coc_capacity, coc_days if coc_days > 0 else None,
                                  coc_hours if coc_hours > 0 else None, coc_notes))
                            conn.commit()
                            conn.execute(
                                "UPDATE cases SET current_capacity=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                (coc_capacity, case_id))
                            conn.commit()
                            conn.close()
                            log_activity(case_id, "COC Added",
                                        f"New COC {coc_from} to {coc_to} — {coc_capacity}")
                            st.success("Certificate added!")
                            st.rerun()

            # --- Payroll Tab ---
            with tab_payroll:
                conn = db.get_connection()
                payroll = pd.read_sql_query(
                    "SELECT * FROM payroll_entries WHERE case_id = ? ORDER BY period_to DESC",
                    conn, params=(case_id,)
                )
                conn.close()

                # Financial summary
                st.markdown("#### Financial Summary")
                if len(payroll) > 0:
                    total_compensation = payroll['compensation_payable'].sum()
                    total_wages = payroll['estimated_wages'].sum()
                    total_topup = payroll['top_up'].sum()
                    total_paid = payroll['total_payable'].sum()
                    total_backpay = payroll['back_pay_expenses'].sum()

                    fm1, fm2, fm3, fm4, fm5 = st.columns(5)
                    fm1.metric("Total Compensation", f"${total_compensation:,.2f}")
                    fm2.metric("Total Wages", f"${total_wages:,.2f}")
                    fm3.metric("Total Top-ups", f"${total_topup:,.2f}")
                    fm4.metric("Back-pay & Expenses", f"${total_backpay:,.2f}")
                    fm5.metric("Total Paid", f"${total_paid:,.2f}")
                else:
                    st.info("No payroll entries recorded.")
                    if case['piawe']:
                        st.markdown(f"**PIAWE:** ${case['piawe']:,.2f} | **Reduction Rate:** {case['reduction_rate']}")

                st.divider()

                # Payroll history
                st.markdown("#### Payroll History")
                if len(payroll) > 0:
                    st.dataframe(
                        payroll[['period_from', 'period_to', 'piawe', 'reduction_rate',
                                 'days_off', 'hours_worked', 'estimated_wages',
                                 'compensation_payable', 'top_up', 'back_pay_expenses',
                                 'total_payable', 'notes']],
                        use_container_width=True, hide_index=True,
                        column_config={
                            "period_from": "From", "period_to": "To",
                            "piawe": st.column_config.NumberColumn("PIAWE", format="$%.2f"),
                            "reduction_rate": st.column_config.NumberColumn("Rate", format="%.0f%%"),
                            "days_off": "Days Off", "hours_worked": "Hours Worked",
                            "estimated_wages": st.column_config.NumberColumn("Wages", format="$%.2f"),
                            "compensation_payable": st.column_config.NumberColumn("Compensation", format="$%.2f"),
                            "top_up": st.column_config.NumberColumn("Top-up", format="$%.2f"),
                            "back_pay_expenses": st.column_config.NumberColumn("Back-pay", format="$%.2f"),
                            "total_payable": st.column_config.NumberColumn("Total", format="$%.2f"),
                        }
                    )

                st.divider()

                # Add payroll entry
                st.markdown("#### Add Pay Period Entry")
                with st.form("cd_payroll_entry"):
                    pe1, pe2 = st.columns(2)
                    pay_from = pe1.date_input("Period From", key="cd_pay_from")
                    pay_to = pe2.date_input("Period To", key="cd_pay_to")

                    default_piawe = float(case['piawe']) if case['piawe'] else 0.0
                    default_rate = 0.95 if case['reduction_rate'] == "95%" else (
                        0.80 if case['reduction_rate'] == "80%" else 0.0)

                    pe3, pe4 = st.columns(2)
                    pay_piawe = pe3.number_input("PIAWE", value=default_piawe, step=0.01, key="cd_pay_piawe")
                    pay_rate = pe4.number_input("Reduction Rate", value=default_rate,
                                                 min_value=0.0, max_value=1.0, step=0.05, key="cd_pay_rate")
                    pay_days = pe3.number_input("Days Off", min_value=0, value=0, key="cd_pay_days")
                    pay_hours = pe4.number_input("Hours Worked", min_value=0.0, value=0.0,
                                                  step=0.5, key="cd_pay_hours")
                    pay_wages = pe3.number_input("Estimated Wages", min_value=0.0, value=0.0,
                                                  step=0.01, key="cd_pay_wages")
                    pay_backpay = pe4.number_input("Back-pay & Expenses", min_value=0.0, value=0.0,
                                                    step=0.01, key="cd_pay_backpay")
                    pay_notes = st.text_area("Notes", key="cd_pay_notes")

                    if st.form_submit_button("Calculate & Save", type="primary"):
                        entitled = pay_piawe * pay_rate
                        if pay_wages > 0:
                            top_up = max(0, entitled - pay_wages)
                            compensation = top_up
                        else:
                            daily = entitled / 5 if entitled > 0 else 0
                            compensation = daily * pay_days
                            top_up = 0
                        total = pay_wages + compensation + pay_backpay

                        conn = db.get_connection()
                        conn.execute("""
                            INSERT INTO payroll_entries (case_id, period_from, period_to, piawe,
                                reduction_rate, days_off, hours_worked, estimated_wages,
                                compensation_payable, top_up, back_pay_expenses, total_payable, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (case_id, pay_from.isoformat(), pay_to.isoformat(), pay_piawe,
                              pay_rate, pay_days, pay_hours, pay_wages, compensation, top_up,
                              pay_backpay, total, pay_notes))
                        conn.commit()
                        conn.close()
                        log_activity(case_id, "Payroll Entry",
                                    f"Period {pay_from} to {pay_to}: Total ${total:,.2f}")
                        st.success(f"Saved! Compensation: ${compensation:,.2f} | Total: ${total:,.2f}")
                        st.rerun()

            # --- Termination Tab ---
            with tab_term:
                if termination:
                    t = termination
                    st.markdown("#### Termination Status")
                    with st.container(border=True):
                        tc1, tc2, tc3 = st.columns(3)
                        tc1.metric("Status", t['status'])
                        tc2.metric("Type", t['termination_type'])
                        tc3.metric("Assigned To", t['assigned_to'] or 'N/A')
                        st.markdown(f"**Approved by:** {t['approved_by']} on {t['approved_date']}")
                        if t.get('completed_date'):
                            st.markdown(f"**Completed:** {t['completed_date']}")

                    # Progress
                    st.markdown("#### Progress")
                    steps = {
                        "Letter Drafted": bool(t['letter_drafted']),
                        "Letter Sent": bool(t['letter_sent']),
                        "Response Received": bool(t['response_received']),
                    }
                    progress = sum(steps.values())
                    st.progress(progress / 3, text=f"Progress: {progress}/3 steps completed")
                    for step_name, done in steps.items():
                        icon = "✅" if done else "⬜"
                        st.markdown(f"{icon} {step_name}")

                    if t.get('notes'):
                        st.markdown(f"**Notes:** {t['notes']}")

                    st.divider()

                    # Update form
                    st.markdown("#### Update Termination Progress")
                    with st.form("cd_update_termination"):
                        ut1, ut2 = st.columns(2)
                        u_status = ut1.selectbox("Status",
                            ["Pending", "In Progress", "Completed", "Cancelled"],
                            index=["Pending", "In Progress", "Completed", "Cancelled"].index(t['status'])
                                if t['status'] in ["Pending", "In Progress", "Completed", "Cancelled"] else 0,
                            key="cd_term_status")
                        u_drafted = ut1.checkbox("Letter Drafted", value=bool(t['letter_drafted']),
                                                  key="cd_term_drafted")
                        u_sent = ut2.checkbox("Letter Sent", value=bool(t['letter_sent']),
                                               key="cd_term_sent")
                        u_response = ut2.checkbox("Response Received", value=bool(t['response_received']),
                                                   key="cd_term_response")
                        u_notes = st.text_area("Notes", value=t.get('notes') or "", key="cd_term_notes")

                        if st.form_submit_button("Update Termination", type="primary"):
                            conn = db.get_connection()
                            conn.execute("""
                                UPDATE terminations SET status=?, letter_drafted=?, letter_sent=?,
                                    response_received=?, notes=?, completed_date=?
                                WHERE id=?
                            """, (u_status, int(u_drafted), int(u_sent), int(u_response), u_notes,
                                  date.today().isoformat() if u_status == "Completed" else None,
                                  int(t['id'])))
                            conn.commit()
                            conn.close()
                            log_activity(case_id, "Termination Updated", f"Status: {u_status}")
                            st.success("Termination updated!")
                            st.rerun()
                else:
                    st.info("No termination has been initiated for this case.")

                    st.markdown("#### Initiate Termination")
                    with st.form("cd_initiate_termination"):
                        term_type = st.selectbox("Termination Type",
                            ["Inherent Requirements", "Show Cause",
                             "Show Cause / Inherent Requirements", "Loss of Contract", "Other"],
                            key="cd_new_term_type")
                        t1, t2 = st.columns(2)
                        approved_by = t1.text_input("Approved By", key="cd_new_term_approved")
                        assigned_to = t2.text_input("Assigned To", key="cd_new_term_assigned")
                        term_notes = st.text_area("Notes", key="cd_new_term_notes")

                        if st.form_submit_button("Initiate Termination", type="primary"):
                            conn = db.get_connection()
                            conn.execute("""
                                INSERT INTO terminations (case_id, termination_type, approved_by,
                                                         approved_date, assigned_to, notes)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (case_id, term_type, approved_by,
                                  date.today().isoformat(), assigned_to, term_notes))
                            conn.commit()
                            conn.close()
                            log_activity(case_id, "Termination Initiated",
                                        f"Type: {term_type}, Assigned to: {assigned_to}")
                            st.success("Termination initiated!")
                            st.rerun()

            # --- Documents Tab ---
            with tab_docs:
                docs = get_documents(case_id)
                if len(docs) > 0:
                    present = len(docs[docs['is_present'] == 1])
                    total = len(docs)
                    st.progress(present / total, text=f"Documents: {present}/{total} complete")

                    doc_cols = st.columns(5)
                    for i, (_, doc) in enumerate(docs.iterrows()):
                        col_idx = i % 5
                        check = "✅" if doc["is_present"] else "❌"
                        doc_cols[col_idx].markdown(f"{check} {doc['doc_type']}")

                    st.divider()
                    st.markdown("#### Update Checklist")
                    doc_changes = {}
                    dcols = st.columns(2)
                    for i, (_, doc) in enumerate(docs.iterrows()):
                        col = dcols[i % 2]
                        doc_changes[doc["id"]] = col.checkbox(
                            doc["doc_type"], value=bool(doc["is_present"]),
                            key=f"cd_doc_{doc['id']}")

                    if st.button("Save Document Checklist", key="cd_save_docs", type="primary"):
                        conn = db.get_connection()
                        for doc_id, present_val in doc_changes.items():
                            conn.execute("UPDATE documents SET is_present=? WHERE id=?",
                                       (int(present_val), int(doc_id)))
                        conn.commit()
                        conn.close()
                        log_activity(case_id, "Documents Updated",
                                    f"Document checklist updated for {case['worker_name']}")
                        st.success("Document checklist saved!")
                        st.rerun()
                else:
                    st.info("No document checklist for this case.")

            # --- Edit Case Tab ---
            with tab_edit:
                with st.form("cd_edit_case"):
                    ec1, ec2 = st.columns(2)
                    edit_entity = ec1.text_input("Entity", value=case["entity"] or "")
                    edit_site = ec2.text_input("Site", value=case["site"] or "")
                    injury_types = ["Manual Handling / Back", "Crush / Fracture", "Laceration / Cut",
                                    "Sprain / Strain", "Chemical", "Disease / Illness", "Burns",
                                    "Slip / Trip / Fall", "Psychological", "Other", "Unknown"]
                    edit_injury_type = ec1.selectbox("Injury Type", injury_types,
                        index=injury_types.index(case.get("injury_type")) if case.get("injury_type") in injury_types else len(injury_types) - 1
                    )
                    edit_capacity = ec2.selectbox("Current Capacity",
                        ["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"],
                        index=["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"].index(case["current_capacity"]) if case["current_capacity"] in ["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"] else 4
                    )
                    edit_shift = ec1.text_input("Shift Structure", value=case["shift_structure"] or "")
                    edit_piawe = ec1.number_input("PIAWE ($)", min_value=0.0,
                        value=float(case["piawe"]) if case["piawe"] else 0.0, step=0.01)
                    edit_reduction = ec2.selectbox("Reduction Rate", ["95%", "80%", "N/A"],
                        index=["95%", "80%", "N/A"].index(case["reduction_rate"]) if case["reduction_rate"] in ["95%", "80%", "N/A"] else 2
                    )
                    priorities = ["HIGH", "MEDIUM", "LOW"]
                    edit_priority = ec1.selectbox("Priority", priorities,
                        index=priorities.index(case["priority"]) if case["priority"] in priorities else 1
                    )
                    statuses = ["Active", "Closed", "Pending Closure"]
                    edit_status = ec2.selectbox("Status", statuses,
                        index=statuses.index(case["status"]) if case["status"] in statuses else 0
                    )
                    edit_email = ec1.text_input("Email", value=case["email"] or "")
                    edit_phone = ec2.text_input("Phone", value=case["phone"] or "")
                    edit_strategy = st.text_area("Strategy", value=case["strategy"] or "")
                    edit_next = st.text_area("Next Action", value=case["next_action"] or "")
                    edit_notes = st.text_area("Notes", value=case["notes"] or "")

                    save = st.form_submit_button("Save Changes", type="primary")
                    if save:
                        conn = db.get_connection()
                        conn.execute("""
                            UPDATE cases SET entity=?, site=?, injury_type=?,
                                current_capacity=?, shift_structure=?, piawe=?,
                                reduction_rate=?, priority=?, status=?, strategy=?,
                                next_action=?, notes=?, email=?, phone=?,
                                updated_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (edit_entity or None, edit_site or None, edit_injury_type,
                              edit_capacity, edit_shift,
                              edit_piawe if edit_piawe > 0 else None,
                              edit_reduction, edit_priority, edit_status,
                              edit_strategy, edit_next, edit_notes,
                              edit_email or None, edit_phone or None,
                              case_id))
                        conn.commit()
                        conn.close()
                        log_activity(case_id, "Case Updated", f"Updated details for {case['worker_name']}")
                        st.success("Case updated!")
                        st.rerun()

            # --- Activity Tab ---
            with tab_log:
                activity = get_activity_log(case_id=case_id, limit=50)
                if len(activity) > 0:
                    for _, entry in activity.iterrows():
                        with st.container(border=True):
                            lc1, lc2 = st.columns([1, 3])
                            lc1.caption(entry['created_at'][:16] if entry['created_at'] else '')
                            lc2.markdown(f"**{entry['action']}**: {entry['details'] or ''}")
                else:
                    st.info("No activity recorded for this case.")


# ============================================================
# DASHBOARD PAGE
# ============================================================
elif page == "Dashboard":
    # Title row with New Case button
    title_col, btn_col = st.columns([4, 1])
    title_col.title("ClaimTrack Pro — Dashboard")
    if btn_col.button("➕ New Case", type="primary", use_container_width=True):
        st.session_state.page = "New Case"
        st.rerun()

    cases_df = get_cases_df()
    active = cases_df[cases_df["status"] == "Active"]
    cocs = get_latest_cocs()
    terms = get_terminations()

    # Key metrics row — clickable
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    no_cap_count = len(active[active["current_capacity"] == "No Capacity"])
    mod_count = len(active[active["current_capacity"] == "Modified Duties"])
    pend_terms = terms[terms["status"] == "Pending"] if len(terms) > 0 else terms
    expired_count = 0
    for _, row in cocs.iterrows():
        status_str, _ = coc_status(row["cert_to"])
        if "EXPIRED" in status_str:
            expired_count += 1
    total_days_lost = sum(calculate_days_lost(row) for _, row in active.iterrows())

    with col1:
        if st.button(f"**Active Cases**\n\n### {len(active)}", key="metric_active", use_container_width=True):
            st.session_state.page = "All Cases"
            st.rerun()
    with col2:
        if st.button(f"**No Capacity**\n\n### {no_cap_count}", key="metric_nocap", use_container_width=True):
            st.session_state.page = "All Cases"
            st.session_state.metric_filter = "No Capacity"
            st.rerun()
    with col3:
        if st.button(f"**Modified Duties**\n\n### {mod_count}", key="metric_mod", use_container_width=True):
            st.session_state.page = "All Cases"
            st.session_state.metric_filter = "Modified Duties"
            st.rerun()
    with col4:
        if st.button(f"**Terminations Pending**\n\n### {len(pend_terms)}", key="metric_term", use_container_width=True):
            st.session_state.page = "Terminations"
            st.rerun()
    with col5:
        if st.button(f"**Expired COCs**\n\n### {expired_count}", key="metric_coc", use_container_width=True):
            st.session_state.page = "COC Tracker"
            st.rerun()
    with col6:
        st.button(f"**Days Lost**\n\n### {total_days_lost:,}", key="metric_dayslost", use_container_width=True, disabled=True)

    st.divider()

    # Alerts section
    st.subheader("Alerts & Actions Required")

    alerts = []

    # COC alerts
    for _, row in cocs.iterrows():
        status, color = coc_status(row["cert_to"])
        if color in ("red", "orange"):
            alerts.append({
                "type": "COC",
                "severity": "URGENT" if color == "red" else "WARNING",
                "worker": row["worker_name"],
                "case_id": int(row["case_id"]),
                "message": f"COC {status}",
                "action": "Obtain new Certificate of Capacity"
            })

    # Check for cases with no COC at all
    cases_with_coc = set(cocs["case_id"].tolist()) if len(cocs) > 0 else set()
    for _, case in active.iterrows():
        if case["id"] not in cases_with_coc and case["current_capacity"] not in ("Full Capacity",):
            alerts.append({
                "type": "COC",
                "severity": "WARNING",
                "worker": case["worker_name"],
                "case_id": int(case["id"]),
                "message": "No COC on record",
                "action": "Obtain Certificate of Capacity from insurer"
            })

    # Termination alerts
    for _, t in terms.iterrows():
        if t["status"] == "Pending":
            alerts.append({
                "type": "TERMINATION",
                "severity": "ACTION",
                "worker": t["worker_name"],
                "case_id": int(t["case_id"]),
                "message": f"Termination pending - {t['termination_type']}",
                "action": f"Follow up with {t['assigned_to']}"
            })

    # Missing PIAWE
    for _, case in active.iterrows():
        if pd.isna(case["piawe"]) and case["current_capacity"] not in ("Full Capacity",) and case["reduction_rate"] != "N/A":
            alerts.append({
                "type": "PAYROLL",
                "severity": "INFO",
                "worker": case["worker_name"],
                "case_id": int(case["id"]),
                "message": "PIAWE data missing",
                "action": "Obtain PIAWE from insurer for payroll calculation"
            })

    if alerts:
        for i, alert in enumerate(sorted(alerts, key=lambda x: {"URGENT": 0, "WARNING": 1, "ACTION": 2, "INFO": 3}[x["severity"]])):
            icon = {"URGENT": "🚨", "WARNING": "⚠️", "ACTION": "📋", "INFO": "ℹ️"}[alert["severity"]]
            _al, _ar = st.columns([3, 2])
            with _al:
                label = f"{icon}  {alert['severity']}  ·  **{alert['worker']}** - {alert['message']}"
                if st.button(label, key=f"alert_{i}_{alert.get('case_id', 0)}", use_container_width=True):
                    st.session_state.selected_case_id = alert.get("case_id")
                    st.session_state.prev_page = "Dashboard"
                    st.session_state.page = "Case Detail"
                    st.rerun()
            with _ar:
                st.markdown(f"<div style='padding:8px 0; font-size:0.85rem; color:#6C757D; text-align:right;'><em>{alert['action']}</em></div>", unsafe_allow_html=True)
    else:
        st.success("No alerts - all cases are up to date!")

    st.divider()

    # Cases by state
    st.subheader("Cases by State")
    col1, col2, col3 = st.columns(3)

    for col, state, color in [(col1, "VIC", "#D6E4F0"), (col2, "NSW", "#E2EFDA"), (col3, "QLD", "#FFF2CC")]:
        state_cases = active[active["state"] == state]
        with col:
            st.markdown(f"### {state} ({len(state_cases)})")
            for _, case in state_cases.iterrows():
                cap = capacity_emoji(case["current_capacity"])
                pri = priority_emoji(case["priority"])
                label = f"{pri} **{case['worker_name']}**\n\n{cap} {case['current_capacity']} · {case['site'] or 'Unknown'}"
                if st.button(label, key=f"dash_{case['id']}", use_container_width=True):
                    st.session_state.selected_case_id = int(case["id"])
                    st.session_state.prev_page = "Dashboard"
                    st.session_state.page = "Case Detail"
                    st.rerun()


# ============================================================
# ALL CASES PAGE
# ============================================================
elif page == "All Cases":
    st.title("All Cases")

    cases_df = get_cases_df()
    filtered = cases_df[
        (cases_df["state"].isin(filter_state)) &
        (cases_df["current_capacity"].isin(filter_capacity)) &
        (cases_df["priority"].isin(filter_priority))
    ]

    active_cases = filtered[filtered["status"] == "Active"]
    inactive_cases = filtered[filtered["status"] != "Active"]

    tab_view, tab_inactive, tab_add, tab_edit = st.tabs(["Active Cases", "Inactive Cases", "Add New Case", "Edit Case"])

    with tab_view:
        if len(active_cases) == 0:
            st.info("No active cases match the current filters.")
        for _, case in active_cases.iterrows():
            cap = capacity_emoji(case["current_capacity"])
            pri = priority_emoji(case["priority"])
            label = f"{pri} **{case['worker_name']}** · {case['state']} - {case['site'] or ''} | {cap} {case['current_capacity']} · {case['priority']}"
            if st.button(label, key=f"allcases_{case['id']}", use_container_width=True):
                st.session_state.selected_case_id = int(case["id"])
                st.session_state.prev_page = "All Cases"
                st.session_state.page = "Case Detail"
                st.rerun()

    with tab_inactive:
        if len(inactive_cases) == 0:
            st.info("No inactive cases.")
        for _, case in inactive_cases.iterrows():
            cap = capacity_emoji(case["current_capacity"])
            label = f"**{case['worker_name']}** · {case['state']} - {case['site'] or ''} | {cap} {case['current_capacity']}"
            if st.button(label, key=f"inactive_{case['id']}", use_container_width=True):
                st.session_state.selected_case_id = int(case["id"])
                st.session_state.prev_page = "All Cases"
                st.session_state.page = "Case Detail"
                st.rerun()

    with tab_add:
        st.subheader("Add New Case")
        st.info("Tip: Use the **+ New Case** button in the sidebar for the full wizard with incident report upload.")
        with st.form("add_case_form"):
            ac1, ac2 = st.columns(2)
            new_name = ac1.text_input("Worker Name*", key="ac_name")
            new_state = ac2.selectbox("State*", ["VIC", "NSW", "QLD", "TAS", "SA", "WA"], key="ac_state")
            new_entity = ac1.text_input("Entity", key="ac_entity")
            new_site_sel = ac2.selectbox("Site", SITE_LIST, key="ac_site")
            new_site_other = ""
            if new_site_sel == "Other":
                new_site_other = ac2.text_input("Site (specify)", key="ac_site_other")
            new_site = new_site_other if new_site_sel == "Other" else (new_site_sel if new_site_sel != "-- Select --" else "")
            new_email = ac1.text_input("Employee Email", key="ac_email")
            new_phone = ac2.text_input("Employee Phone", key="ac_phone")
            new_doi = ac1.date_input("Date of Injury", value=None, key="ac_doi", format="DD/MM/YYYY")
            new_capacity = ac2.selectbox("Current Capacity", ["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"], key="ac_cap")
            injury_types = ["Manual Handling / Back", "Crush / Fracture", "Laceration / Cut",
                            "Sprain / Strain", "Chemical", "Disease / Illness", "Burns",
                            "Slip / Trip / Fall", "Psychological", "Other", "Unknown"]
            new_injury_type = ac1.selectbox("Injury Type", injury_types, key="ac_injury_type")
            new_injury = st.text_area("Injury Description", key="ac_injury")
            new_shift = ac1.text_input("Shift Structure", key="ac_shift")
            new_piawe = ac2.number_input("PIAWE ($)", min_value=0.0, value=0.0, step=0.01, key="ac_piawe")
            new_reduction = ac1.selectbox("Reduction Rate", ["95%", "80%", "N/A"], key="ac_reduction")
            new_claim = ac2.text_input("Claim Number", key="ac_claim")
            new_priority = ac1.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"], key="ac_priority")
            new_strategy = st.text_area("Strategy", key="ac_strategy")
            new_next = st.text_area("Next Action Required", key="ac_next")
            new_notes = st.text_area("Notes", key="ac_notes")

            submitted = st.form_submit_button("Add Case")
            if submitted and new_name:
                conn = db.get_connection()
                conn.execute("""
                    INSERT INTO cases (worker_name, state, entity, site, date_of_injury,
                        injury_description, current_capacity, shift_structure, piawe,
                        reduction_rate, claim_number, priority, strategy, next_action, notes,
                        email, phone, injury_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (new_name, new_state, new_entity, new_site,
                      new_doi.isoformat() if new_doi else None,
                      new_injury, new_capacity, new_shift,
                      new_piawe if new_piawe > 0 else None,
                      new_reduction, new_claim or None, new_priority,
                      new_strategy, new_next, new_notes,
                      new_email or None, new_phone or None, new_injury_type))
                conn.commit()
                case_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                # Create document checklist
                doc_types = [
                    "Incident Report", "Claim Form", "Payslips (12 months)",
                    "PIAWE Calculation", "Certificate of Capacity (Current)",
                    "RTW Plan (Current)", "Suitable Duties Plan", "Medical Certificates",
                    "Insurance Correspondence", "Wage Records"
                ]
                for dt in doc_types:
                    conn.execute("INSERT INTO documents (case_id, doc_type) VALUES (?, ?)", (case_id, dt))
                conn.commit()
                conn.close()
                log_activity(case_id, "Case Created", f"New case added for {new_name}")
                st.success(f"Case added for {new_name}!")
                st.rerun()

    with tab_edit:
        st.subheader("Edit Case")
        cases_list = cases_df["worker_name"].tolist()
        selected_name = st.selectbox("Select Case to Edit", cases_list)
        if selected_name:
            case = cases_df[cases_df["worker_name"] == selected_name].iloc[0]
            with st.form("edit_case_form"):
                ec1, ec2 = st.columns(2)
                edit_entity_ac = ec1.text_input("Entity", value=case["entity"] or "", key="ec_entity")
                edit_site_ac = ec2.text_input("Site", value=case["site"] or "", key="ec_site")
                injury_types = ["Manual Handling / Back", "Crush / Fracture", "Laceration / Cut",
                                "Sprain / Strain", "Chemical", "Disease / Illness", "Burns",
                                "Slip / Trip / Fall", "Psychological", "Other", "Unknown"]
                edit_injury_type_ac = ec1.selectbox("Injury Type", injury_types,
                    index=injury_types.index(case.get("injury_type", "Unknown") or "Unknown") if (case.get("injury_type") or "Unknown") in injury_types else len(injury_types) - 1,
                    key="ec_injury_type"
                )
                edit_capacity = ec2.selectbox("Current Capacity",
                    ["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"],
                    index=["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"].index(case["current_capacity"]) if case["current_capacity"] in ["No Capacity", "Modified Duties", "Full Capacity", "Uncertain", "Unknown"] else 4
                )
                edit_shift = ec1.text_input("Shift Structure", value=case["shift_structure"] or "")
                edit_piawe = ec2.number_input("PIAWE ($)", min_value=0.0, value=float(case["piawe"]) if pd.notna(case["piawe"]) else 0.0, step=0.01)
                edit_reduction = ec1.selectbox("Reduction Rate", ["95%", "80%", "N/A"],
                    index=["95%", "80%", "N/A"].index(case["reduction_rate"]) if case["reduction_rate"] in ["95%", "80%", "N/A"] else 2
                )
                priorities = ["HIGH", "MEDIUM", "LOW"]
                edit_priority = ec2.selectbox("Priority", priorities,
                    index=priorities.index(case["priority"]) if case["priority"] in priorities else 1
                )
                statuses = ["Active", "Closed", "Pending Closure"]
                edit_status = ec1.selectbox("Status", statuses,
                    index=statuses.index(case["status"]) if case["status"] in statuses else 0
                )
                edit_strategy = st.text_area("Strategy", value=case["strategy"] or "")
                edit_next = st.text_area("Next Action", value=case["next_action"] or "")
                edit_notes = st.text_area("Notes", value=case["notes"] or "")

                save = st.form_submit_button("Save Changes")
                if save:
                    conn = db.get_connection()
                    conn.execute("""
                        UPDATE cases SET entity=?, site=?, injury_type=?,
                            current_capacity=?, shift_structure=?, piawe=?,
                            reduction_rate=?, priority=?, status=?, strategy=?,
                            next_action=?, notes=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (edit_entity_ac or None, edit_site_ac or None, edit_injury_type_ac,
                          edit_capacity, edit_shift,
                          edit_piawe if edit_piawe > 0 else None,
                          edit_reduction, edit_priority, edit_status,
                          edit_strategy, edit_next, edit_notes, int(case["id"])))
                    conn.commit()
                    conn.close()
                    log_activity(int(case["id"]), "Case Updated", f"Updated details for {selected_name}")
                    st.success("Case updated!")
                    st.rerun()

            # Document checklist update
            st.markdown("---")
            st.markdown("**Update Document Checklist:**")
            docs = get_documents(int(case["id"]))
            if len(docs) > 0:
                doc_changes = {}
                dcols = st.columns(2)
                for i, (_, doc) in enumerate(docs.iterrows()):
                    col = dcols[i % 2]
                    doc_changes[doc["id"]] = col.checkbox(
                        doc["doc_type"], value=bool(doc["is_present"]), key=f"doc_{doc['id']}"
                    )
                if st.button("Save Document Checklist"):
                    conn = db.get_connection()
                    for doc_id, present in doc_changes.items():
                        conn.execute("UPDATE documents SET is_present=? WHERE id=?", (int(present), int(doc_id)))
                    conn.commit()
                    conn.close()
                    log_activity(int(case["id"]), "Documents Updated", f"Document checklist updated for {selected_name}")
                    st.success("Document checklist saved!")
                    st.rerun()


# ============================================================
# INJURY ANALYTICS PAGE
# ============================================================
elif page == "Injury Analytics":
    st.title("Injury Type Analytics")
    st.caption("Breakdown of claims by injury type to identify focus areas for prevention and training.")

    cases_df = get_cases_df()
    active = cases_df[cases_df["status"] == "Active"]

    # Fill missing injury_type
    active = active.copy()
    active["injury_type"] = active["injury_type"].fillna("Unknown")

    # Summary metrics
    total_active = len(active)
    types_present = active["injury_type"].nunique()

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Total Active Claims", total_active)
    mc2.metric("Injury Categories", types_present)

    # Most common type
    type_counts = active["injury_type"].value_counts()
    if len(type_counts) > 0:
        mc3.metric("Most Common", type_counts.index[0], delta=f"{type_counts.iloc[0]} cases")

    # No capacity count
    no_cap = active[active["current_capacity"] == "No Capacity"]
    mc4.metric("No Capacity Cases", len(no_cap))

    st.divider()

    # --- Injury Type Breakdown ---
    tab_overview, tab_detail, tab_trends = st.tabs(["Overview", "Detailed Breakdown", "By State & Priority"])

    with tab_overview:
        st.markdown("#### Claims by Injury Type")

        # Build breakdown data
        type_summary = []
        for itype in type_counts.index:
            subset = active[active["injury_type"] == itype]
            no_cap_count = len(subset[subset["current_capacity"] == "No Capacity"])
            mod_count = len(subset[subset["current_capacity"] == "Modified Duties"])
            full_count = len(subset[subset["current_capacity"].isin(["Full Capacity"])])
            high_pri = len(subset[subset["priority"] == "HIGH"])
            type_summary.append({
                "Injury Type": itype,
                "Cases": len(subset),
                "% of Total": f"{len(subset)/total_active*100:.0f}%",
                "No Capacity": no_cap_count,
                "Modified": mod_count,
                "Full Capacity": full_count,
                "High Priority": high_pri,
            })

        summary_df = pd.DataFrame(type_summary)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        st.divider()

        # Visual bar chart using columns
        st.markdown("#### Distribution")
        max_count = type_counts.max() if len(type_counts) > 0 else 1
        for itype, count in type_counts.items():
            tc1, tc2, tc3 = st.columns([2, 4, 1])
            tc1.markdown(f"**{itype}**")
            tc2.progress(count / max_count)
            tc3.markdown(f"**{count}**")

    with tab_detail:
        st.markdown("#### Detailed Case List by Injury Type")

        # Selector for injury type
        selected_type = st.selectbox("Filter by Injury Type",
                                      ["All"] + list(type_counts.index))

        if selected_type == "All":
            display = active
        else:
            display = active[active["injury_type"] == selected_type]

        for _, case in display.iterrows():
            cap = capacity_emoji(case["current_capacity"])
            pri = priority_emoji(case["priority"])
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
                c1.markdown(f"{pri} **{case['worker_name']}**")
                c2.markdown(f"{cap} {case['current_capacity']} · {case['site'] or 'Unknown'}")
                c3.markdown(f"**{case['state']}**")
                c4.markdown(f"*{case.get('injury_type', 'Unknown')}*")

                if case["injury_description"]:
                    st.caption(case["injury_description"][:150])

    with tab_trends:
        st.markdown("#### Injury Types by State")

        # Cross-tabulation: state x injury type
        state_type = pd.crosstab(active["state"], active["injury_type"])
        if not state_type.empty:
            st.dataframe(state_type, use_container_width=True)
        else:
            st.info("No data available.")

        st.divider()

        st.markdown("#### Injury Types by Priority")
        pri_type = pd.crosstab(active["priority"], active["injury_type"])
        if not pri_type.empty:
            # Reindex to keep HIGH/MEDIUM/LOW order
            pri_order = [p for p in ["HIGH", "MEDIUM", "LOW"] if p in pri_type.index]
            pri_type = pri_type.reindex(pri_order)
            st.dataframe(pri_type, use_container_width=True)

        st.divider()

        st.markdown("#### Injury Types by Capacity Status")
        cap_type = pd.crosstab(active["current_capacity"], active["injury_type"])
        if not cap_type.empty:
            st.dataframe(cap_type, use_container_width=True)

        st.divider()

        # Key insights
        st.markdown("#### Key Insights")
        insights = []
        if len(type_counts) > 0:
            top_type = type_counts.index[0]
            top_count = type_counts.iloc[0]
            insights.append(f"**{top_type}** is the most common injury type with **{top_count}** active case(s) ({top_count/total_active*100:.0f}% of all claims).")

        # Types with most no-capacity
        for itype in type_counts.index:
            subset = active[active["injury_type"] == itype]
            nc = len(subset[subset["current_capacity"] == "No Capacity"])
            if nc > 0:
                insights.append(f"**{itype}**: {nc} case(s) with no capacity — focus area for return-to-work planning.")

        # Types with all high priority
        for itype in type_counts.index:
            subset = active[active["injury_type"] == itype]
            high = len(subset[subset["priority"] == "HIGH"])
            if high == len(subset) and len(subset) > 1:
                insights.append(f"**{itype}**: All {len(subset)} cases are HIGH priority.")

        if insights:
            for insight in insights:
                st.markdown(f"- {insight}")
        else:
            st.info("Not enough data for insights.")


# ============================================================
# SITE ANALYSIS PAGE
# ============================================================
elif page == "Site Analysis":
    st.title("Site-by-Site Analysis")
    st.caption("Performance and claims analysis for each work site.")

    cases_df = get_cases_df()
    active = cases_df[cases_df["status"] == "Active"]
    active = active.copy()
    active["site"] = active["site"].fillna("Unknown")
    active["injury_type"] = active["injury_type"].fillna("Unknown")
    cocs = get_latest_cocs()

    # Build site summary
    sites = active["site"].value_counts()
    total_sites = len(sites)
    total_claims = len(active)

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Active Sites", total_sites)
    mc2.metric("Total Active Claims", total_claims)
    if len(sites) > 0:
        mc3.metric("Most Claims", sites.index[0], delta=f"{sites.iloc[0]} cases")
        avg = total_claims / total_sites if total_sites > 0 else 0
        mc4.metric("Avg Claims/Site", f"{avg:.1f}")

    st.divider()

    tab_overview, tab_detail, tab_compare = st.tabs(["Site Overview", "Site Detail", "Comparison"])

    with tab_overview:
        st.markdown("#### Claims by Site")

        site_data = []
        for site_name in sites.index:
            subset = active[active["site"] == site_name]
            entity = subset["entity"].mode().iloc[0] if not subset["entity"].mode().empty else "N/A"
            states = ", ".join(sorted(subset["state"].unique()))
            no_cap = len(subset[subset["current_capacity"] == "No Capacity"])
            mod = len(subset[subset["current_capacity"] == "Modified Duties"])
            full = len(subset[subset["current_capacity"].isin(["Full Capacity"])])
            high = len(subset[subset["priority"] == "HIGH"])
            types = ", ".join(sorted(subset["injury_type"].unique()))

            site_data.append({
                "Site": site_name,
                "Entity": entity,
                "State": states,
                "Cases": len(subset),
                "No Capacity": no_cap,
                "Modified": mod,
                "Full": full,
                "HIGH Priority": high,
                "Injury Types": types,
            })

        site_df = pd.DataFrame(site_data)
        st.dataframe(site_df, use_container_width=True, hide_index=True)

        st.divider()

        # Visual breakdown
        st.markdown("#### Claims Distribution")
        max_count = sites.max() if len(sites) > 0 else 1
        for site_name, count in sites.items():
            sc1, sc2, sc3 = st.columns([2, 4, 1])
            sc1.markdown(f"**{site_name}**")
            sc2.progress(count / max_count)
            sc3.markdown(f"**{count}**")

    with tab_detail:
        st.markdown("#### Detailed Site View")

        selected_site = st.selectbox("Select Site", list(sites.index))
        if selected_site:
            subset = active[active["site"] == selected_site]

            # Site header metrics
            s1, s2, s3, s4, s5 = st.columns(5)
            s1.metric("Total Claims", len(subset))
            s2.metric("No Capacity", len(subset[subset["current_capacity"] == "No Capacity"]))
            s3.metric("Modified Duties", len(subset[subset["current_capacity"] == "Modified Duties"]))
            s4.metric("HIGH Priority", len(subset[subset["priority"] == "HIGH"]))

            # Average PIAWE for site
            piawe_vals = subset["piawe"].dropna()
            if len(piawe_vals) > 0:
                s5.metric("Avg PIAWE", f"${piawe_vals.mean():,.2f}")
            else:
                s5.metric("Avg PIAWE", "N/A")

            st.divider()

            # Injury type breakdown for this site
            st.markdown("##### Injury Types at This Site")
            site_types = subset["injury_type"].value_counts()
            for itype, count in site_types.items():
                st.markdown(f"- **{itype}**: {count} case(s)")

            st.divider()

            # Workers at this site
            st.markdown("##### Workers")
            for _, case in subset.iterrows():
                cap = capacity_emoji(case["current_capacity"])
                pri = priority_emoji(case["priority"])
                with st.container(border=True):
                    wc1, wc2, wc3 = st.columns([2, 2, 2])
                    wc1.markdown(f"{pri} **{case['worker_name']}**")
                    wc2.markdown(f"{cap} {case['current_capacity']}")
                    wc3.markdown(f"*{case.get('injury_type', 'Unknown')}*")
                    if case["injury_description"]:
                        st.caption(case["injury_description"][:120])

    with tab_compare:
        st.markdown("#### Site Comparison")

        # Cross-tabulation: site x capacity
        st.markdown("##### Cases by Site & Capacity")
        site_cap = pd.crosstab(active["site"], active["current_capacity"])
        if not site_cap.empty:
            st.dataframe(site_cap, use_container_width=True)

        st.divider()

        # Site x injury type
        st.markdown("##### Cases by Site & Injury Type")
        site_injury = pd.crosstab(active["site"], active["injury_type"])
        if not site_injury.empty:
            st.dataframe(site_injury, use_container_width=True)

        st.divider()

        # Site x priority
        st.markdown("##### Cases by Site & Priority")
        site_pri = pd.crosstab(active["site"], active["priority"])
        if not site_pri.empty:
            # Reorder columns
            pri_cols = [c for c in ["HIGH", "MEDIUM", "LOW"] if c in site_pri.columns]
            site_pri = site_pri[pri_cols]
            st.dataframe(site_pri, use_container_width=True)

        st.divider()

        # Risk assessment
        st.markdown("#### Site Risk Assessment")
        risk_data = []
        for site_name in sites.index:
            subset = active[active["site"] == site_name]
            total = len(subset)
            no_cap = len(subset[subset["current_capacity"] == "No Capacity"])
            high_pri = len(subset[subset["priority"] == "HIGH"])
            score = (total * 1) + (no_cap * 3) + (high_pri * 2)  # weighted risk score
            risk_level = "HIGH" if score >= 8 else ("MEDIUM" if score >= 4 else "LOW")
            risk_emoji = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟢"}[risk_level]

            risk_data.append({
                "Site": site_name,
                "Claims": total,
                "No Capacity": no_cap,
                "High Priority": high_pri,
                "Risk Score": score,
                "Risk Level": f"{risk_emoji} {risk_level}",
            })

        risk_df = pd.DataFrame(risk_data).sort_values("Risk Score", ascending=False)
        st.dataframe(risk_df, use_container_width=True, hide_index=True)


# ============================================================
# COC TRACKER PAGE
# ============================================================
elif page == "COC Tracker":
    st.title("Certificate of Capacity Tracker")

    cocs = get_latest_cocs()
    cases_df = get_cases_df()

    # Summary metrics
    today = date.today()
    expired = 0
    expiring = 0
    current = 0

    for _, row in cocs.iterrows():
        status, color = coc_status(row["cert_to"])
        if color == "red":
            expired += 1
        elif color == "orange":
            expiring += 1
        elif color == "green":
            current += 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total COCs Tracked", len(cocs))
    c2.metric("Current", current)
    c3.metric("Expiring Soon", expiring, delta="within 7 days", delta_color="inverse")
    c4.metric("Expired", expired, delta=f"{expired} overdue", delta_color="inverse")

    st.divider()

    tab_view, tab_add, tab_scan = st.tabs(["COC Status", "Add New COC", "Scan OneDrive Folders"])

    with tab_view:
        st.subheader("Certificate Status (sorted by expiry)")
        for _, row in cocs.iterrows():
            status, color = coc_status(row["cert_to"])
            emoji = coc_status_emoji(color)

            with st.container(border=True):
                cc1, cc2, cc3, cc4 = st.columns([2, 2, 2, 2])
                cc1.markdown(f"{emoji} **{row['worker_name']}**")
                cc2.markdown(f"**Period:** {row['cert_from']} to {row['cert_to']}")
                cc3.markdown(f"**Capacity:** {row['capacity'] or 'N/A'}")
                cc4.markdown(f"**Status:** {status}")

                if row["days_per_week"] or row["hours_per_day"]:
                    st.caption(f"Schedule: {row['days_per_week'] or '?'} days/week, {row['hours_per_day'] or '?'} hrs/day")

    with tab_add:
        st.subheader("Add New Certificate of Capacity")
        with st.form("add_coc_form"):
            active_cases = cases_df[cases_df["status"] == "Active"]
            case_options = {f"{r['worker_name']} ({r['state']})": r["id"] for _, r in active_cases.iterrows()}
            selected_case = st.selectbox("Worker", list(case_options.keys()))

            cc1, cc2 = st.columns(2)
            coc_from = cc1.date_input("Certificate From")
            coc_to = cc2.date_input("Certificate To")
            coc_capacity = st.selectbox("Capacity", ["No Capacity", "Modified Duties", "Full Capacity", "Clearance"])
            cc1b, cc2b = st.columns(2)
            coc_days = cc1b.number_input("Days Per Week", min_value=0, max_value=7, value=0)
            coc_hours = cc2b.number_input("Hours Per Day", min_value=0.0, max_value=24.0, value=0.0, step=0.5)
            coc_notes = st.text_area("Notes")

            add_coc = st.form_submit_button("Add Certificate")
            if add_coc and selected_case:
                case_id = case_options[selected_case]
                conn = db.get_connection()
                conn.execute("""
                    INSERT INTO certificates (case_id, cert_from, cert_to, capacity, days_per_week, hours_per_day, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (case_id, coc_from.isoformat(), coc_to.isoformat(),
                      coc_capacity, coc_days if coc_days > 0 else None,
                      coc_hours if coc_hours > 0 else None, coc_notes))
                conn.commit()

                # Also update the case's current capacity
                conn.execute("UPDATE cases SET current_capacity=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                             (coc_capacity, case_id))
                conn.commit()
                conn.close()

                worker_name = selected_case.split(" (")[0]
                log_activity(case_id, "COC Added", f"New COC {coc_from} to {coc_to} - {coc_capacity}")
                st.success(f"Certificate added for {worker_name}!")
                st.rerun()

    with tab_scan:
        st.subheader("Auto-Detect COCs from OneDrive Folders")
        st.caption("Scans Active Cases folders for new COC PDFs that haven't been added to the system yet.")

        if st.button("🔍 Scan for New COCs", type="primary"):
            with st.spinner("Scanning Active Cases folders..."):
                all_coc_files = coc_parser.scan_active_cases_for_cocs(ACTIVE_CASES_DIR)
                processed_paths = get_processed_coc_paths()
                new_files = [f for f in all_coc_files if f["file_path"] not in processed_paths]
                st.session_state["scan_results"] = new_files
                st.session_state["scan_total"] = len(all_coc_files)

        scan_results = st.session_state.get("scan_results", None)
        scan_total = st.session_state.get("scan_total", 0)

        if scan_results is not None:
            st.info(f"Found **{scan_total}** total COC files. **{len(scan_results)}** are new (not yet in system).")

            if len(scan_results) == 0:
                st.success("All COC files are already tracked in the system!")
            else:
                worker_names = get_worker_names_list()

                for i, file_info in enumerate(scan_results[:20]):  # Show max 20
                    fname = file_info["filename"]
                    folder = file_info["folder_name"]
                    fpath = file_info["file_path"]

                    # Try to match worker
                    matched_worker = coc_parser.match_worker_from_path(fpath, worker_names)

                    # Try to extract dates from filename
                    fn_dates = coc_parser._extract_dates_from_filename(fname)

                    with st.container(border=True):
                        fc1, fc2, fc3 = st.columns([3, 2, 1])
                        fc1.markdown(f"**{fname}**")
                        fc1.caption(f"Folder: {folder}")
                        if matched_worker:
                            fc2.markdown(f"Worker: **{matched_worker}**")
                        else:
                            fc2.markdown("Worker: *Unknown*")
                        if fn_dates.get("cert_from") and fn_dates.get("cert_to"):
                            fc2.caption(f"Dates: {fn_dates['cert_from']} to {fn_dates['cert_to']}")

                        # Quick-add button
                        if matched_worker and fn_dates.get("cert_from") and fn_dates.get("cert_to"):
                            if fc3.button("Quick Add", key=f"scan_add_{i}", type="primary"):
                                # Find case_id for this worker
                                conn = db.get_connection()
                                case_row = conn.execute(
                                    "SELECT id FROM cases WHERE worker_name = ?",
                                    (matched_worker,)).fetchone()
                                if case_row:
                                    matched_case_id = case_row[0]
                                    # Add certificate with filename dates
                                    conn.execute("""
                                        INSERT INTO certificates (case_id, cert_from, cert_to, capacity, notes)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, (matched_case_id, fn_dates["cert_from"], fn_dates["cert_to"],
                                          "Unknown", f"Auto-imported from: {fname}"))
                                    conn.commit()
                                    # Mark as processed
                                    conn.execute(
                                        "INSERT OR IGNORE INTO processed_coc_files (file_path, case_id) VALUES (?, ?)",
                                        (fpath, matched_case_id))
                                    conn.commit()
                                    # Update document checklist
                                    conn.execute(
                                        "UPDATE documents SET is_present=1 WHERE case_id=? AND doc_type LIKE '%Certificate%'",
                                        (matched_case_id,))
                                    conn.commit()
                                    conn.close()
                                    log_activity(matched_case_id, "COC Auto-Imported",
                                                f"From file: {fname}")
                                    st.success(f"Added for {matched_worker}!")
                                    # Remove from scan results
                                    scan_results.pop(i)
                                    st.session_state["scan_results"] = scan_results
                                    st.rerun()
                                else:
                                    conn.close()
                                    st.warning("Could not find matching case.")
                        else:
                            fc3.button("Review", key=f"scan_review_{i}", disabled=True,
                                       help="Worker or dates could not be determined. Add manually via Case Detail.")

                if len(scan_results) > 20:
                    st.caption(f"Showing first 20 of {len(scan_results)} new files.")


# ============================================================
# TERMINATIONS PAGE
# ============================================================
elif page == "Terminations":
    st.title("Termination Tracker")

    terms = get_terminations()
    cases_df = get_cases_df()

    pending = terms[terms["status"] == "Pending"]
    completed = terms[terms["status"] == "Completed"]

    c1, c2 = st.columns(2)
    c1.metric("Pending Terminations", len(pending))
    c2.metric("Completed", len(completed))

    st.divider()

    tab_pending, tab_add, tab_update = st.tabs(["Pending", "Initiate Termination", "Update Progress"])

    with tab_pending:
        if len(pending) == 0:
            st.info("No pending terminations")
        for _, t in pending.iterrows():
            with st.container(border=True):
                tc1, tc2, tc3 = st.columns([2, 2, 2])
                tc1.markdown(f"🔴 **{t['worker_name']}** ({t['state']})")
                tc2.markdown(f"**Type:** {t['termination_type']}")
                tc3.markdown(f"**Assigned to:** {t['assigned_to']}")

                st.markdown(f"**Approved by:** {t['approved_by']} on {t['approved_date']}")

                # Progress checklist
                steps = {
                    "Letter Drafted": bool(t["letter_drafted"]),
                    "Letter Sent": bool(t["letter_sent"]),
                    "Response Received": bool(t["response_received"]),
                }
                progress = sum(steps.values())
                st.progress(progress / 3, text=f"Progress: {progress}/3 steps")

                for step, done in steps.items():
                    icon = "✅" if done else "⬜"
                    st.markdown(f"{icon} {step}")

                if t["notes"]:
                    st.caption(f"Notes: {t['notes']}")

    with tab_add:
        st.subheader("Initiate New Termination")
        with st.form("add_termination"):
            active_cases = cases_df[cases_df["status"] == "Active"]
            existing_term_cases = set(terms["case_id"].tolist()) if len(terms) > 0 else set()
            available = active_cases[~active_cases["id"].isin(existing_term_cases)]
            case_options = {f"{r['worker_name']} ({r['state']})": r["id"] for _, r in available.iterrows()}

            if case_options:
                sel = st.selectbox("Worker", list(case_options.keys()))
                term_type = st.selectbox("Termination Type", ["Inherent Requirements", "Show Cause", "Show Cause / Inherent Requirements", "Loss of Contract", "Other"])
                approved_by = st.text_input("Approved By")
                assigned_to = st.text_input("Assigned To")
                term_notes = st.text_area("Notes")

                if st.form_submit_button("Initiate Termination"):
                    case_id = case_options[sel]
                    conn = db.get_connection()
                    conn.execute("""
                        INSERT INTO terminations (case_id, termination_type, approved_by, approved_date, assigned_to, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (case_id, term_type, approved_by, date.today().isoformat(), assigned_to, term_notes))
                    conn.commit()
                    conn.close()
                    log_activity(case_id, "Termination Initiated", f"Type: {term_type}, Assigned to: {assigned_to}")
                    st.success("Termination initiated!")
                    st.rerun()
            else:
                st.info("All active cases already have termination records.")
                st.form_submit_button("Initiate Termination", disabled=True)

    with tab_update:
        st.subheader("Update Termination Progress")
        if len(terms) > 0:
            term_options = {f"{r['worker_name']} - {r['termination_type']}": r for _, r in terms.iterrows()}
            sel_term = st.selectbox("Select Termination", list(term_options.keys()))
            t = term_options[sel_term]

            with st.form("update_termination"):
                ut1, ut2 = st.columns(2)
                u_status = ut1.selectbox("Status", ["Pending", "In Progress", "Completed", "Cancelled"],
                    index=["Pending", "In Progress", "Completed", "Cancelled"].index(t["status"]) if t["status"] in ["Pending", "In Progress", "Completed", "Cancelled"] else 0
                )
                u_drafted = ut1.checkbox("Letter Drafted", value=bool(t["letter_drafted"]))
                u_sent = ut2.checkbox("Letter Sent", value=bool(t["letter_sent"]))
                u_response = ut2.checkbox("Response Received", value=bool(t["response_received"]))
                u_notes = st.text_area("Notes", value=t["notes"] or "")

                if st.form_submit_button("Update"):
                    conn = db.get_connection()
                    conn.execute("""
                        UPDATE terminations SET status=?, letter_drafted=?, letter_sent=?,
                            response_received=?, notes=?, completed_date=?
                        WHERE id=?
                    """, (u_status, int(u_drafted), int(u_sent), int(u_response), u_notes,
                          date.today().isoformat() if u_status == "Completed" else None,
                          int(t["id"])))
                    conn.commit()
                    conn.close()
                    log_activity(int(t["case_id"]), "Termination Updated", f"Status: {u_status}")
                    st.success("Updated!")
                    st.rerun()
        else:
            st.info("No termination records to update.")


# ============================================================
# PIAWE CALCULATOR PAGE
# ============================================================
elif page == "PIAWE Calculator":
    st.title("PIAWE & Compensation Calculator")

    st.info("Use this calculator to work out weekly compensation entitlements based on PIAWE, capacity, and current earnings.")

    tab_calc, tab_bulk = st.tabs(["Quick Calculator", "All Cases"])

    with tab_calc:
        with st.form("piawe_calc"):
            pc1, pc2 = st.columns(2)
            calc_piawe = pc1.number_input("PIAWE (Weekly, pre-tax)", min_value=0.0, value=0.0, step=0.01)
            calc_period = pc2.selectbox("Entitlement Period", ["Weeks 1-13 (95%)", "Weeks 14-130 (80%)"])
            calc_cwe = pc1.number_input("Current Weekly Earnings (CWE)", min_value=0.0, value=0.0, step=0.01, help="Gross amount earned by worker for working in the pay period")
            calc_days = pc2.number_input("Days in Pay Period", min_value=1, max_value=14, value=10)
            calc_backpay = pc1.number_input("Back-pay & Expenses", min_value=0.0, value=0.0, step=0.01)

            if st.form_submit_button("Calculate"):
                rate = 0.95 if "95%" in calc_period else 0.80
                entitled = calc_piawe * rate
                daily_rate = entitled / 5  # 5 working days

                if calc_cwe > 0:
                    # Worker is on modified duties earning CWE
                    compensation = max(0, entitled - (calc_cwe * rate))
                    top_up = max(0, entitled - calc_cwe) if calc_cwe < entitled else 0
                else:
                    # No capacity - full compensation
                    compensation = entitled * (calc_days / 5) if calc_days != 10 else entitled * 2
                    top_up = 0

                total = calc_cwe + compensation + calc_backpay

                st.divider()
                st.subheader("Results")
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("PIAWE Rate", f"${entitled:,.2f}/wk")
                rc1.metric("Daily Rate", f"${daily_rate:,.2f}/day")
                rc2.metric("Wages (CWE)", f"${calc_cwe:,.2f}")
                rc2.metric("Compensation", f"${compensation:,.2f}")
                rc3.metric("Total Payable", f"${total:,.2f}")
                if top_up > 0:
                    rc3.metric("Top-up Required", f"${top_up:,.2f}")

                st.caption(f"Calculation: PIAWE ${calc_piawe:,.2f} x {rate*100:.0f}% = ${entitled:,.2f} entitlement. "
                          f"CWE ${calc_cwe:,.2f}. Compensation = max(0, ${entitled:,.2f} - ${calc_cwe*rate:,.2f}) = ${compensation:,.2f}")

    with tab_bulk:
        st.subheader("PIAWE Summary - All Active Cases")
        cases_df = get_cases_df()
        active = cases_df[cases_df["status"] == "Active"]

        for _, case in active.iterrows():
            piawe = case["piawe"]
            rate_str = case["reduction_rate"]

            with st.container(border=True):
                bc1, bc2, bc3, bc4 = st.columns([2, 1, 1, 2])
                bc1.markdown(f"**{case['worker_name']}** ({case['state']})")

                if pd.notna(piawe) and rate_str in ("95%", "80%"):
                    rate = 0.95 if rate_str == "95%" else 0.80
                    entitled = piawe * rate
                    bc2.markdown(f"PIAWE: **${piawe:,.2f}**")
                    bc3.markdown(f"Rate: **{rate_str}** = ${entitled:,.2f}/wk")
                    bc4.markdown(f"Capacity: {case['current_capacity']}")
                elif pd.notna(piawe):
                    bc2.markdown(f"PIAWE: **${piawe:,.2f}**")
                    bc3.markdown(f"Rate: {rate_str}")
                    bc4.markdown(f"Capacity: {case['current_capacity']}")
                else:
                    bc2.markdown("🔴 **PIAWE Missing**")
                    bc3.markdown(f"Rate: {rate_str}")
                    bc4.markdown(f"Capacity: {case['current_capacity']}")


# ============================================================
# PAYROLL PAGE
# ============================================================
elif page == "Payroll":
    st.title("Payroll - Workcover Compensation")

    cases_df = get_cases_df()
    active = cases_df[cases_df["status"] == "Active"]

    tab_entry, tab_history = st.tabs(["New Pay Period Entry", "History"])

    with tab_entry:
        st.subheader("Enter Compensation for Pay Period")

        with st.form("payroll_entry"):
            case_options = {f"{r['worker_name']} ({r['state']})": r["id"] for _, r in active.iterrows()}
            sel_case = st.selectbox("Worker", list(case_options.keys()))

            pe1, pe2 = st.columns(2)
            pay_from = pe1.date_input("Period From")
            pay_to = pe2.date_input("Period To")

            case_row = active[active["id"] == case_options[sel_case]].iloc[0]
            default_piawe = float(case_row["piawe"]) if pd.notna(case_row["piawe"]) else 0.0
            default_rate = 0.95 if case_row["reduction_rate"] == "95%" else (0.80 if case_row["reduction_rate"] == "80%" else 0.0)

            pe3, pe4 = st.columns(2)
            pay_piawe = pe3.number_input("PIAWE", value=default_piawe, step=0.01)
            pay_rate = pe4.number_input("Reduction Rate", value=default_rate, min_value=0.0, max_value=1.0, step=0.05)
            pay_days = pe3.number_input("Days Off / Light Duties", min_value=0, value=0)
            pay_hours = pe4.number_input("Hours Worked", min_value=0.0, value=0.0, step=0.5)
            pay_wages = pe3.number_input("Estimated Wages", min_value=0.0, value=0.0, step=0.01)
            pay_backpay = pe4.number_input("Back-pay & Expenses", min_value=0.0, value=0.0, step=0.01)
            pay_notes = st.text_area("Notes")

            if st.form_submit_button("Calculate & Save"):
                entitled = pay_piawe * pay_rate
                if pay_wages > 0:
                    top_up = max(0, entitled - pay_wages)
                    compensation = top_up
                else:
                    daily = entitled / 5
                    compensation = daily * pay_days
                    top_up = 0

                total = pay_wages + compensation + pay_backpay

                case_id = case_options[sel_case]
                conn = db.get_connection()
                conn.execute("""
                    INSERT INTO payroll_entries (case_id, period_from, period_to, piawe, reduction_rate,
                        days_off, hours_worked, estimated_wages, compensation_payable, top_up,
                        back_pay_expenses, total_payable, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (case_id, pay_from.isoformat(), pay_to.isoformat(), pay_piawe, pay_rate,
                      pay_days, pay_hours, pay_wages, compensation, top_up, pay_backpay, total, pay_notes))
                conn.commit()
                conn.close()
                log_activity(case_id, "Payroll Entry", f"Period {pay_from} to {pay_to}: Total ${total:,.2f}")

                st.success(f"Saved! Compensation: ${compensation:,.2f} | Wages: ${pay_wages:,.2f} | Total: ${total:,.2f}")

    with tab_history:
        st.subheader("Payroll History")
        conn = db.get_connection()
        history = pd.read_sql_query("""
            SELECT p.*, c.worker_name, c.state
            FROM payroll_entries p
            JOIN cases c ON p.case_id = c.id
            ORDER BY p.period_to DESC
        """, conn)
        conn.close()

        if len(history) > 0:
            st.dataframe(
                history[["worker_name", "state", "period_from", "period_to", "piawe",
                         "reduction_rate", "estimated_wages", "compensation_payable",
                         "top_up", "total_payable", "notes"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "worker_name": "Worker",
                    "state": "State",
                    "period_from": "From",
                    "period_to": "To",
                    "piawe": st.column_config.NumberColumn("PIAWE", format="$%.2f"),
                    "reduction_rate": st.column_config.NumberColumn("Rate", format="%.0f%%"),
                    "estimated_wages": st.column_config.NumberColumn("Wages", format="$%.2f"),
                    "compensation_payable": st.column_config.NumberColumn("Compensation", format="$%.2f"),
                    "top_up": st.column_config.NumberColumn("Top-up", format="$%.2f"),
                    "total_payable": st.column_config.NumberColumn("Total", format="$%.2f"),
                }
            )
        else:
            st.info("No payroll entries yet. Use the 'New Pay Period Entry' tab to add entries.")


# ============================================================
# ACTIVITY LOG PAGE
# ============================================================
elif page == "Activity Log":
    st.title("Activity Log")

    tab_activity, tab_audit = st.tabs(["Activity Log", "Audit Trail"])

    with tab_activity:
        log = get_activity_log(limit=100)
        if len(log) > 0:
            for _, entry in log.iterrows():
                with st.container(border=True):
                    lc1, lc2, lc3 = st.columns([1, 2, 3])
                    lc1.caption(entry["created_at"][:16] if entry["created_at"] else "")
                    lc2.markdown(f"**{entry['worker_name'] or 'System'}** - {entry['action']}")
                    lc3.markdown(entry["details"] or "")
        else:
            st.info("No activity recorded yet.")

    with tab_audit:
        conn = db.get_connection()
        audit = pd.read_sql_query(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 200", conn
        )
        conn.close()
        if len(audit) > 0:
            st.dataframe(audit, use_container_width=True, hide_index=True,
                         column_config={
                             "id": None,
                             "created_at": st.column_config.TextColumn("When", width="small"),
                             "user": st.column_config.TextColumn("User", width="small"),
                             "action": st.column_config.TextColumn("Action", width="small"),
                             "table_name": st.column_config.TextColumn("Table", width="small"),
                             "field_changed": st.column_config.TextColumn("Field", width="small"),
                             "old_value": st.column_config.TextColumn("Old", width="medium"),
                             "new_value": st.column_config.TextColumn("New", width="medium"),
                             "details": st.column_config.TextColumn("Details", width="large"),
                         })
        else:
            st.info("No audit entries yet. Changes will be tracked here.")


# ============================================================
# ENTITLEMENTS PAGE
# ============================================================
elif page == "Entitlements":
    st.title("Entitlement Calculator")

    tab_case, tab_manual, tab_premium = st.tabs(["By Case", "Manual Calculator", "Premium Savings"])

    with tab_case:
        st.caption("Select a case to view entitlement breakdown based on state, PIAWE, and date of injury.")
        cases_df = get_cases_df()
        active_cases = cases_df[cases_df["status"] == "Active"]

        if len(active_cases) == 0:
            st.info("No active cases.")
        else:
            case_options = {f"{r['worker_name']} ({r['state']})": r for _, r in active_cases.iterrows()}
            selected = st.selectbox("Select Worker", list(case_options.keys()))
            case = case_options[selected]

            result = entitlements.calculate_entitlement(
                state=case["state"],
                piawe=case["piawe"],
                date_of_injury=case["date_of_injury"],
            )

            if result is None:
                missing = []
                if not case["piawe"]:
                    missing.append("PIAWE")
                if not case["date_of_injury"]:
                    missing.append("Date of Injury")
                st.warning(f"Cannot calculate — missing: {', '.join(missing) or 'data'}. Update the case details first.")
            else:
                # Summary metrics
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Weeks Since Injury", result.weeks_since_injury)
                m2.metric("Current Rate", f"{result.current_rate * 100:.0f}%")
                m3.metric("Weekly Comp.", f"${result.weekly_compensation:,.2f}")
                m4.metric("Est. Total Paid", f"${result.total_paid_estimate:,.2f}")
                m5.metric("Weeks Remaining", result.remaining_weeks)

                st.caption(f"**Current period:** {result.current_period_label}")

                # Period breakdown table
                st.markdown("#### Step-Down Breakdown")
                period_df = pd.DataFrame(result.all_periods)
                st.dataframe(
                    period_df[["label", "rate_pct", "weeks_in_period", "weekly_amount", "period_total", "status"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "label": "Period",
                        "rate_pct": "Rate",
                        "weeks_in_period": "Weeks",
                        "weekly_amount": st.column_config.NumberColumn("Weekly $", format="$%.2f"),
                        "period_total": st.column_config.NumberColumn("Period Total", format="$%.2f"),
                        "status": "Status",
                    }
                )

                # Timeline bar chart
                timeline = entitlements.get_step_down_timeline(case["state"], case["piawe"])
                if timeline:
                    tl_df = pd.DataFrame(timeline)
                    st.bar_chart(tl_df.set_index("period")["weekly"], use_container_width=True)

                # Notes
                st.markdown("#### Legislative Notes")
                rules = entitlements.STATE_RULES.get(case["state"], {})
                st.caption(f"**{rules.get('legislation', '')}**")
                for note in result.notes:
                    st.markdown(f"- {note}")

    with tab_manual:
        st.caption("Calculate entitlements manually for any scenario.")
        mc1, mc2, mc3 = st.columns(3)
        calc_state = mc1.selectbox("State", ["VIC", "NSW", "QLD", "TAS", "SA", "WA"], key="ent_state")
        calc_piawe = mc2.number_input("PIAWE ($)", min_value=0.0, value=1000.0, step=50.0, key="ent_piawe")
        calc_doi = mc3.date_input("Date of Injury", value=None, key="ent_doi", format="DD/MM/YYYY")

        if calc_piawe > 0 and calc_doi:
            result = entitlements.calculate_entitlement(
                state=calc_state,
                piawe=calc_piawe,
                date_of_injury=calc_doi.isoformat(),
            )
            if result:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Weeks Since Injury", result.weeks_since_injury)
                m2.metric("Current Rate", f"{result.current_rate * 100:.0f}%")
                m3.metric("Weekly Comp.", f"${result.weekly_compensation:,.2f}")
                m4.metric("Est. Total Paid", f"${result.total_paid_estimate:,.2f}")

                st.caption(f"**{result.current_period_label}**")

                timeline = entitlements.get_step_down_timeline(calc_state, calc_piawe)
                if timeline:
                    tl_df = pd.DataFrame(timeline)
                    st.dataframe(tl_df, use_container_width=True, hide_index=True,
                                 column_config={
                                     "weekly": st.column_config.NumberColumn("Weekly $", format="$%.2f"),
                                     "period_total": st.column_config.NumberColumn("Period Total", format="$%.2f"),
                                     "cumulative": st.column_config.NumberColumn("Cumulative $", format="$%.2f"),
                                 })

                for note in result.notes:
                    st.markdown(f"- {note}")

    with tab_premium:
        st.markdown("#### Premium Savings Calculator")
        st.caption("See how better claim management translates to reduced premiums and real dollar savings.")

        pc1, pc2 = st.columns(2)
        prem_state = pc1.selectbox("State", ["VIC", "NSW", "QLD", "TAS", "SA", "WA"], key="prem_state")
        prem_wages = pc2.number_input("Annual Wages Bill ($)", min_value=0.0, value=2000000.0,
                                       step=100000.0, format="%.0f", key="prem_wages")
        prem_rate = pc1.number_input("Current Premium Rate (%)", min_value=0.0, max_value=20.0,
                                      value=2.5, step=0.1, format="%.2f", key="prem_rate")
        prem_claims = pc2.number_input("Active Claims (last 3 years)", min_value=0, value=5,
                                        step=1, key="prem_claims")
        prem_avg_cost = pc1.number_input("Avg Claim Cost ($)", min_value=0.0, value=25000.0,
                                          step=5000.0, format="%.0f", key="prem_avg_cost")

        if prem_wages > 0 and prem_rate > 0:
            savings = entitlements.calculate_premium_savings(
                annual_wages=prem_wages,
                current_rate=prem_rate,
                num_claims=prem_claims,
                avg_claim_cost=prem_avg_cost,
                state=prem_state,
            )

            # Current state
            st.divider()
            st.markdown("#### Current Position")
            cp1, cp2, cp3 = st.columns(3)
            cp1.metric("Annual Wages", f"${savings.annual_wages:,.0f}")
            cp2.metric("Premium Rate", f"{savings.current_rate:.2f}%")
            cp3.metric("Annual Premium", f"${savings.current_premium:,.0f}")

            # Savings scenarios
            st.divider()
            st.markdown("#### Projected Savings with Better Management")

            for i, scenario in enumerate(savings.scenarios):
                with st.container(border=True):
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.markdown(f"**{scenario['label']}**")
                    sc2.metric("New Rate", scenario["new_rate_pct"],
                               delta=f"-{scenario['reduction_pct']:.1f}%", delta_color="inverse")
                    sc3.metric("Annual Savings", f"${scenario['annual_savings']:,.0f}")
                    sc4.metric("5-Year Savings", f"${scenario['savings_5yr']:,.0f}")

            # ROI highlight
            st.divider()
            best = savings.scenarios[2]  # aggressive
            moderate = savings.scenarios[1]

            st.markdown("#### Return on Investment")
            roi1, roi2 = st.columns(2)
            with roi1:
                st.markdown(f"""
**With moderate improvement:**
- Reduce claims by 20%, shorten durations by 25%
- Premium drops from **{savings.current_rate:.2f}%** to **{moderate['new_rate']:.2f}%**
- Save **${moderate['annual_savings']:,.0f}/year** = **${moderate['savings_5yr']:,.0f} over 5 years**
""")
            with roi2:
                st.markdown(f"""
**With active management:**
- Reduce claims by 35%, shorten durations by 40%
- Premium drops from **{savings.current_rate:.2f}%** to **{best['new_rate']:.2f}%**
- Save **${best['annual_savings']:,.0f}/year** = **${best['savings_5yr']:,.0f} over 5 years**
""")

            st.info(
                "These projections are based on standard experience rating models. "
                "Actual savings depend on insurer calculations, industry classification, "
                "and claims history weighting period (typically 3 years)."
            )


# ============================================================
# CALENDAR PAGE
# ============================================================
elif page == "Calendar":
    st.title("Calendar")

    # Auto-generate events from case data (COC expiries, follow-ups, termination dates)
    cases_df = get_cases_df()
    active = cases_df[cases_df["status"] == "Active"]
    cocs = get_latest_cocs()

    tab_upcoming, tab_add, tab_all = st.tabs(["Upcoming", "Add Event", "All Events"])

    with tab_upcoming:
        # Build event list from system data + manual events
        events = []

        # COC expiry dates
        for _, row in cocs.iterrows():
            if row["cert_to"]:
                try:
                    exp_date = datetime.strptime(row["cert_to"], "%Y-%m-%d").date()
                    status = "OVERDUE" if exp_date < date.today() else "Upcoming"
                    events.append({
                        "date": exp_date,
                        "title": f"COC Expiry — {row['worker_name']}",
                        "type": "COC Review",
                        "status": status,
                        "case_id": int(row["case_id"]),
                    })
                except (ValueError, TypeError):
                    pass

        # Correspondence follow-ups
        conn = db.get_connection()
        follow_ups = pd.read_sql_query("""
            SELECT co.*, c.worker_name FROM correspondence co
            JOIN cases c ON co.case_id = c.id
            WHERE co.follow_up_date IS NOT NULL AND co.follow_up_done = 0
            ORDER BY co.follow_up_date
        """, conn)

        for _, fu in follow_ups.iterrows():
            try:
                fu_date = datetime.strptime(fu["follow_up_date"], "%Y-%m-%d").date()
                status = "OVERDUE" if fu_date < date.today() else "Upcoming"
                events.append({
                    "date": fu_date,
                    "title": f"Follow up: {fu['subject'] or 'Correspondence'} — {fu['worker_name']}",
                    "type": "Follow-up",
                    "status": status,
                    "case_id": int(fu["case_id"]),
                })
            except (ValueError, TypeError):
                pass

        # Manual calendar events
        manual_events = pd.read_sql_query("""
            SELECT ce.*, c.worker_name FROM calendar_events ce
            LEFT JOIN cases c ON ce.case_id = c.id
            WHERE ce.is_completed = 0
            ORDER BY ce.event_date
        """, conn)
        conn.close()

        for _, ev in manual_events.iterrows():
            try:
                ev_date = datetime.strptime(ev["event_date"], "%Y-%m-%d").date()
                status = "OVERDUE" if ev_date < date.today() else "Upcoming"
                events.append({
                    "date": ev_date,
                    "title": f"{ev['title']}" + (f" — {ev['worker_name']}" if ev["worker_name"] else ""),
                    "type": ev["event_type"],
                    "status": status,
                    "case_id": ev.get("case_id"),
                })
            except (ValueError, TypeError):
                pass

        # Sort all events by date
        events.sort(key=lambda x: x["date"])

        if not events:
            st.info("No upcoming events.")
        else:
            # Group by week
            overdue = [e for e in events if e["status"] == "OVERDUE"]
            upcoming = [e for e in events if e["status"] == "Upcoming"]

            if overdue:
                st.markdown(f"#### Overdue ({len(overdue)})")
                for ev in overdue:
                    days_overdue = (date.today() - ev["date"]).days
                    label = f"🔴 **{ev['title']}** · {ev['type']} · {ev['date'].strftime('%d/%m/%Y')} ({days_overdue}d overdue)"
                    if ev.get("case_id"):
                        if st.button(label, key=f"cal_o_{ev['title'][:20]}_{ev['date']}", use_container_width=True):
                            st.session_state.selected_case_id = int(ev["case_id"])
                            st.session_state.prev_page = "Calendar"
                            st.session_state.page = "Case Detail"
                            st.rerun()
                    else:
                        st.markdown(label)

            if upcoming:
                st.markdown(f"#### Upcoming ({len(upcoming)})")
                for ev in upcoming:
                    days_until = (ev["date"] - date.today()).days
                    icon = "🟠" if days_until <= 7 else "🟢"
                    label = f"{icon} **{ev['title']}** · {ev['type']} · {ev['date'].strftime('%d/%m/%Y')} ({days_until}d)"
                    if ev.get("case_id"):
                        if st.button(label, key=f"cal_u_{ev['title'][:20]}_{ev['date']}", use_container_width=True):
                            st.session_state.selected_case_id = int(ev["case_id"])
                            st.session_state.prev_page = "Calendar"
                            st.session_state.page = "Case Detail"
                            st.rerun()
                    else:
                        st.markdown(label)

    with tab_add:
        st.markdown("#### Add Calendar Event")
        with st.form("add_calendar_event"):
            ev_title = st.text_input("Event Title*")
            ev1, ev2 = st.columns(2)
            ev_date = ev1.date_input("Date*", format="DD/MM/YYYY")
            ev_types = ["COC Review", "Medical Appointment", "Insurer Meeting",
                        "RTW Review", "Termination Deadline", "Follow-up", "Other"]
            ev_type = ev2.selectbox("Event Type", ev_types)

            # Optional case link
            case_opts = {"None": None}
            for _, c in active.iterrows():
                case_opts[f"{c['worker_name']} ({c['state']})"] = int(c["id"])
            ev_case = st.selectbox("Link to Case (optional)", list(case_opts.keys()))
            ev_desc = st.text_area("Description")

            if st.form_submit_button("Add Event", type="primary") and ev_title:
                conn = db.get_connection()
                conn.execute(
                    "INSERT INTO calendar_events (case_id, title, event_date, event_type, description) VALUES (?, ?, ?, ?, ?)",
                    (case_opts[ev_case], ev_title, ev_date.isoformat(), ev_type, ev_desc or None)
                )
                conn.commit()
                conn.close()
                log_audit("Created", "calendar_events", case_id=case_opts[ev_case], details=f"Event: {ev_title} on {ev_date}")
                st.success(f"Event added: {ev_title}")
                st.rerun()

    with tab_all:
        conn = db.get_connection()
        all_events = pd.read_sql_query("""
            SELECT ce.*, c.worker_name FROM calendar_events ce
            LEFT JOIN cases c ON ce.case_id = c.id
            ORDER BY ce.event_date DESC
        """, conn)
        conn.close()
        if len(all_events) > 0:
            st.dataframe(all_events[["event_date", "title", "event_type", "worker_name", "is_completed"]],
                         use_container_width=True, hide_index=True,
                         column_config={
                             "event_date": "Date",
                             "title": "Event",
                             "event_type": "Type",
                             "worker_name": "Worker",
                             "is_completed": st.column_config.CheckboxColumn("Done"),
                         })
        else:
            st.info("No calendar events yet.")


# ============================================================
# CORRESPONDENCE PAGE
# ============================================================
elif page == "Correspondence":
    st.title("Insurer Correspondence Tracker")

    cases_df = get_cases_df()
    active = cases_df[cases_df["status"] == "Active"]

    tab_view, tab_add = st.tabs(["View Correspondence", "Log New"])

    with tab_view:
        # Filter by case
        case_opts = {"All Cases": None}
        for _, c in active.iterrows():
            case_opts[f"{c['worker_name']} ({c['state']})"] = int(c["id"])
        sel_filter = st.selectbox("Filter by Case", list(case_opts.keys()), key="corr_filter")

        conn = db.get_connection()
        if case_opts[sel_filter]:
            corr = pd.read_sql_query("""
                SELECT co.*, c.worker_name FROM correspondence co
                JOIN cases c ON co.case_id = c.id
                WHERE co.case_id = ? ORDER BY co.date DESC
            """, conn, params=(case_opts[sel_filter],))
        else:
            corr = pd.read_sql_query("""
                SELECT co.*, c.worker_name FROM correspondence co
                JOIN cases c ON co.case_id = c.id ORDER BY co.date DESC
            """, conn)
        conn.close()

        if len(corr) == 0:
            st.info("No correspondence logged yet.")
        else:
            # Pending follow-ups first
            pending = corr[(corr["follow_up_date"].notna()) & (corr["follow_up_done"] == 0)]
            if len(pending) > 0:
                st.markdown(f"#### Pending Follow-ups ({len(pending)})")
                for _, row in pending.iterrows():
                    days_str = ""
                    try:
                        fu_date = datetime.strptime(row["follow_up_date"], "%Y-%m-%d").date()
                        diff = (fu_date - date.today()).days
                        if diff < 0:
                            days_str = f" · 🔴 {abs(diff)}d overdue"
                        else:
                            days_str = f" · {diff}d remaining"
                    except (ValueError, TypeError):
                        pass
                    with st.container(border=True):
                        st.markdown(f"**{row['worker_name']}** — {row['subject'] or 'No subject'}{days_str}")
                        st.caption(f"{row['direction']} {row['contact_type']} · {row['date']} · {row['contact_name'] or ''}")
                        if row["summary"]:
                            st.markdown(row["summary"])
                        if st.button("Mark Done", key=f"corr_done_{row['id']}"):
                            conn2 = db.get_connection()
                            conn2.execute("UPDATE correspondence SET follow_up_done = 1 WHERE id = ?", (row["id"],))
                            conn2.commit()
                            conn2.close()
                            log_audit("Updated", "correspondence", record_id=int(row["id"]),
                                      case_id=int(row["case_id"]), field_changed="follow_up_done",
                                      old_value="0", new_value="1")
                            st.rerun()

            # All correspondence
            st.markdown("#### All Correspondence")
            st.dataframe(
                corr[["date", "worker_name", "direction", "contact_type", "contact_name", "subject", "follow_up_date", "follow_up_done"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "date": "Date",
                    "worker_name": "Worker",
                    "direction": "Direction",
                    "contact_type": "Type",
                    "contact_name": "Contact",
                    "subject": "Subject",
                    "follow_up_date": "Follow-up By",
                    "follow_up_done": st.column_config.CheckboxColumn("Done"),
                }
            )

    with tab_add:
        st.markdown("#### Log New Correspondence")
        with st.form("add_correspondence"):
            case_opts_form = {}
            for _, c in active.iterrows():
                case_opts_form[f"{c['worker_name']} ({c['state']})"] = int(c["id"])
            corr_case = st.selectbox("Case*", list(case_opts_form.keys()), key="corr_case")

            cc1, cc2 = st.columns(2)
            corr_date = cc1.date_input("Date*", value=date.today(), format="DD/MM/YYYY", key="corr_date")
            corr_dir = cc2.selectbox("Direction", ["Outbound", "Inbound"], key="corr_dir")
            corr_type = cc1.selectbox("Type", ["Email", "Phone", "Letter", "Portal", "Meeting", "Other"], key="corr_type")
            corr_contact = cc2.text_input("Contact Name", key="corr_contact")
            corr_subject = st.text_input("Subject", key="corr_subject")
            corr_summary = st.text_area("Summary / Notes", key="corr_summary")
            corr_followup = st.date_input("Follow-up Date (optional)", value=None, format="DD/MM/YYYY", key="corr_fu")

            if st.form_submit_button("Log Correspondence", type="primary") and corr_case:
                cid = case_opts_form[corr_case]
                conn = db.get_connection()
                conn.execute("""
                    INSERT INTO correspondence (case_id, date, direction, contact_type, contact_name,
                        subject, summary, follow_up_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (cid, corr_date.isoformat(), corr_dir, corr_type,
                      corr_contact or None, corr_subject or None,
                      corr_summary or None,
                      corr_followup.isoformat() if corr_followup else None))
                conn.commit()
                conn.close()
                log_activity(cid, "Correspondence Logged", f"{corr_dir} {corr_type}: {corr_subject}")
                log_audit("Created", "correspondence", case_id=cid, details=f"{corr_dir} {corr_type}: {corr_subject}")
                st.success("Correspondence logged!")
                st.rerun()
