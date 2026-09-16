import os
import time
import hashlib
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from theme import inject_sovereign_css, get_plotly_sovereign_layout
from backend import get_all_complaints, execute_admin_sanction, execute_field_resolution
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="JanSeva DPI | Govt of India", layout="wide", page_icon="🇮🇳", initial_sidebar_state="expanded")
inject_sovereign_css()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DEPT_DIRECTORY = {
    "Roads":       {"office": "State PWD Roads & Bridges Division",      "officer": "Er. Rajesh Varma, JE (Civil)"},
    "Water":       {"office": "Municipal Water Supply Board",            "officer": "Er. K. Ramesh, AEE (Water)"},
    "Electricity": {"office": "Power Distribution Corp (DISCOM)",        "officer": "Er. M. Praveen, SDE (Power)"},
    "Sanitation":  {"office": "Solid Waste Management Bureau",           "officer": "Dr. A. Rao, Chief Sanitary Inspector"},
    "Cyber Crime": {"office": "Cyber Crime Police Station",              "officer": "Inspector S. Reddy, Cyber Cell"},
    "Civil":       {"office": "Municipal Zonal Engineering Office",      "officer": "Er. P. Naidu, Executive Engineer"},
}

AUTH_DB = {
    "collector":   {"pass": "ias@india2026",  "role": "admin", "dept": "All"},
    "pwd_roads":   {"pass": "pwd@infra2026",  "role": "field", "dept": "Roads"},
    "water_board": {"pass": "jal@clean2026",  "role": "field", "dept": "Water"},
    "electricity": {"pass": "power@grid2026", "role": "field", "dept": "Electricity"},
    "cyber_cop":   {"pass": "cyber@cell2026", "role": "field", "dept": "Cyber Crime"},
    "sanitation":  {"pass": "swm@clean2026",  "role": "field", "dept": "Sanitation"},
}

for k, v in {"role": "public", "dept": None, "login_attempts": 0, "lockout_time": 0}.items():
    if k not in st.session_state: st.session_state[k] = v

def get_telegram_url(file_id: str) -> str | None:
    if not file_id or str(file_id).strip().lower() in {"none", "nan", "null", ""}: return None
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        if r.get("ok"): return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}"
    except Exception: pass
    return None

@st.cache_data(ttl=86400)
def fetch_address(lat, lon) -> str:
    if pd.isna(lat) or pd.isna(lon): return "GPS Location Not Provided"
    try:
        r = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={"User-Agent": "JanSeva_DPI_India"}, timeout=5).json()
        return f"{r.get('display_name', 'Address unknown')} <a href='https://maps.google.com/?q={lat},{lon}' target='_blank' style='color:var(--clr-azure)'>📍 Map</a>"
    except Exception: return f"Coordinates: {lat:.5f}, {lon:.5f}"

def display_media(file_url: str, media_type: str, is_officer: bool = False):
    if not file_url: return
    m = str(media_type).lower()
    try:
        if "photo" in m or m in {"nan", "none"}:
            st.image(file_url, use_container_width=True)
            if is_officer: 
                st.markdown(f"<div style='text-align:center;margin-top:6px'><a href='{file_url}' target='_blank' style='font-size:12px;font-weight:700;color:var(--clr-azure)'>🔍 View Original Govt Scan</a></div>", unsafe_allow_html=True)
        elif "video" in m or "animation" in m: 
            st.video(file_url)
        else: 
            st.markdown(f"📎 <a href='{file_url}' target='_blank'>Download Evidence File</a>", unsafe_allow_html=True)
    except Exception: 
        st.markdown(f"📎 <a href='{file_url}' target='_blank'>View Media File</a>", unsafe_allow_html=True)

def render_status_badge(status: str, hours_open: float = 0) -> str:
    if "Resolved" in status: return f'<span class="badge badge--resolved">✓ {status}</span>'
    if hours_open > 48 and "Pending" in status: return f'<span class="badge badge--breach">🚨 SLA BREACH</span>'
    if any(k in status for k in ("Tender", "Survey", "Sanction")): return f'<span class="badge badge--progress">↻ {status}</span>'
    return f'<span class="badge badge--pending">⏳ {status}</span>'

