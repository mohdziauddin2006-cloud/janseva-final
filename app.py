import os
import time
import hashlib
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from theme import inject_sovereign_css, get_plotly_layout
from backend import get_all_complaints, execute_admin_sanction, execute_field_resolution
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="JanSeva DPI | Govt of India", layout="wide", page_icon="🇮🇳", initial_sidebar_state="expanded")
inject_sovereign_css()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DEPT_DIRECTORY = {
    "Roads":       {"office": "State PWD Roads & Bridges", "officer": "Er. Rajesh Varma"},
    "Water":       {"office": "Municipal Water Board",     "officer": "Er. K. Ramesh"},
    "Electricity": {"office": "DISCOM Power Grid",         "officer": "Er. M. Praveen"},
    "Sanitation":  {"office": "Solid Waste Management",    "officer": "Dr. A. Rao"},
    "Cyber Crime": {"office": "Cyber Police Cell",         "officer": "Insp. S. Reddy"},
    "Civil":       {"office": "Zonal Engineering Office",  "officer": "Er. P. Naidu"},
}

AUTH_DB = {
    "collector":   {"pass": "ias@india2026",  "role": "admin", "dept": "All"},
    "pwd_roads":   {"pass": "pwd@infra2026",  "role": "field", "dept": "Roads"},
    "sanitation":  {"pass": "swm@clean2026",  "role": "field", "dept": "Sanitation"},
}

for k, v in {"role": "public", "dept": None, "login_attempts": 0, "lockout_time": 0}.items():
    if k not in st.session_state: st.session_state[k] = v

def get_telegram_url(file_id: str):
    if not file_id or str(file_id).lower() in {"none", "nan", ""}: return None
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=5).json()
        if r.get("ok"): return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}"
    except: pass
    return None

@st.cache_data(ttl=86400)
def fetch_address(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return "Location Not Provided"
    try:
        r = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={"User-Agent": "JanSeva_DPI"}, timeout=3).json()
        return f"{r.get('display_name', 'Address unknown')} <a href='https://maps.google.com/?q={lat},{lon}' target='_blank' style='color:#2563EB'>📍 Map</a>"
    except: return f"Coordinates: {lat:.4f}, {lon:.4f}"

def render_status_badge(status: str) -> str:
    if "Resolved" in status: return f'<span class="badge badge-resolved">✓ {status}</span>'
    if "Pending" in status: return f'<span class="badge badge-pending">⏳ {status}</span>'
    return f'<span class="badge badge-progress">↻ {status}</span>'

def load_data() -> pd.DataFrame:
    records = get_all_complaints()
    if not records: return pd.DataFrame()
    df = pd.DataFrame(records)
    df["budget_allocated"] = pd.to_numeric(df.get("budget_allocated", 0), errors="coerce").fillna(0)
    df["amount_spent"]     = pd.to_numeric(df.get("amount_spent", 0), errors="coerce").fillna(0)
    df["timestamp_dt"]     = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["category"]         = df["category"].astype(str).replace(["nan", "None"], "Civil")
    df["office_name"]      = df["office_name"].astype(str).replace(["nan", "None"], "Pending Assignment")
    df["assigned_officer"] = df["assigned_officer"].astype(str).replace(["nan", "None"], "Awaiting Nodal Officer")
    return df

# --- TOP BANNER ---
st.markdown('<div class="gov-banner"><div>🇮🇳 भारत सरकार | Government of India</div><div>Digital Public Infrastructure · JanSeva DPI</div></div><div class="tricolor-strip"></div>', unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=68)
    st.markdown("<h2 style='margin:8px 0 2px;'>JanSeva DPI</h2><p style='font-size:12px;color:#71717A;'>Empowering Citizens · Transparency</p>", unsafe_allow_html=True)
    st.divider()
    if st.session_state.role == "public":
        page = st.radio("Navigation", ["🌐 Public Transparency Board", "📊 Open Data Ledger", "📍 Live Incident Map", "🔐 Officer Gateway"], label_visibility="collapsed")
    else:
        st.success(f"Auth: {st.session_state.role.upper()} | Dept: {st.session_state.dept}")
        page = st.radio("Navigation", ["⚙️ Command Dashboard", "🌐 Public Transparency Board", "📊 Open Data Ledger", "📍 Live Incident Map"], label_visibility="collapsed")
        st.divider()
        if st.button("🚪 Secure Sign Out", use_container_width=True):
            st.session_state.update({"role": "public", "dept": None})
            st.rerun()

df = load_data()

