import os
import time
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from backend import get_all_complaints, execute_admin_sanction, execute_field_resolution
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="JanSeva DPI - National Grievance", layout="wide", page_icon="🏛️")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ==========================================
# 🎨 THE DESIGN SYSTEM (STABLE)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600;700&family=Space+Grotesk:wght@400;600;700&display=swap');
    
    .stApp { background-color: #F1F3F5; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: #111827 !important; text-transform: uppercase; letter-spacing: -0.5px; }
    p, span, div, label { font-family: 'Space Grotesk', sans-serif; }
    
    header[data-testid="stHeader"] { display: none !important; }
    
    .dpi-card {
        background: #FFFFFF;
        border: 2px solid #111827;
        border-radius: 0px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 4px 4px 0px #111827;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .dpi-card:hover { transform: translate(-2px, -2px); box-shadow: 6px 6px 0px #111827; }
    
    .ledger-data { font-family: 'IBM Plex Mono', monospace !important; font-size: 32px; font-weight: 700; color: #111827; margin-top: 8px; }
    .ledger-label { font-size: 13px; text-transform: uppercase; font-weight: 700; color: #4B5563; letter-spacing: 1px; }
    
    .status-badge { font-family: 'IBM Plex Mono', monospace !important; display: inline-block; padding: 4px 10px; font-size: 12px; font-weight: 700; text-transform: uppercase; border: 1px solid #111827; box-shadow: 2px 2px 0px #111827; }
    .badge-pending { background-color: #FEF08A; color: #854D0E; }
    .badge-progress { background-color: #BAE6FD; color: #0369A1; }
    .badge-resolved { background-color: #A7F3D0; color: #065F46; }
    
    .evidence-box { border: 2px solid #111827; padding: 10px; background: #F8FAFC; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 STATE MANAGEMENT & ROUTING
# ==========================================
if "role" not in st.session_state: st.session_state.role = "public"
if "dept" not in st.session_state: st.session_state.dept = None
if "login_attempts" not in st.session_state: st.session_state.login_attempts = 0
if "lockout_time" not in st.session_state: st.session_state.lockout_time = 0

DEPT_DIRECTORY = {
    "Roads": {"office": "State PWD Roads Division", "officer": "Er. R. Varma, JE"},
    "Water": {"office": "Municipal Water Board", "officer": "Er. K. Ramesh, AEE"},
    "Electricity": {"office": "State DISCOM", "officer": "Er. M. Praveen, SDE"},
    "Sanitation": {"office": "Solid Waste Management", "officer": "Dr. A. Rao, CSI"},
    "Cyber Crime": {"office": "Cyber Investigation Cell", "officer": "Inspector S. Reddy"},
    "Civil": {"office": "Municipal Zonal Office", "officer": "Er. P. Naidu, EE"}
}

AUTH_DB = {
    "collector": {"pass": "ias@india2026", "role": "admin", "dept": "All"},
    "pwd_roads": {"pass": "pwd@infra2026", "role": "field", "dept": "Roads"},
    "water_board": {"pass": "jal@clean2026", "role": "field", "dept": "Water"},
    "electricity": {"pass": "power@grid2026", "role": "field", "dept": "Electricity"},
    "cyber_cop": {"pass": "cyber@cell2026", "role": "field", "dept": "Cyber Crime"},
    "sanitation": {"pass": "swm@clean2026", "role": "field", "dept": "Sanitation"}
}

def get_telegram_url(file_id):
    if not file_id or str(file_id).lower() in {"none", "nan", ""}: return None
    try:
        res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=4).json()
        if res.get("ok"): return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{res['result']['file_path']}"
    except: pass
    return None

@st.cache_data(ttl=86400)
def fetch_address(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return "GPS Location Not Provided"
    try:
        res = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={'User-Agent': 'JanSeva_Hackathon'}, timeout=3).json()
        return f"{res.get('display_name', 'Address resolution failed')} — <a href='https://maps.google.com/?q={lat},{lon}' target='_blank'>[Map]</a>"
    except: return f"Coordinates: {lat}, {lon}"

def render_status_badge(status):
    if not status: return ""
    if "Resolved" in status: return f'<span class="status-badge badge-resolved">{status}</span>'
    elif "Pending" in status: return f'<span class="status-badge badge-pending">{status}</span>'
    return f'<span class="status-badge badge-progress">{status}</span>'

# ==========================================
# 📱 SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=60)
    st.markdown("<h2 style='font-size:20px; margin-top:10px;'>JanSeva DPI</h2>", unsafe_allow_html=True)
    st.divider()
    
    if st.session_state.role == "public":
        page = st.radio("Navigation", ["🌐 Public Transparency Portal", "📍 Geospatial Incident Map", "🔐 Officer Gateway"])
    else:
        st.success(f"**Role:** {st.session_state.role.upper()}\n\n**Dept:** {st.session_state.dept}")
        page = st.radio("Navigation", ["⚙️ Officer Command Dashboard", "🌐 Public Transparency Portal"])
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.role = "public"
            st.session_state.dept = None
            st.rerun()

# Load Data
records = get_all_complaints()
df = pd.DataFrame(records) if records else pd.DataFrame()
if not df.empty:
    df['budget_allocated'] = pd.to_numeric(df.get('budget_allocated', 0)).fillna(0)
    df['amount_spent'] = pd.to_numeric(df.get('amount_spent', 0)).fillna(0)
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')

# ==========================================
# PAGE 1: PUBLIC TRANSPARENCY
# ==========================================
if page == "🌐 Public Transparency Portal":
    st.title("Citizens' Social Audit Ledger")
    
    if not df.empty:
        total_sanctioned = df['budget_allocated'].sum()
        total_spent = df['amount_spent'].sum()
        resolved_count = len(df[df['status'].str.contains("Resolved", na=False)])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="dpi-card"><div class="ledger-label">Total Logged</div><div class="ledger-data">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="dpi-card"><div class="ledger-label">Funds Sanctioned</div><div class="ledger-data">₹{total_sanctioned:,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="dpi-card"><div class="ledger-label">Actual Spent</div><div class="ledger-data">₹{total_spent:,.0f}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="dpi-card"><div class="ledger-label">Verified Resolved</div><div class="ledger-data" style="color:#059669;">{resolved_count}</div></div>', unsafe_allow_html=True)
        
        # --- PLOTLY GRAPH INJECTED SAFELY HERE ---
        st.markdown('<div class="dpi-card"><div class="ledger-label">SECTOR-WISE FISCAL LEDGER</div>', unsafe_allow_html=True)
        fiscal_df = df.groupby("category", as_index=False)[["budget_allocated", "amount_spent"]].sum()
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Sanctioned", x=fiscal_df["category"], y=fiscal_df["budget_allocated"], marker_color="#111827"))
        fig.add_trace(go.Bar(name="Spent", x=fiscal_df["category"], y=fiscal_df["amount_spent"], marker_color="#059669"))
        fig.update_layout(barmode="group", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family='Space Grotesk', color='#111827'), margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

        tab_all, tab_resolved = st.tabs(["📋 Registered Grievances", "📸 Verified Proof Feed"])
        
        with tab_all:
            for _, item in df.iterrows():
                time_str = item['timestamp_dt'].strftime('%d %b %Y, %I:%M %p') if pd.notna(item['timestamp_dt']) else str(item['timestamp'])[:16]
                loc_str = fetch_address(item['lat'], item['lon'])
                
                st.markdown(f"""
                    <div class="dpi-card">
                        <div style="display:flex; justify-content:space-between; margin-bottom: 10px;">
                            <span style="font-family:'IBM Plex Mono', monospace; font-size:18px; font-weight:700;">#{item['id']}</span>
                            {render_status_badge(item['status'])}
                        </div>
                        <div style="font-size:16px; font-weight:600; margin-bottom: 8px;">{item['raw_text']}</div>
                        <div style="font-size:14px; color:#4B5563; margin-bottom: 15px;">📍 {loc_str}</div>
                        <div style="display:flex; flex-wrap:wrap; gap:15px; border-top:2px solid #E5E7EB; padding-top:10px;">
                            <div class="ledger-label">Dept: <span style="color:#111827;">{item.get('category', 'Civil')}</span></div>
                            <div class="ledger-label">Officer: <span style="color:#111827;">{item.get('assigned_officer', 'Pending')}</span></div>
                            <div class="ledger-label">Sanctioned: <span style="color:#111827;">₹{item['budget_allocated']:,.0f}</span></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"Inspect Media for #{item['id']}"):
                    m_url = get_telegram_url(item.get('media_file_id'))
                    if m_url:
                        if str(item.get('media_type')) == 'photo': st.image(m_url, width=400)
                        else: st.video(m_url)
                    else: st.write("No media attached.")

        with tab_resolved:
            resolved_subset = df[df['status'].str.contains("Resolved", na=False)]
            if not resolved_subset.empty:
                for _, r in resolved_subset.iterrows():
                    res_time = str(r.get('resolved_at'))[:16] if pd.notna(r.get('resolved_at')) else "Completed"
                    loc_str = fetch_address(r['lat'], r['lon'])
                    
                    st.markdown(f"""
                        <div class="dpi-card">
                            <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                                <span style="font-weight:700; font-size:18px;">{r.get('category', 'Civil')} — {r.get('office_name', 'Office')}</span>
                                <span class="status-badge badge-resolved">✅ Resolved {res_time}</span>
                            </div>
                            <div style="margin-bottom:15px;">
                                <b>Issue:</b> {r['raw_text']}<br>
                                <b>Location:</b> {loc_str}<br>
                                <b>BOQ/Materials:</b> {r.get('materials_used', 'Standard Specs')}
                            </div>
                            <div style="font-family:'IBM Plex Mono', monospace; font-size:16px;">
                                Sanctioned: ₹{r['budget_allocated']:,.0f} &nbsp;|&nbsp; <b>Spent: ₹{r['amount_spent']:,.0f}</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    c_before, c_after = st.columns(2)
                    with c_before:
                        st.markdown('<div class="evidence-box"><div class="ledger-label">1. Citizen Complaint</div>', unsafe_allow_html=True)
                        b_url = get_telegram_url(r.get('media_file_id'))
                        if b_url: st.image(b_url, use_container_width=True)
                        else: st.caption("No photo attached")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c_after:
                        st.markdown('<div class="evidence-box"><div class="ledger-label">2. Gov Repair Proof</div>', unsafe_allow_html=True)
                        a_url = get_telegram_url(r.get('resolution_media_id'))
                        if a_url: st.image(a_url, use_container_width=True)
                        else: st.caption("No photo attached")
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.write("---")
            else:
                st.info("No grievances resolved yet.")
    else:
        st.info("No data available.")

# ==========================================
# PAGE 2: SECURE OFFICER LOGIN
# ==========================================
elif page == "🔐 Officer Gateway":
    st.title("Administrative Access Gateway")
    
    if time.time() < st.session_state.lockout_time:
        st.error(f"🚨 Lockout Active. Wait {int(st.session_state.lockout_time - time.time())} seconds.")
    else:
        c_left, c_mid, c_right = st.columns([1, 1.5, 1])
        with c_mid:
            st.markdown('<div class="dpi-card">', unsafe_allow_html=True)
            st.markdown("<h3>Officer Verification</h3>", unsafe_allow_html=True)
            with st.form("auth"):
                uid = st.text_input("GovID (Username)")
                pwd = st.text_input("Passkey (Password)", type="password")
                if st.form_submit_button("Access Portal", use_container_width=True):
                    if uid in AUTH_DB and AUTH_DB[uid]["pass"] == pwd:
                        st.session_state.role = AUTH_DB[uid]["role"]
                        st.session_state.dept = AUTH_DB[uid]["dept"]
                        st.session_state.login_attempts = 0
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        if st.session_state.login_attempts >= 3:
                            st.session_state.lockout_time = time.time() + 60
                            st.session_state.login_attempts = 0
                            st.rerun()
                        else: st.error(f"Access Denied ({st.session_state.login_attempts}/3)")
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# PAGE 3: MAP
# ==========================================
elif page == "📍 Geospatial Incident Map":
    st.title("Live Geospatial Incident Map")
    if not df.empty and not df['lat'].isnull().all():
        map_df = df.dropna(subset=['lat', 'lon']).rename(columns={"lat": "latitude", "lon": "longitude"})
        st.map(map_df, zoom=11)
    else: st.warning("No GPS data available yet.")

# ==========================================
# PAGE 4: OFFICER DASHBOARD
# ==========================================
elif page == "⚙️ Officer Command Dashboard":
    st.title(f"Command Dashboard — {st.session_state.dept.upper()}")
    
    if not df.empty:
        working_df = df[df['category'].str.contains(st.session_state.dept, case=False, na=False)] if st.session_state.role == "field" else df.copy()
        active_df = working_df[~working_df['status'].str.contains("Resolved", na=False)]
        
        if not active_df.empty:
            sel_id = st.selectbox("Select Active Grievance:", active_df["id"].tolist())
            row = active_df[active_df["id"] == sel_id].iloc[0]
            loc_str = fetch_address(row['lat'], row['lon'])
            
            st.markdown(f"""
                <div class="dpi-card">
                    <h3>Ticket #{row['id']}</h3>
                    <p><b>Issue:</b> {row['raw_text']}</p>
                    <p><b>Location:</b> {loc_str}</p>
                    <p><b>Category:</b> {row.get('category')} | <b>Office:</b> {row.get('office_name')}</p>
                    <p><b>Status:</b> {render_status_badge(row['status'])}</p>
                </div>
            """, unsafe_allow_html=True)
            
            c_url = get_telegram_url(row.get('media_file_id'))
            if c_url: st.image(c_url, width=350, caption="Citizen Submitted Photograph")
            
            # --- TIER A: ADMIN (COLLECTOR) ---
            if st.session_state.role == "admin":
                st.markdown("<h3>🏛️ Route & Sanction</h3>", unsafe_allow_html=True)
                with st.form("admin_form"):
                    current_cat = row.get('category', 'Civil')
                    d_keys = list(DEPT_DIRECTORY.keys())
                    sel_dept = st.selectbox("Route to Department:", d_keys, index=d_keys.index(current_cat) if current_cat in d_keys else 0)
                    
                    c_d1, c_d2 = st.columns(2)
                    with c_d1: t_office = st.text_input("Designated Office:", value=DEPT_DIRECTORY[sel_dept]["office"])
                    with c_d2: t_officer = st.text_input("Assigned Officer:", value=DEPT_DIRECTORY[sel_dept]["officer"])
                    
                    c_s1, c_s2 = st.columns(2)
                    with c_s1: stage = st.selectbox("Advance Stage:", ["2. Survey", "3. Admin Sanction", "4. Tender Awarded"])
                    with c_s2: budget = st.number_input("Sanction Budget (₹):", value=float(row['budget_allocated']), step=5000.0)
                    contractor = st.text_input("Contractor:", value=str(row.get('contractor_name', '')))
                    
                    if st.form_submit_button("Lock Sanction & Dispatch", use_container_width=True):
                        execute_admin_sanction(sel_id, stage, budget, contractor, sel_dept, t_office, t_officer)
                        if pd.notna(row['chat_id']) and BOT_TOKEN:
                            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": row['chat_id'], "text": f"🏛️ Ticket `{sel_id}` routed to {t_office}. Budget: ₹{budget:,.0f}"})
                            except: pass
                        st.success("Ticket dispatched successfully!")
                        st.rerun()

            # --- TIER B: FIELD OFFICER ---
            elif st.session_state.role == "field":
                st.markdown("<h3>👷 Execution & Measurement</h3>", unsafe_allow_html=True)
                st.info(f"💰 Sanction Budget: ₹{row['budget_allocated']:,.0f} | Contractor: {row.get('contractor_name', 'Dept Work')}")
                
                with st.form("field_form"):
                    materials = st.text_area("Measurement Book (Materials Used):")
                    spent = st.number_input("Amount Spent (₹):", value=float(row['budget_allocated']), step=1000.0)
                    proof = st.file_uploader("Upload Resolution Proof:", type=['jpg', 'jpeg', 'png'])
                    
                    if st.form_submit_button("Submit & Resolve", use_container_width=True):
                        if not proof: st.error("Proof photo is required.")
                        else:
                            m_id = None
                            if pd.notna(row['chat_id']) and BOT_TOKEN:
                                try:
                                    res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": row['chat_id'], "caption": f"✅ Ticket `{sel_id}` Resolved!\nCost: ₹{spent:,.0f}\nBOQ: {materials}"}, files={"photo": proof.getvalue()}).json()
                                    if res.get("ok"): m_id = res["result"]["photo"][-1]["file_id"]
                                except: pass
                            execute_field_resolution(sel_id, spent, materials, m_id)
                            st.success("Work verified and published to Public Audit.")
                            st.rerun()
        else: st.success("No pending grievances in your jurisdiction.")
    else: st.info("No complaints found.")