def render_timeline(status: str) -> str:
    stages = [("1.", "Pending Review"), ("2.", "Survey & Estimation"), ("3.", "Admin Sanction"), ("4.", "Tender Awarded"), ("6.", "Resolved (Social Audit)")]
    current = next((i for i, (pfx, _) in enumerate(stages) if pfx in status[:2]), 0)
    steps = "".join([f'<div class="timeline-step {"completed" if i < current else ("active" if i == current else "")}">{label}</div>' for i, (_, label) in enumerate(stages)])
    return f'<div class="timeline-rail">{steps}</div>'

def get_audit_hash(ticket_id, amount_spent) -> str:
    return hashlib.sha256(f"GOI_DPI_{ticket_id}_{amount_spent}_VERIFIED".encode()).hexdigest()[:16].upper()

@st.cache_data(ttl=30)
def load_data() -> pd.DataFrame:
    records = get_all_complaints()
    if not records: return pd.DataFrame()
    df = pd.DataFrame(records)
    df["budget_allocated"] = pd.to_numeric(df.get("budget_allocated", 0), errors="coerce").fillna(0)
    df["amount_spent"]     = pd.to_numeric(df.get("amount_spent", 0),     errors="coerce").fillna(0)
    df["timestamp_dt"]     = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["hours_open"]       = (pd.Timestamp.now(tz="UTC") - df["timestamp_dt"]).dt.total_seconds() / 3600
    df["category"]         = df["category"].astype(str).replace(["nan", "None"], "Civil")
    df["office_name"]      = df["office_name"].astype(str).replace(["nan", "None", ""], "Pending Assignment")
    df["assigned_officer"] = df["assigned_officer"].astype(str).replace(["nan", "None", ""], "Awaiting Nodal Officer")
    df["materials_used"]   = df["materials_used"].astype(str).replace(["nan", "None", ""], "Standard operations.")
    df["severity"]         = df["severity"].astype(str).replace(["nan", "None"], "Medium")
    for col in ("resolution_media_id", "media_file_id"):
        if col in df.columns: df[col] = df[col].astype(str).replace(["nan", "None", ""], None)
    return df

st.markdown('<div class="gov-banner"><div>🇮🇳 भारत सरकार | Government of India</div><div>Digital Public Infrastructure · JanSeva Grievance Platform</div></div><div class="tricolor-strip"></div>', unsafe_allow_html=True)

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=68)
    st.markdown("<h2 style='margin:8px 0 2px;letter-spacing:-0.02em'>JanSeva DPI</h2><p style='font-size:12px;color:var(--clr-text-muted);margin:0'>Empowering Citizens · Enabling Transparency</p>", unsafe_allow_html=True)
    st.divider()
    if st.session_state.role == "public":
        page = st.radio("Navigation", ["🌐 Public Transparency Board", "📊 Open Data Ledger", "📍 Incident Map", "🔐 Officer Gateway"], label_visibility="collapsed")
    else:
        st.markdown(f'<div class="dpi-card dpi-card--emerald" style="padding:12px 14px;margin-bottom:12px;"><div class="stat-label">Authenticated</div><div style="font-weight:700;font-size:14px;margin-top:4px">{st.session_state.role.upper()} · {st.session_state.dept}</div></div>', unsafe_allow_html=True)
        page = st.radio("Navigation", ["⚙️ Command Dashboard", "🌐 Public Transparency Board", "📊 Open Data Ledger"], label_visibility="collapsed")
        st.divider()
        if st.button("🚪 Secure Sign Out", use_container_width=True):
            st.session_state.update({"role": "public", "dept": None})
            st.rerun()

df = load_data()