# ==========================================
# PAGE 1: TRANSPARENCY BOARD
# ==========================================
if page == "🌐 Public Transparency Board":
    st.markdown("<h1>Public Transparency & Social Audit Ledger</h1>", unsafe_allow_html=True)
    
    if df.empty:
        st.info("📭 No grievances in the database yet. Submit one via the Telegram bot.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f'<div class="stat-card" style="border-left-color: #2563EB"><div class="stat-label">Total Logged</div><div class="stat-val">{len(df)}</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="stat-card" style="border-left-color: #09090B"><div class="stat-label">Public Sanctioned</div><div class="stat-val">₹{df["budget_allocated"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="stat-card" style="border-left-color: #EA580C"><div class="stat-label">Treasury Disbursed</div><div class="stat-val">₹{df["amount_spent"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="stat-card" style="border-left-color: #10B981"><div class="stat-label">Verified Resolutions</div><div class="stat-val" style="color:#10B981">{len(df[df["status"].str.contains("Resolved", na=False)])}</div></div>', unsafe_allow_html=True)

        st.write("<br>", unsafe_allow_html=True)
        tab_live, tab_audit = st.tabs(["📋 Live Grievance Registry", "📸 Immutable Social Audit Feed"])
        
        with tab_live:
            for _, item in df.iterrows():
                loc_str = fetch_address(item["lat"], item["lon"])
                date_str = item["timestamp_dt"].strftime("%d %b %Y, %H:%M") if pd.notna(item["timestamp_dt"]) else "—"
                is_resolved = "Resolved" in str(item["status"])
                
                st.markdown(f"""
                    <div class="dpi-card {'dpi-card--emerald' if is_resolved else 'dpi-card--saffron'}">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                            <div><span class="mono-hash" style="color:white;">{item['id']}</span> <span style="margin-left:10px">{render_status_badge(item['status'])}</span></div>
                            <span style="font-size:12px;color:#71717A;font-family:'JetBrains Mono';">📅 {date_str}</span>
                        </div>
                        <div style="font-size:16px;font-weight:600;margin-bottom:6px;">{item['raw_text']}</div>
                        <div style="font-size:13px;color:#71717A;margin-bottom:16px;">📍 {loc_str}</div>
                        <div style="display:flex;gap:24px;font-size:13px;border-top:1px solid #E4E4E7;padding-top:12px;">
                            <div><span style="color:#71717A">Sector:</span> <b>{item['category']}</b></div>
                            <div><span style="color:#71717A">Office:</span> <b>{item['office_name']}</b></div>
                            <div><span style="color:#71717A">Budget:</span> <b>₹{item['budget_allocated']:,.0f}</b></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # BUG FIX: Strict explicit logic for images (kills the Streamlit text bug)
                c_url = get_telegram_url(item.get("media_file_id"))
                if is_resolved:
                    st.markdown("**📸 Resolution Evidence**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption("🔴 Citizen Report")
                        if c_url: st.image(c_url, use_container_width=True)
                        else: st.info("No initial media.")
                    with col2:
                        st.caption("🟢 Official Govt Resolution")
                        r_url = get_telegram_url(item.get("resolution_media_id"))
                        if r_url: st.image(r_url, use_container_width=True)
                        else: st.info("Resolution verified without photo.")
                else:
                    with st.expander(f"📎 View Citizen Evidence — {item['id']}"):
                        if c_url: st.image(c_url, use_container_width=True)
                        else: st.write("No media attached by citizen.")
                st.markdown("<br>", unsafe_allow_html=True)

        with tab_audit:
            resolved_df = df[df["status"].str.contains("Resolved", na=False)]
            if resolved_df.empty: 
                st.info("No resolved grievances yet.")
            else:
                for _, r in resolved_df.iterrows():
                    h_val = r.get("audit_hash") or get_audit_hash(r["id"], r["amount_spent"])
                    st.markdown(f"""
                        <div class="dpi-card dpi-card--emerald">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                                <span style="font-weight:700;font-size:16px;">{r['category']} — {r['office_name']}</span>
                                <span class="badge live-pulse">✅ AUDITED</span>
                            </div>
                            <div style="font-size:14px;line-height:1.6;color:#52525B;">
                                <b>Bill of Quantities:</b> {r.get('materials_used', 'Standard operations.')}<br>
                                <b>Fiscal Audit:</b> Sanctioned ₹{r['budget_allocated']:,.0f} &nbsp;|&nbsp; Final Treasury Payout: <b style="color:#10B981">₹{r['amount_spent']:,.0f}</b><br>
                                <span class="mono-hash" style="margin-top:8px;display:inline-block;">🛡️ SHA-256: 0x{h_val}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    col_b, col_a = st.columns(2)
                    with col_b:
                        b_url = get_telegram_url(r.get("media_file_id"))
                        if b_url: st.image(b_url, use_container_width=True, caption="Before")
                    with col_a:
                        a_url = get_telegram_url(r.get("resolution_media_id"))
                        if a_url: st.image(a_url, use_container_width=True, caption="After (Resolved)")
                    st.markdown("<hr style='margin:2rem 0;'>", unsafe_allow_html=True)

# ==========================================
# PAGE 2: OPEN DATA LEDGER
# ==========================================
elif page == "📊 Open Data Ledger":
    st.markdown("<h1>National Open Data Ledger</h1>", unsafe_allow_html=True)
    if df.empty: st.warning("No data available yet.")
    else:
        # 1. Sector-Wise Fiscal Ledger (Full Width)
        st.markdown('<div class="dpi-card" style="border-top-color:#09090B;"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;"><span style="font-size:13px;font-weight:700;text-transform:uppercase;color:#71717A;">🏛️ Sector-wise Fiscal Ledger</span><span class="badge live-pulse">LIVE AUDIT</span></div>', unsafe_allow_html=True)
        fiscal_df = df.groupby("category", as_index=False)[["budget_allocated", "amount_spent"]].sum()
        fig_fiscal = go.Figure()
        fig_fiscal.add_trace(go.Bar(name="Sanctioned Budget", x=fiscal_df["category"], y=fiscal_df["budget_allocated"], marker_color="#09090B"))
        fig_fiscal.add_trace(go.Bar(name="Disbursed (Spent)", x=fiscal_df["category"], y=fiscal_df["amount_spent"], marker_color="#10B981"))
        fig_fiscal.update_layout(barmode="group", height=350, **get_plotly_layout())
        st.plotly_chart(fig_fiscal, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

        # 2. Split Dashboards
        col_l, col_r = st.columns(2)
        color_map = {"Roads": "#09090B", "Sanitation": "#10B981", "Water": "#2563EB", "Electricity": "#EA580C", "Civil": "#71717A", "Cyber Crime": "#E11D48"}
        
        with col_l:
            st.markdown('<div class="dpi-card" style="border-top-color:#09090B;"><div class="stat-label" style="margin-bottom:15px;">Grievances by Sector</div>', unsafe_allow_html=True)
            pie_data = df["category"].value_counts()
            colors = [color_map.get(cat, "#A1A1AA") for cat in pie_data.index]
            fig_pie = go.Figure(go.Pie(labels=pie_data.index, values=pie_data.values, hole=0.5, marker_colors=colors))
            fig_pie.update_layout(height=320, **get_plotly_layout())
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_r:
            st.markdown('<div class="dpi-card" style="border-top-color:#09090B;"><div class="stat-label" style="margin-bottom:15px;">Lifecycle Pipeline</div>', unsafe_allow_html=True)
            status_counts = df["status"].value_counts().reset_index()
            bar_colors = ["#10B981" if "Resolved" in s else ("#EA580C" if "Pending" in s else "#2563EB") for s in status_counts["status"]]
            fig_bar = go.Figure(go.Bar(x=status_counts["status"], y=status_counts["count"], marker_color=bar_colors))
            fig_bar.update_layout(height=320, **get_plotly_layout())
            st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# PAGE 3: MAP
# ==========================================
elif page == "📍 Live Incident Map":
    st.markdown("<h1>Live Geospatial Incident Map</h1>", unsafe_allow_html=True)
    if not df.empty and not df["lat"].isnull().all():
        st.markdown('<div class="dpi-card" style="padding:4px; border-top-color:#2563EB;">', unsafe_allow_html=True)
        map_data = df.dropna(subset=["lat", "lon"]).rename(columns={"lat": "latitude", "lon": "longitude"})
        st.map(map_data, zoom=11, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else: st.warning("No geospatial telemetry available yet.")

# ==========================================
# PAGE 4: LOGIN
# ==========================================
elif page == "🔐 Officer Gateway":
    st.markdown("<h1>Secure Authentication Gateway</h1><p style='color:#71717A;font-size:14px;margin-bottom:2rem;'>GovID credentials are issued by the NIC.</p>", unsafe_allow_html=True)
    if time.time() < st.session_state.lockout_time:
        st.error(f"🚨 Security Lockout Active. Retry in **{int(st.session_state.lockout_time - time.time())}s**.")
    else:
        _, col_center, _ = st.columns([1, 1.2, 1])
        with col_center:
            st.markdown('<div class="dpi-card dpi-card--saffron" style="padding:40px 30px;"><div style="text-align:center;margin-bottom:24px"><span style="font-size:36px">🔐</span><br><b style="font-size:20px;">GovID Secure Login</b><br><span style="font-size:11px;color:#71717A;text-transform:uppercase;letter-spacing:1px;">National Informatics Centre</span></div>', unsafe_allow_html=True)
            with st.form("auth_form"):
                uid = st.text_input("Username", placeholder="e.g. collector")
                pwd = st.text_input("Passkey", type="password", placeholder="GovID credential")
                st.write("")
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

# ==========================================
# PAGE 5: COMMAND DASHBOARD
# ==========================================
elif page == "⚙️ Command Dashboard":
    st.markdown(f"<h1>Command Dashboard — {st.session_state.dept.upper()}</h1>", unsafe_allow_html=True)
    if df.empty: st.info("No complaints found in the system.")
    else:
        active_df = (df[df["category"].str.contains(st.session_state.dept, case=False, na=False)] if st.session_state.role == "field" else df)[~df["status"].str.contains("Resolved", na=False)]
        
        if active_df.empty:
            st.markdown('<div class="dpi-card dpi-card--emerald" style="text-align:center;padding:40px;"><span style="font-size:40px">✅</span><br><b style="font-size:18px">All queues are clear.</b></div>', unsafe_allow_html=True)
        else:
            sel_id = st.selectbox("Select Grievance to Action:", active_df["id"].tolist())
            row = active_df[active_df["id"] == sel_id].iloc[0]
            
            st.markdown(f"""
                <div class="dpi-card dpi-card--saffron">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
                        <span class="mono-hash" style="color:white;font-size:16px;">{row['id']}</span>
                        {render_status_badge(row['status'])}
                    </div>
                    <div style="font-size:16px;font-weight:600;margin-bottom:8px;">{row['raw_text']}</div>
                    <div style="font-size:14px;color:#71717A;margin-bottom:16px;">📍 {fetch_address(row['lat'], row['lon'])}</div>
                </div>
            """, unsafe_allow_html=True)

            if st.session_state.role == "admin":
                st.markdown('<div class="dpi-card dpi-card--azure"><h3 style="margin-top:0;">⚙️ Administrative Sanction Panel</h3>', unsafe_allow_html=True)
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

                    st.write("")
                    if st.form_submit_button("🔒 Lock Sanction & Dispatch", type="primary", use_container_width=True):
                        execute_admin_sanction(sel_id, n_stage, b_alloc, contractor, s_dept, t_office, t_officer)
                        if pd.notna(row["chat_id"]) and BOT_TOKEN:
                            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": row["chat_id"], "text": f"🇮🇳 *Govt Update*\nTicket `{sel_id}` routed to *{t_office}*.\n🚥 Stage: {n_stage}\n💰 Sanctioned: ₹{b_alloc:,.0f}", "parse_mode": "Markdown"}, timeout=5)
                            except: pass
                        st.cache_data.clear()
                        st.success("✅ Sanction locked and dispatched.")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            elif st.session_state.role == "field":
                st.markdown('<div class="dpi-card dpi-card--emerald"><h3 style="margin-top:0;">🔧 Field Resolution Panel</h3>', unsafe_allow_html=True)
                st.info(f"💰 **Locked Budget:** ₹{row['budget_allocated']:,.0f} | **Contractor:** {row.get('contractor_name') or 'Internal'}")
                with st.form("field_form"):
                    materials = st.text_area("Measurement Book (BOQ & Materials Used):")
                    spent = st.number_input("Final Treasury Payout (₹):", value=float(row["budget_allocated"]), step=1000.0, min_value=0.0)
                    proof = st.file_uploader("Upload Official Resolution Photograph:", type=["jpg", "jpeg", "png"])

                    st.write("")
                    if st.form_submit_button("📤 Submit Resolution Proof", type="primary", use_container_width=True):
                        if not proof: st.error("❌ Resolution photograph is mandatory.")
                        else:
                            m_id = None
                            if pd.notna(row["chat_id"]) and BOT_TOKEN:
                                try:
                                    res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": row["chat_id"], "caption": f"✅ *Resolved*\nTicket: `{sel_id}`\nTreasury Payout: ₹{spent:,.0f}\nAudited by: {row['assigned_officer']}", "parse_mode": "Markdown"}, files={"photo": proof.getvalue()}, timeout=10).json()
                                    if res.get("ok"): m_id = res["result"]["photo"][-1]["file_id"]
                                except: pass
                            execute_field_resolution(sel_id, spent, materials, m_id)
                            st.cache_data.clear()
                            st.success("✅ Work verified.")
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)