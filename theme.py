import streamlit as st

def inject_sovereign_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

    /* Color Palette */
    :root {
        --bg-main: #F4F4F5;
        --obsidian: #09090B;
        --saffron: #EA580C;
        --emerald: #10B981;
        --azure: #2563EB;
        --crimson: #E11D48;
        --surface: #FFFFFF;
        --border: #E4E4E7;
        --text-muted: #71717A;
    }

    /* Annihilate Streamlit Defaults */
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    .main, .stApp { background-color: var(--bg-main) !important; }
    
    /* Flush Top Layout */
    .block-container {
        padding-top: 0rem !important; 
        padding-bottom: 3rem !important;
        max-width: 1200px;
    }

    /* Typography */
    html, body, p, span, div { font-family: 'Space Grotesk', sans-serif !important; color: var(--obsidian); }
    h1, h2, h3 { font-weight: 700 !important; letter-spacing: -0.02em; }
    h1 { font-size: 28px !important; margin-bottom: 20px !important; }

    /* The Sovereign Banner */
    .gov-banner {
        background-color: var(--obsidian);
        color: #FFFFFF;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 0 0 4px 4px;
    }
    .tricolor-strip {
        height: 4px;
        width: 100%;
        background: linear-gradient(to right, #FF9933 0%, #FF9933 33.3%, #FFFFFF 33.3%, #FFFFFF 66.6%, #138808 66.6%, #138808 100%);
        margin-bottom: 30px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }

    /* UI Cards with Hover Physics */
    .dpi-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 3px solid var(--obsidian);
        border-radius: 6px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .dpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .dpi-card--saffron { border-top-color: var(--saffron); }
    .dpi-card--emerald { border-top-color: var(--emerald); }
    .dpi-card--azure { border-top-color: var(--azure); }

    /* Metric Stat Cards */
    .stat-card {
        background: var(--surface);
        padding: 20px;
        border-radius: 6px;
        border: 1px solid var(--border);
        border-left: 4px solid var(--obsidian);
    }
    .stat-label { font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
    .stat-val { font-size: 32px; font-weight: 800; font-family: 'JetBrains Mono', monospace; margin-top: 4px; }

    /* Badges & Pulses */
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
    }
    .badge-pending { background: #FFF7ED; color: #C2410C; border: 1px solid #FFEDD5; }
    .badge-progress { background: #EFF6FF; color: #1D4ED8; border: 1px solid #DBEAFE; }
    .badge-resolved { background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }
    .badge-breach { background: #FEF2F2; color: #BE123C; border: 1px solid #FECDD3; }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
        70% { box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
    .live-pulse { animation: pulse 2s infinite; background: var(--emerald); color: white; }
    .mono-hash { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 600; background: var(--obsidian); color: #34D399; padding: 4px 8px; border-radius: 4px; }

    /* Native Element Overrides */
    [data-testid="stSidebar"] { background-color: var(--surface) !important; border-right: 1px solid var(--border) !important; }
    .stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid var(--border); }
    .stTabs [data-baseweb="tab"] { font-family: 'Space Grotesk', sans-serif !important; font-weight: 600 !important; text-transform: uppercase; font-size: 13px; }
    .stButton > button { font-family: 'Space Grotesk', sans-serif !important; font-weight: 600 !important; border-radius: 4px !important; transition: all 0.2s; }
    .stButton > button[kind="primary"] { background: var(--obsidian) !important; color: white !important; border: none !important; }
    .stButton > button[kind="primary"]:hover { background: #27272A !important; }
    </style>
    """, unsafe_allow_html=True)

def get_plotly_layout() -> dict:
    return dict(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Space Grotesk', color='#52525B'),
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(showgrid=False, zeroline=False, linecolor='#E4E4E7', tickfont=dict(size=12, color='#3F3F46', weight=500)),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='right', x=1)
    )