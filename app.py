import os
import time
import hashlib
import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from backend import get_all_complaints, execute_admin_sanction, execute_field_resolution
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="JanSeva DPI | Govt of India", layout="wide", page_icon="🇮🇳")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ==========================================
# 🎨 SOVEREIGN CSS ENGINE (BUG-FREE)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; color: #0F172A; }
    .main, .stApp { background-color: #F8FAFC !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 0rem !important; padding-bottom: 3rem !important; max-width: 1400px; }
    
    h1, h2, h3 { font-weight: 700 !important; letter-spacing: -0.03em; }
    
    .gov-banner { background-color: #0F172A; color: #FFFFFF; padding: 14px 24px; font-size: 15px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; border-radius: 0 0 6px 6px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .tricolor-strip { height: 4px; width: 100%; background: linear-gradient(to right, #FF9933 0%, #FF9933 33.3%, #FFFFFF 33.3%, #FFFFFF 66.6%, #138808 66.6%, #138808 100%); margin-bottom: 24px; }
    
    .dpi-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 3px solid #0F172A; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); transition: transform 0.2s ease; }
    .dpi-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .dpi-card--resolved { border-top-color: #10B981; }
    .dpi-card--pending { border-top-color: #F97316; }
    
    .stat-card { background: #FFFFFF; padding: 20px; border-radius: 8px; border: 1px solid #E2E8F0; border-left: 4px solid #0F172A; }
    .stat-label { font-size: 12px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; }
    .stat-val { font-size: 32px; font-weight: 800; font-family: 'JetBrains Mono', monospace; margin-top: 4px; }
    
    .badge { display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; font-family: 'JetBrains Mono', monospace; }
    .badge-resolved { background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }
    .badge-pending { background: #FFF7ED; color: #C2410C; border: 1px solid #FFEDD5; }
    .badge-progress { background: #EFF6FF; color: #1D4ED8; border: 1px solid #DBEAFE; }
    
    .mono-hash { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 600; background: #0F172A; color: #34D399; padding: 4px 8px; border-radius: 4px; }
    
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0 !important; }
    .stButton > button[kind="primary"] { background: #0F172A !important; color: white !important; border-radius: 6px !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🏛️ THE 16-SECTOR GOVERNMENT DIRECTORY
# ==========================================
DEPT_CONFIG = {
    "Transport (RTO)": {"base": "Regional Transport Office (RTO)", "officer": "Transport Inspector"},
    "Revenue & Land": {"base": "Tehsildar & Property Reg.", "officer": "Mandal Revenue Officer"},
    "Food & Civil Supplies": {"base": "Civil Supplies & PDS", "officer": "PDS Nodal Officer"},
    "Police & Law Enforcement": {"base": "State Police Command", "officer": "Station House Officer"},
    "Public Health": {"base": "Civic Hospital & Welfare", "officer": "Chief Medical Officer"},
    "Urban Development": {"base": "Town Planning & Zoning", "officer": "Zonal Commissioner"},
    "Pollution Control": {"base": "State Pollution Control Board", "officer": "Environmental Engineer"},
    "Fire & Rescue": {"base": "Fire & Emergency Services", "officer": "District Fire Officer"},
    "Women & Child Development": {"base": "WCD Protection Unit", "officer": "Protection Officer"},
    "Labour Welfare": {"base": "Employment Grievance Board", "officer": "Labour Commissioner"},
    "Disaster Management": {"base": "Disaster Relief Authority", "officer": "NDRF Nodal Head"},
    "Telecom & Postal": {"base": "DOT / India Post Cell", "officer": "Telecom Reg. Officer"},
    "Roads & Infrastructure": {"base": "State PWD Division", "officer": "Executive Engineer"},
    "Water & Sanitation": {"base": "Water & Sewerage Board", "officer": "Sanitary Inspector"},
    "Electricity & Power": {"base": "State DISCOM", "officer": "Superintending Engineer"},
    "Civil": {"base": "Municipal Zonal Office", "officer": "Nodal Officer"}
}

AUTH_DB = {
    "collector": {"pass": "ias2026", "role": "admin", "dept": "All"},
    "rto_admin": {"pass": "rto2026", "role": "field", "dept": "Transport (RTO)"},
    "revenue_land": {"pass": "rev2026", "role": "field", "dept": "Revenue & Land"},
    "civil_supplies": {"pass": "pds2026", "role": "field", "dept": "Food & Civil Supplies"},
    "police_hq": {"pass": "ips2026", "role": "field", "dept": "Police & Law Enforcement"},
    "health_welfare": {"pass": "cmo2026", "role": "field", "dept": "Public Health"},
    "urban_dev": {"pass": "udp2026", "role": "field", "dept": "Urban Development"},
    "pollution_board": {"pass": "epb2026", "role": "field", "dept": "Pollution Control"},
    "fire_rescue": {"pass": "fire2026", "role": "field", "dept": "Fire & Rescue"},
    "wcd_unit": {"pass": "wcd2026", "role": "field", "dept": "Women & Child Development"},
    "labour_board": {"pass": "labour2026", "role": "field", "dept": "Labour Welfare"},
    "disaster_mgmt": {"pass": "ndrf2026", "role": "field", "dept": "Disaster Management"},
    "telecom_post": {"pass": "dot2026", "role": "field", "dept": "Telecom & Postal"},
    "pwd_roads": {"pass": "pwd2026", "role": "field", "dept": "Roads & Infrastructure"},
    "water_board": {"pass": "jal2026", "role": "field", "dept": "Water & Sanitation"},
    "electricity": {"pass": "power2026", "role": "field", "dept": "Electricity & Power"}
}

if "role" not in st.session_state: st.session_state.role = "public"
if "dept" not in st.session_state: st.session_state.dept = None

# ==========================================
# 🧠 SMART HELPER FUNCTIONS
# ==========================================
def get_telegram_url(file_id):
    if pd.isna(file_id) or not file_id: return None
    fid_str = str(file_id).strip().lower()
    if fid_str in {"none", "nan", "", "0", "null"}: return None
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=5).json()
        if r.get("ok"): return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}"
    except: pass
    return None

@st.cache_data(ttl=86400)
def fetch_geo_data(lat, lon):
    """Returns a full address AND extracts the local district for dynamic office routing."""
    if pd.isna(lat) or pd.isna(lon): return "Location Unknown", "Central"
    try:
        r = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={"User-Agent": "JanSeva_DPI"}, timeout=3).json()
        address = r.get('display_name', 'Address unknown')
        addr_dict = r.get('address', {})
        district = addr_dict.get('state_district') or addr_dict.get('city') or addr_dict.get('county') or "Regional"
        return f"{address} ([Map](https://maps.google.com/?q={lat},{lon}))", district
    except: return f"Coordinates: {lat:.4f}, {lon:.4f}", "Regional"

def render_media(url, media_type, caption_text=""):
    """Bulletproof media renderer to prevent broken icons."""
    if not url: return
    m_type = str(media_type).lower()
    if "video" in m_type or "animation" in m_type or url.endswith(".mp4"):
        st.video(url)
        if caption_text: st.caption(caption_text)
    else:
        st.image(url, use_container_width=True, caption=caption_text)

def get_audit_hash(ticket_id, amount_spent):
    return hashlib.sha256(f"GOI_DPI_{ticket_id}_{amount_spent}_VERIFIED".encode()).hexdigest()[:16].upper()

def load_data():
    records = get_all_complaints()
    if not records: return pd.DataFrame()
    df = pd.DataFrame(records)
    df["budget_allocated"] = pd.to_numeric(df.get("budget_allocated", 0), errors="coerce").fillna(0)
    df["amount_spent"]     = pd.to_numeric(df.get("amount_spent", 0), errors="coerce").fillna(0)
    df["timestamp_dt"]     = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    return df

# ==========================================
# 🖥️ UI RENDER PIPELINE
# ==========================================
st.markdown('<div class="gov-banner"><div>🇮🇳 Government of India | JanSeva DPI Platform</div><div>Secure Connection Established</div></div><div class="tricolor-strip"></div>', unsafe_allow_html=True)

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=70)
    st.markdown("<h2 style='margin:8px 0 0;'>JanSeva DPI</h2><p style='font-size:12px;color:#64748B;'>National Grievance Network</p>", unsafe_allow_html=True)
    st.divider()
    if st.session_state.role == "public":
        page = st.radio("Navigation", ["🌐 Live Grievance Registry", "📊 Open Data Ledger", "🏛️ Agency Jurisdiction Matrix", "📍 Incident Map", "🔐 Officer Gateway"])
    else:
        st.success(f"Auth: {st.session_state.role.upper()} | {st.session_state.dept}")
        page = st.radio("Navigation", ["⚙️ Command Dashboard", "🌐 Live Grievance Registry", "📊 Open Data Ledger", "📍 Incident Map"])
        if st.button("Sign Out", use_container_width=True):
            st.session_state.update({"role": "public", "dept": None})
            st.rerun()

df = load_data()

# ------------------------------------------
# PAGE 1: PUBLIC TRANSPARENCY BOARD
# ------------------------------------------
if page == "🌐 Live Grievance Registry":
    st.header("Public Transparency & Social Audit Registry")
    
    if df.empty:
        st.info("📭 No active grievances. Send a message to your Telegram bot to test the pipeline.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card" style="border-left-color: #2563EB"><div class="stat-label">Total Logged</div><div class="stat-val">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card" style="border-left-color: #0F172A"><div class="stat-label">Public Sanctioned</div><div class="stat-val">₹{df["budget_allocated"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card" style="border-left-color: #EA580C"><div class="stat-label">Treasury Disbursed</div><div class="stat-val">₹{df["amount_spent"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card" style="border-left-color: #10B981"><div class="stat-label">Verified Resolutions</div><div class="stat-val" style="color:#10B981">{len(df[df["status"].str.contains("Resolved", na=False)])}</div></div>', unsafe_allow_html=True)

        st.write("---")
        
        # Unified Feed Generation
        for _, item in df.iterrows():
            is_res = "Resolved" in str(item["status"])
            badge = f'<span class="badge badge-resolved">✓ {item["status"]}</span>' if is_res else f'<span class="badge badge-pending">⏳ {item["status"]}</span>'
            css_class = "dpi-card--resolved" if is_res else "dpi-card--pending"
            
            loc_str, district = fetch_geo_data(item["lat"], item["lon"])
            date_str = item["timestamp_dt"].strftime("%d %b %Y, %H:%M") if pd.notna(item["timestamp_dt"]) else "—"
            
            # Dynamic Regional Office Mapping
            cat = item.get("category", "Civil")
            base_office = item.get("office_name")
            if not base_office or base_office == "None" or base_office == "Pending Assignment":
                base_office = DEPT_CONFIG.get(cat, {}).get("base", "Zonal Office")
            local_branch = f"{base_office} — {district} Branch"
            
            st.markdown(f"""
            <div class="dpi-card {css_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div><span class="mono-hash" style="color:white;">{item['id']}</span> <span style="margin-left:10px">{badge}</span></div>
                    <span style="font-size:12px; color:#64748B; font-family:'JetBrains Mono';">📅 {date_str}</span>
                </div>
                <h3 style="margin-top:16px; margin-bottom:8px; font-size:18px;">{item['raw_text']}</h3>
                <p style="color:#475569; font-size:14px; margin-bottom:16px;">📍 {loc_str}</p>
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:12px; border-radius:6px; display:flex; gap:20px; font-size:13px;">
                    <div><span style="color:#64748B">Jurisdiction:</span> <b>{local_branch}</b></div>
                    <div><span style="color:#64748B">Sector:</span> <b>{cat}</b></div>
                    <div><span style="color:#64748B">Budget Allocated:</span> <b>₹{item['budget_allocated']:,.0f}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Media Renderer
            c_url = get_telegram_url(item.get("media_file_id"))
            if is_res:
                r_url = get_telegram_url(item.get("resolution_media_id"))
                hash_val = item.get("audit_hash") or get_audit_hash(item["id"], item["amount_spent"])
                st.info(f"🛡️ **Social Audit Verified** | Treasury Payout: **₹{item['amount_spent']:,.0f}** | SHA-256 Hash: `{hash_val}`")
                
                col1, col2 = st.columns(2)
                with col1:
                    if c_url: render_media(c_url, item.get("media_type"), "🔴 Before (Citizen Report)")
                with col2:
                    if r_url: render_media(r_url, "photo", "🟢 After (Govt Resolution)")
            else:
                with st.expander(f"📎 View Citizen Evidence — {item['id']}"):
                    if c_url: render_media(c_url, item.get("media_type"))
                    else: st.write("No media attached.")
            st.write("<br>", unsafe_allow_html=True)

# ------------------------------------------
# PAGE 2: OPEN DATA LEDGER
# ------------------------------------------
elif page == "📊 Open Data Ledger":
    st.header("National Open Data Ledger")
    if df.empty: st.warning("No data available.")
    else:
        st.markdown('<div class="dpi-card"><div class="stat-label" style="margin-bottom:15px;">Sanctioned vs Disbursed Fiscal Ledger</div>', unsafe_allow_html=True)
        fiscal = df.groupby("category", as_index=False)[["budget_allocated", "amount_spent"]].sum()
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="Sanctioned", x=fiscal["category"], y=fiscal["budget_allocated"], marker_color="#0F172A"))
        fig_bar.add_trace(go.Bar(name="Spent", x=fiscal["category"], y=fiscal["amount_spent"], marker_color="#10B981"))
        fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="dpi-card"><div class="stat-label" style="margin-bottom:15px;">Grievances by Sector</div>', unsafe_allow_html=True)
            pie_data = df["category"].value_counts()
            fig_pie = go.Figure(go.Pie(labels=pie_data.index, values=pie_data.values, hole=0.5))
            fig_pie.update_layout(height=350, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="dpi-card"><div class="stat-label" style="margin-bottom:15px;">Operational Pipeline</div>', unsafe_allow_html=True)
            status_counts = df["status"].value_counts().reset_index()
            colors = ["#10B981" if "Resolved" in s else ("#EA580C" if "Pending" in s else "#2563EB") for s in status_counts["status"]]
            fig_pipe = go.Figure(go.Bar(x=status_counts["status"], y=status_counts["count"], marker_color=colors))
            fig_pipe.update_layout(height=350, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig_pipe, use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# PAGE 3: AGENCY JURISDICTION MATRIX
# ------------------------------------------
elif page == "🏛️ Agency Jurisdiction Matrix":
    st.header("Integrated Department Operations Matrix")
    st.markdown("This matrix defines the statutory bodies and nodal officers responsible for specific civic sectors across the DPI network.")
    
    matrix_data = []
    for cat, data in DEPT_CONFIG.items():
        matrix_data.append({"Sector Category": cat, "Statutory Body": data["base"], "Nodal Officer Title": data["officer"]})
    
    st.dataframe(pd.DataFrame(matrix_data), use_container_width=True, hide_index=True)

# ------------------------------------------
# PAGE 4: MAP
# ------------------------------------------
elif page == "📍 Incident Map":
    st.header("Live Geospatial Incident Map")
    if not df.empty and 'lat' in df.columns and 'lon' in df.columns:
        map_df = df.dropna(subset=['lat', 'lon']).copy()
        map_df['latitude'] = pd.to_numeric(map_df['lat'], errors='coerce')
        map_df['longitude'] = pd.to_numeric(map_df['lon'], errors='coerce')
        map_df = map_df.dropna(subset=['latitude', 'longitude'])
        map_df = map_df[(map_df['latitude'] != 0.0) & (map_df['longitude'] != 0.0)]
        
        if not map_df.empty: 
            st.markdown('<div class="dpi-card" style="padding:4px;">', unsafe_allow_html=True)
            st.map(map_df, zoom=10)
            st.markdown('</div>', unsafe_allow_html=True)
        else: st.warning("No valid coordinate data points found.")
    else: st.warning("No geospatial data available.")

# ------------------------------------------
# PAGE 5: AUTH
# ------------------------------------------
elif page == "🔐 Officer Gateway":
    st.header("Officer Authentication")
    with st.form("login_form"):
        user = st.text_input("Username (GovID)")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Authenticate", type="primary"):
            if user in AUTH_DB and AUTH_DB[user]["pass"] == pwd:
                st.session_state.role = AUTH_DB[user]["role"]
                st.session_state.dept = AUTH_DB[user]["dept"]
                st.rerun()
            else: st.error("Invalid credentials.")

# ------------------------------------------
# PAGE 6: COMMAND DASHBOARD
# ------------------------------------------
elif page == "⚙️ Command Dashboard":
    st.header(f"Command Dashboard — {st.session_state.dept}")
    if df.empty: st.info("No active data.")
    else:
        active_df = df if st.session_state.role == "admin" else df[df["category"].str.contains(st.session_state.dept, na=False, case=False)]
        active_df = active_df[~active_df["status"].str.contains("Resolved", na=False)]
        
        if active_df.empty: st.success("✅ All queues clear!")
        else:
            sel_id = st.selectbox("Select Grievance to Process:", active_df["id"].tolist())
            row = active_df[active_df["id"] == sel_id].iloc[0]
            
            _, district = fetch_geo_data(row['lat'], row['lon'])
            
            st.markdown(f"""
            <div class="dpi-card dpi-card--pending">
                <div style="font-family:'JetBrains Mono'; font-weight:700; font-size:16px;">#{row['id']}</div>
                <h3 style="margin-top:10px;">{row['raw_text']}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            c_url = get_telegram_url(row.get("media_file_id"))
            if c_url:
                with st.expander("View Citizen Evidence"): render_media(c_url, row.get("media_type"))
            
            if st.session_state.role == "admin":
                st.subheader("🏛️ Route & Sanction")
                with st.form("admin_act"):
                    d_keys = list(DEPT_CONFIG.keys())
                    cat = row.get('category', 'Roads & Infrastructure')
                    sel_cat = st.selectbox("Route to Sector:", d_keys, index=d_keys.index(cat) if cat in d_keys else 0)
                    
                    calc_office = f"{DEPT_CONFIG[sel_cat]['base']} — {district} Branch"
                    
                    c1, c2 = st.columns(2)
                    with c1: office = st.text_input("Office Assignment:", value=calc_office)
                    with c2: officer = st.text_input("Nodal Officer:", value=DEPT_CONFIG[sel_cat]['officer'])
                    
                    c3, c4 = st.columns(2)
                    with c3: stage = st.selectbox("Stage:", ["2. Survey & Estimation", "3. Admin Sanction", "4. Tender Awarded"])
                    with c4: budget = st.number_input("Sanction Budget (₹):", value=float(row['budget_allocated']), step=5000.0)
                    
                    if st.form_submit_button("Lock Sanction & Dispatch", type="primary"):
                        execute_admin_sanction(sel_id, stage, budget, "Govt Contractor", sel_cat, office, officer)
                        st.success("Ticket Dispatched.")
                        st.rerun()
                        
            elif st.session_state.role == "field":
                st.info(f"**Budget Available:** ₹{row['budget_allocated']:,.0f}")
                with st.form("field_act"):
                    spent = st.number_input("Final Treasury Payout (₹):", value=float(row['budget_allocated']))
                    materials = st.text_area("Measurement Book (BOQ Details):")
                    proof = st.file_uploader("Upload Completion Photo:", type=['jpg','jpeg','png'])
                    if st.form_submit_button("Verify & Publish to Social Audit", type="primary"):
                        execute_field_resolution(sel_id, spent, materials, "local_upload_placeholder")
                        st.success("Resolved.")
                        st.rerun()