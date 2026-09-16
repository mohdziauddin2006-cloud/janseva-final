import streamlit as st

def inject_sovereign_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

    :root {
        --clr-obsidian:      #111827;
        --clr-saffron:       #FF9933;
        --clr-saffron-light: #fff7ed;
        --clr-saffron-border:#ffedd5;
        --clr-azure:         #2563EB;
        --clr-azure-light:   #eff6ff;
        --clr-azure-border:  #dbeafe;
        --clr-emerald:       #059669;
        --clr-emerald-light: #ecfdf5;
        --clr-emerald-border:#a7f3d0;
        --clr-crimson:       #B91C1C;
        --clr-crimson-light: #fef2f2;
        --clr-crimson-border:#fecaca;
        --clr-chalk:         #F8FAFC;
        --clr-surface:       #FFFFFF;
        --clr-border:        #E2E8F0;
        --clr-border-strong: #CBD5E1;
        --clr-text-primary:  #0F172A;
        --clr-text-secondary:#475569;
        --clr-text-muted:    #94A3B8;
        --clr-text-inverted: #F8FAFC;

        --font-display:      'Space Grotesk', system-ui, sans-serif;
        --font-mono:         'JetBrains Mono', 'Courier New', monospace;

        --text-xs:    11px;
        --text-sm:    13px;
        --text-base:  15px;
        --text-lg:    18px;
        --text-xl:    22px;
        --text-3xl:   36px;
    }

    *, *::before, *::after { box-sizing: border-box; }

    html, body, [class*="css"] {
        font-family: var(--font-display) !important;
        font-size: var(--text-base);
        color: var(--clr-text-primary);
    }

    /* CRITICAL FIX: Kill Streamlit Header and Padding */
    header[data-testid="stHeader"] { display: none !important; }
    .main, .stApp { background-color: var(--clr-chalk) !important; }
    
    .block-container {
        padding-top: 0rem !important; 
        padding-bottom: 40px !important;
        max-width: 1200px;
        margin-top: 0rem !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-display) !important;
        color: var(--clr-text-primary) !important;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    h1 { font-size: var(--text-3xl) !important; font-weight: 700 !important; }
    h2 { font-size: 28px !important; font-weight: 700 !important; }
    h3 { font-size: 22px !important; font-weight: 600 !important; }

    p, li, span {
        font-family: var(--font-display) !important;
        font-size: var(--text-base);
        line-height: 1.6;
        color: var(--clr-text-secondary);
    }

    .dpi-card {
        background:        var(--clr-surface);
        border:            1px solid var(--clr-border);
        border-top:        3px solid var(--clr-obsidian);
        border-radius:     8px;
        padding:           24px;
        margin-bottom:     24px;
        box-shadow:        0 4px 6px -1px rgba(0,0,0,0.06);
    }

    .dpi-card--saffron { border-top-color: var(--clr-saffron); }
    .dpi-card--azure   { border-top-color: var(--clr-azure);   }
    .dpi-card--emerald { border-top-color: var(--clr-emerald); }
    .dpi-card--crimson { border-top-color: var(--clr-crimson); }

    .stat-card {
        background:     var(--clr-surface);
        padding:        24px;
        border-radius:  8px;
        border:         1px solid var(--clr-border);
        border-left:    5px solid var(--clr-saffron);
        box-shadow:     0 1px 3px rgba(0,0,0,0.06);
    }
    .stat-label {
        font-size:       var(--text-xs);
        font-weight:     700;
        color:           var(--clr-text-muted);
        text-transform:  uppercase;
        letter-spacing:  0.08em;
    }
    .stat-val {
        font-size:   var(--text-3xl);
        font-weight: 700;
        color:       var(--clr-text-primary);
        margin-top:  4px;
    }

    .badge {
        display:        inline-block;
        padding:        4px 12px;
        border-radius:  4px;
        font-size:      var(--text-xs);
        font-weight:    700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .badge--pending  { background: var(--clr-saffron-light); color: #c2410c; border: 1px solid var(--clr-saffron-border); }
    .badge--progress { background: var(--clr-azure-light);   color: #1d4ed8; border: 1px solid var(--clr-azure-border);   }
    .badge--resolved { background: var(--clr-emerald-light); color: #15803d; border: 1px solid var(--clr-emerald-border); }
    .badge--breach   { background: var(--clr-crimson-light); color: var(--clr-crimson); border: 1px solid var(--clr-crimson-border); }

    .audit-hash {
        display:          inline-block;
        font-family:      var(--font-mono);
        font-size:        var(--text-sm);
        font-weight:      500;
        background:       var(--clr-obsidian);
        color:            #34d399;
        padding:          8px 12px;
        border-radius:    4px;
        letter-spacing:   0.04em;
        margin-top:       12px;
    }

    .gov-banner {
        background-color: var(--clr-obsidian);
        color:            var(--clr-text-inverted);
        padding:          12px 20px;
        font-size:        var(--text-sm);
        font-weight:      500;
        display:          flex;
        justify-content:  space-between;
        align-items:      center;
        border-radius:    0 0 4px 4px;
        margin-top:       0px;
    }
    .tricolor-strip {
        height:     4px;
        width:      100%;
        background: linear-gradient(to right, #FF9933 0%, #FF9933 33.3%, #FFFFFF 33.3%, #FFFFFF 66.6%, #138808 66.6%, #138808 100%);
        margin-bottom: 24px;
    }

    .timeline-rail {
        display:        flex;
        align-items:    center;
        justify-content: space-between;
        margin:         20px 0;
        padding:        16px 20px;
        background:     var(--clr-chalk);
        border-radius:  8px;
        border:         1px solid var(--clr-border);
        gap:            8px;
    }
    .timeline-step {
        font-size:       var(--text-xs);
        font-weight:     600;
        color:           var(--clr-text-muted);
        text-align:      center;
        flex:            1;
        text-transform:  uppercase;
    }
    .timeline-step.active    { color: var(--clr-saffron); font-weight: 800; }
    .timeline-step.completed { color: var(--clr-emerald); }

    .photo-box {
        background:    var(--clr-chalk);
        border:        1px solid var(--clr-border);
        border-radius: 8px;
        padding:       12px;
        text-align:    center;
        height:        100%;
    }

    [data-testid="stSidebar"] { background-color: var(--clr-surface) !important; border-right: 1px solid var(--clr-border) !important; }
    .stButton > button { font-family: var(--font-display) !important; font-weight: 600 !important; border-radius: 4px !important; }
    .stButton > button[kind="primary"] { background: var(--clr-obsidian) !important; color: var(--clr-text-inverted) !important; }
    .stButton > button[kind="primary"]:hover { background: #1e293b !important; }
    .stTextInput > div > div > input, .stTextArea > div > textarea, .stNumberInput > div > div > input, .stSelectbox > div > div {
        font-family: var(--font-display) !important; border-radius: 4px !important; border-color: var(--clr-border-strong) !important;
    }
    .stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid var(--clr-border) !important; gap: 0 !important; }
    .stTabs [data-baseweb="tab"] { font-family: var(--font-display) !important; font-weight: 600 !important; font-size: var(--text-sm) !important; text-transform: uppercase !important; color: var(--clr-text-muted) !important; padding: 12px 20px !important; }
    .stTabs [aria-selected="true"] { color: var(--clr-obsidian) !important; border-bottom: 2px solid var(--clr-obsidian) !important; }
    hr { border: none !important; border-top: 1px solid var(--clr-border) !important; margin: 20px 0 !important; }
    [data-testid="stExpander"] { border: 1px solid var(--clr-border) !important; border-radius: 8px !important; background: var(--clr-surface) !important; }
    [data-testid="stPlotlyChart"] { background: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

def get_plotly_sovereign_layout() -> dict:
    return dict(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Space Grotesk, sans-serif', color='#475569'),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, zeroline=False, linecolor='#E2E8F0', linewidth=1, tickfont=dict(size=12, color='#334155', family='Space Grotesk, sans-serif', weight=600), title=None),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=None),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(family='Space Grotesk, sans-serif', size=12, color='#0F172A'))
    )