if page == "🌐 Public Transparency Board":
    st.markdown("<h1>Public Transparency &amp; Social Audit Ledger</h1>", unsafe_allow_html=True)
    
    if df.empty:
        st.info("📭 No grievances in the database yet. Submit one via the Telegram bot.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="stat-card"><div class="stat-label">Total Logged</div><div class="stat-val">{len(df)}</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="stat-card" style="border-left-color:var(--clr-azure)"><div class="stat-label">Public Sanctioned</div><div class="stat-val">₹{df["budget_allocated"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="stat-card" style="border-left-color:var(--clr-saffron)"><div class="stat-label">Treasury Disbursed</div><div class="stat-val">₹{df["amount_spent"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="stat-card" style="border-left-color:var(--clr-emerald)"><div class="stat-label">Verified Resolutions</div><div class="stat-val" style="color:var(--clr-emerald)">{len(df[df["status"].str.contains("Resolved", na=False)])}</div></div>', unsafe_allow_html=True)
        st.write("<br>", unsafe_allow_html=True)

        st.markdown('<div class="dpi-card dpi-card--obsidian"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px"><span style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em">🏛️ Sector-wise Fiscal Ledger</span><span class="badge badge--resolved">LIVE AUDIT</span></div>', unsafe_allow_html=True)
        fiscal_df = df.groupby("category", as_index=False)[["budget_allocated", "amount_spent"]].sum()
        fig_fiscal = go.Figure()
        fig_fiscal.add_trace(go.Bar(name="Sanctioned Budget", x=fiscal_df["category"], y=fiscal_df["budget_allocated"], marker_color="#111827", text=[f"₹{v:,.0f}" for v in fiscal_df["budget_allocated"]], textposition="auto", textfont=dict(color="#ffffff", size=11, family="Space Grotesk, sans-serif")))
        fig_fiscal.add_trace(go.Bar(name="Disbursed (Spent)", x=fiscal_df["category"], y=fiscal_df["amount_spent"], marker_color="#059669", text=[f"₹{v:,.0f}" for v in fiscal_df["amount_spent"]], textposition="auto", textfont=dict(color="#ffffff", size=11, family="Space Grotesk, sans-serif")))
        fig_fiscal.update_layout(barmode="group", height=310, **get_plotly_sovereign_layout())
        st.plotly_chart(fig_fiscal, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

        tab_live, tab_audit = st.tabs(["📋 Live Grievance Registry", "📸 Immutable Social Audit Feed"])
        with tab_live:
            for _, item in df.iterrows():
                loc_str, is_resolved, date_str = fetch_address(item["lat"], item["lon"]), "Resolved" in item["status"], item["timestamp_dt"].strftime("%d %b %Y") if pd.notna(item["timestamp_dt"]) else "—"
                st.markdown(f"""
                    <div class="dpi-card {'dpi-card--emerald' if is_resolved else ''}">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start">
                            <div><span style="font-family:var(--font-mono);font-size:15px;font-weight:700">{item['id']}</span><span style="margin-left:10px">{render_status_badge(item['status'], item['hours_open'])}</span></div>
                            <span style="font-size:12px;color:var(--clr-text-muted)">📅 {date_str}</span>
                        </div>
                        <div style="margin-top:10px;font-size:14px;color:var(--clr-text-secondary);line-height:1.6"><b>Reported Issue:</b> {item['raw_text']}<br><b>Location:</b> {loc_str}</div><hr>
                        <div style="display:flex;flex-wrap:wrap;gap:20px;font-size:12px;color:var(--clr-text-secondary)"><div><b>Sector:</b> {item['category']}</div><div><b>Office:</b> {item['office_name']}</div><div><b>Officer:</b> {item['assigned_officer']}</div><div><b>Budget:</b> ₹{item['budget_allocated']:,.0f}</div><div><b>Severity:</b> {item['severity']}</div></div>
                """, unsafe_allow_html=True)
                
                # CRITICAL BUG FIX: Strict explicit if-blocks to prevent Streamlit DeltaGenerator bug
                if is_resolved:
                    st.markdown("**📸 Official Resolution Evidence**")
                    col_b, col_a = st.columns(2)
                    with col_b:
                        st.markdown('<div class="photo-box"><b>🔴 Citizen Report</b>', unsafe_allow_html=True)
                        c_url = get_telegram_url(item.get("media_file_id"))
                        if c_url:
                            display_media(c_url, item.get("media_type"))
                        else:
                            st.caption("No media attached.")
                        st.markdown("</div>", unsafe_allow_html=True)
                    with col_a:
                        st.markdown('<div class="photo-box"><b style="color:var(--clr-emerald)">🟢 Govt Resolution</b>', unsafe_allow_html=True)
                        r_url = get_telegram_url(item.get("resolution_media_id"))
                        if r_url:
                            display_media(r_url, "photo", is_officer=True)
                        else:
                            st.caption("No photo uploaded.")
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    with st.expander(f"📎 View Citizen Evidence — {item['id']}"):
                        m_url = get_telegram_url(item.get("media_file_id"))
                        if m_url:
                            display_media(m_url, item.get("media_type"))
                        else:
                            st.caption("No media attached.")
                st.markdown("</div>", unsafe_allow_html=True)

        with tab_audit:
            resolved_df = df[df["status"].str.contains("Resolved", na=False)]
            if resolved_df.empty: st.info("No resolved grievances yet.")
            else:
                for _, r in resolved_df.iterrows():
                    st.markdown(f"""
                        <div class="dpi-card dpi-card--emerald">
                            <div style="display:flex;justify-content:space-between;align-items:center"><span style="font-weight:700;font-size:15px">{r['category']} — {r['office_name']}</span><span style="font-size:13px;color:var(--clr-emerald);font-weight:700">✅ Audited &amp; Verified</span></div>
                            <div style="margin-top:10px;font-size:13px;color:var(--clr-text-secondary)"><b>BOQ:</b> {r['materials_used']}<br><b>Fiscal Audit:</b> Sanctioned ₹{r['budget_allocated']:,.0f} &nbsp;|&nbsp; Treasury Payout: <b style="color:var(--clr-azure)">₹{r['amount_spent']:,.0f}</b><br><span class="audit-hash">🛡️ SHA-256: 0x{r.get("audit_hash") or get_audit_hash(r["id"], r["amount_spent"])}</span></div><hr>
                    """, unsafe_allow_html=True)
                    c_b, c_a = st.columns(2)
                    with c_b:
                        st.markdown('<div class="photo-box"><b>🔴 Before</b>', unsafe_allow_html=True)
                        b_url = get_telegram_url(r.get("media_file_id"))
                        if b_url:
                            display_media(b_url, r.get("media_type"))
                        else:
                            st.caption("No photo.")
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c_a:
                        st.markdown('<div class="photo-box"><b style="color:var(--clr-emerald)">🟢 After</b>', unsafe_allow_html=True)
                        a_url = get_telegram_url(r.get("resolution_media_id"))
                        if a_url:
                            display_media(a_url, "photo", is_officer=True)
                        else:
                            st.caption("No photo.")
                        st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

elif page == "📊 Open Data Ledger":
    st.markdown("<h1>National Open Data Ledger</h1>", unsafe_allow_html=True)
    if df.empty: st.warning("No data available yet.")
    else:
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown('<div class="dpi-card"><b>Grievances by Sector</b>', unsafe_allow_html=True)
            fig_pie = go.Figure(go.Pie(labels=df["category"].value_counts().index, values=df["category"].value_counts().values, hole=0.45, marker_colors=["#111827", "#059669", "#FF9933", "#2563EB", "#94A3B8", "#B91C1C"], textfont=dict(family="Space Grotesk, sans-serif", size=12)))
            fig_pie.update_layout(height=350, showlegend=True, **get_plotly_sovereign_layout())
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)
        with col_r:
            st.markdown('<div class="dpi-card"><b>Status Lifecycle Pipeline</b>', unsafe_allow_html=True)
            status_counts = df["status"].value_counts().reset_index()
            status_colors = ["#059669" if "Resolved" in s else "#2563EB" for s in status_counts["status"]]
            fig_bar = go.Figure(go.Bar(x=status_counts["status"], y=status_counts["count"], marker_color=status_colors, textfont=dict(family="Space Grotesk, sans-serif")))
            fig_bar.update_layout(height=350, **get_plotly_sovereign_layout())
            st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="dpi-card"><b>Severity Distribution by Department</b>', unsafe_allow_html=True)
        sev_df = df.groupby(["category", "severity"]).size().reset_index(name="count")
        fig_sev = go.Figure()
        for sev, color in {"High": "#B91C1C", "Medium": "#FF9933", "Low": "#059669"}.items():
            sub = sev_df[sev_df["severity"] == sev]
            fig_sev.add_trace(go.Bar(name=sev, x=sub["category"], y=sub["count"], marker_color=color, textfont=dict(family="Space Grotesk, sans-serif")))
        fig_sev.update_layout(barmode="stack", height=350, **get_plotly_sovereign_layout())
        st.plotly_chart(fig_sev, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

elif page == "📍 Incident Map":
    st.markdown("<h1>Live Geospatial Incident Map</h1>", unsafe_allow_html=True)
    if not df.empty and not df["lat"].isnull().all():
        map_data = df.dropna(subset=["lat", "lon"]).rename(columns={"lat": "latitude", "lon": "longitude"})
        st.map(map_data, zoom=11, use_container_width=True)
    else: st.warning("No geospatial telemetry available yet.")

elif page == "🔐 Officer Gateway":
    st.markdown("<h1>Secure Authentication Gateway</h1><p style='color:var(--clr-text-muted);font-size:13px'>GovID credentials are issued by the NIC.</p>", unsafe_allow_html=True)
    if time.time() < st.session_state.lockout_time:
        st.error(f"🚨 Security Lockout Active. Retry in **{int(st.session_state.lockout_time - time.time())}s**.")
    else:
        _, col_center, _ = st.columns([1, 1.2, 1])
        with col_center:
            st.markdown('<div class="dpi-card dpi-card--saffron"><div style="text-align:center;margin-bottom:16px"><span style="font-size:28px">🔐</span><br><b style="font-size:17px;letter-spacing:-0.02em">GovID Secure Login</b><br><span style="font-size:11px;color:var(--clr-text-muted);text-transform:uppercase;letter-spacing:0.08em">National Informatics Centre</span></div>', unsafe_allow_html=True)
            with st.form("auth_form"):
                uid = st.text_input("Username", placeholder="e.g. collector")
                pwd = st.text_input("Passkey", type="password", placeholder="GovID credential")
                if st.form_submit_button("🔓 Authenticate", use_container_width=True, type="primary"):
                    if uid in AUTH_DB and AUTH_DB[uid]["pass"] == pwd:
                        st.session_state.update({"role": AUTH_DB[uid]["role"], "dept": AUTH_DB[uid]["dept"], "login_attempts": 0})
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        if st.session_state.login_attempts >= 3:
                            st.session_state.lockout_time = time.time() + 60
                            st.rerun()
                        else: st.error(f"❌ Access Denied. {3 - st.session_state.login_attempts} attempt(s) remaining.")
            st.markdown("</div>", unsafe_allow_html=True)

elif page == "⚙️ Command Dashboard":
    st.markdown(f"<h1>Command Dashboard — {st.session_state.dept.upper()}</h1>", unsafe_allow_html=True)
    if df.empty: st.info("No complaints found in the system.")
    else:
        active_df = (df[df["category"].str.contains(st.session_state.dept, case=False, na=False)] if st.session_state.role == "field" else df)[~df["status"].str.contains("Resolved", na=False)]
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="stat-card" style="border-left-color:var(--clr-saffron)"><div class="stat-label">Active Tickets</div><div class="stat-val">{len(active_df)}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="stat-card" style="border-left-color:var(--clr-crimson)"><div class="stat-label">SLA Breaches (&gt;48h)</div><div class="stat-val" style="color:var(--clr-crimson)">{len(active_df[active_df["hours_open"] > 48])}</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="stat-card" style="border-left-color:var(--clr-emerald)"><div class="stat-label">Budget Allocated</div><div class="stat-val">₹{df["budget_allocated"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        st.write("<br>", unsafe_allow_html=True)

        if active_df.empty:
            st.markdown('<div class="dpi-card dpi-card--emerald" style="text-align:center;padding:32px"><span style="font-size:32px">✅</span><br><b style="font-size:16px">All queues are clear.</b></div>', unsafe_allow_html=True)
        else:
            sel_id = st.selectbox("Select Grievance:", active_df["id"].tolist())
            row = active_df[active_df["id"] == sel_id].iloc[0]
            st.markdown(render_timeline(row["status"]), unsafe_allow_html=True)
            st.markdown(f"""
                <div class="dpi-card {'dpi-card--crimson' if row['hours_open'] > 48 else 'dpi-card--saffron'}">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start"><span style="font-family:var(--font-mono);font-weight:700;font-size:15px">{row['id']}</span>{render_status_badge(row['status'], row['hours_open'])}</div>
                    <div style="margin-top:10px;font-size:14px;color:var(--clr-text-secondary);line-height:1.7"><b>Issue:</b> {row['raw_text']}<br><b>Location:</b> {fetch_address(row['lat'], row['lon'])}<br><b>Severity:</b> {row['severity']} &nbsp;·&nbsp; <b>Open For:</b> {row['hours_open']:.1f}h</div>
                </div>
            """, unsafe_allow_html=True)
            c_url = get_telegram_url(row.get("media_file_id"))
            with st.expander("📎 View Citizen Evidence"): 
                if c_url:
                    display_media(c_url, row.get("media_type"))
                else:
                    st.caption("No media attached.")

            if st.session_state.role == "admin":
                st.markdown('<div class="dpi-card dpi-card--azure">**⚙️ Administrative Sanction Panel**', unsafe_allow_html=True)
                with st.form("admin_form"):
                    d_keys = list(DEPT_DIRECTORY.keys())
                    c_cat = row["category"] if row["category"] in d_keys else "Roads"
                    s_dept = st.selectbox("Route to Department:", d_keys, index=d_keys.index(c_cat))
                    c1, c2 = st.columns(2)
                    with c1: t_office = st.text_input("Office Name:", value=DEPT_DIRECTORY[s_dept]["office"])
                    with c2: t_officer = st.text_input("Assigned Officer:", value=DEPT_DIRECTORY[s_dept]["officer"])
                    c3, c4 = st.columns(2)
                    with c3: n_stage = st.selectbox("Advance Lifecycle:", ["2. Survey & Estimation", "3. Administrative Sanction", "4. Tender Awarded"])
                    with c4: b_alloc = st.number_input("Sanction Budget (₹):", value=float(row["budget_allocated"]), step=5000.0)
                    contractor = st.text_input("Awarded Contractor:", value=str(row.get("contractor_name") or ""))

                    if st.form_submit_button("🔒 Lock Sanction & Dispatch", type="primary", use_container_width=True):
                        execute_admin_sanction(sel_id, n_stage, b_alloc, contractor, s_dept, t_office, t_officer)
                        if pd.notna(row["chat_id"]) and BOT_TOKEN:
                            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": row["chat_id"], "text": f"🇮🇳 *Govt Update*\nTicket `{sel_id}` routed to *{t_office}*.\n🚥 Stage: {n_stage}\n💰 Sanctioned: ₹{b_alloc:,.0f}", "parse_mode": "Markdown"}, timeout=8)
                            except Exception: pass
                        st.cache_data.clear()
                        st.success("✅ Sanction locked and dispatched.")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            elif st.session_state.role == "field":
                st.markdown('<div class="dpi-card dpi-card--emerald">', unsafe_allow_html=True)
                st.info(f"💰 **Locked Budget:** ₹{row['budget_allocated']:,.0f} | **Contractor:** {row.get('contractor_name') or 'Internal'}")
                st.markdown("**🔧 Field Resolution Panel**")
                with st.form("field_form"):
                    materials = st.text_area("Measurement Book (BOQ & Materials Used):")
                    spent = st.number_input("Final Treasury Payout (₹):", value=float(row["budget_allocated"]), step=1000.0, min_value=0.0)
                    proof = st.file_uploader("Upload Official Resolution Photograph:", type=["jpg", "jpeg", "png"])

                    if st.form_submit_button("📤 Submit Resolution Proof", type="primary", use_container_width=True):
                        if not proof: st.error("❌ Resolution photograph is mandatory.")
                        else:
                            m_id = None
                            if pd.notna(row["chat_id"]) and BOT_TOKEN:
                                try:
                                    res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": row["chat_id"], "caption": f"✅ *Resolved*\nTicket: `{sel_id}`\nTreasury Payout: ₹{spent:,.0f}\nAudited by: {row['assigned_officer']}", "parse_mode": "Markdown"}, files={"photo": proof.getvalue()}, timeout=15).json()
                                    if res.get("ok"): m_id = res["result"]["photo"][-1]["file_id"]
                                except Exception: pass
                            execute_field_resolution(sel_id, spent, materials, m_id)
                            st.cache_data.clear()
                            st.success("✅ Work verified.")
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr><div style='text-align:center;padding:12px 0 4px'><p style='font-size:11px;color:var(--clr-text-muted);letter-spacing:0.04em'>DIGITAL PUBLIC INFRASTRUCTURE · JANSEVA DPI · GOVERNMENT OF INDIA 🇮🇳</p></div>", unsafe_allow_html=True)