import os
import time
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
# SAFE CSS (No Overlapping Elements)
# ==========================================
st.markdown("""
    <style>
    .gov-banner { background-color: #111827; color: #FFFFFF; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 4px 4px 0 0; }
    .tricolor-strip { height: 4px; width: 100%; background: linear-gradient(to right, #FF9933 0%, #FF9933 33.3%, #FFFFFF 33.3%, #FFFFFF 66.6%, #138808 66.6%, #138808 100%); margin-bottom: 20px; }
    .dpi-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 3px solid #111827; border-radius: 6px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stat-card { background: #FFFFFF; padding: 20px; border-radius: 6px; border: 1px solid #E2E8F0; border-left: 4px solid #FF9933; }
    .stat-label { font-size: 12px; font-weight: bold; color: #64748B; text-transform: uppercase; }
    .stat-val { font-size: 28px; font-weight: bold; color: #0F172A; }
    .badge-resolved { background-color: #D1FAE5; color: #065F46; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-pending { background-color: #FEF3C7; color: #92400E; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# STATE & AUTH LOGIC
# ==========================================
if "role" not in st.session_state: st.session_state.role = "public"
if "dept" not in st.session_state: st.session_state.dept = None

AUTH_DB = {
    "collector":   {"pass": "ias@2026", "role": "admin", "dept": "All"},
    "pwd_roads":   {"pass": "pwd@2026", "role": "field", "dept": "Roads"},
    "sanitation":  {"pass": "swm@2026", "role": "field", "dept": "Sanitation"},
    "water_board": {"pass": "jal@2026", "role": "field", "dept": "Water"}
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_telegram_url(file_id):
    """Safely fetches image URLs and prevents the broken '0' image bug."""
    if pd.isna(file_id) or not file_id: return None
    fid_str = str(file_id).strip().lower()
    if fid_str in {"none", "nan", "", "0", "null"}: return None
    
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=5).json()
        if r.get("ok"): return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}"
    except Exception: pass
    return None

@st.cache_data(ttl=86400)
def fetch_address(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return "GPS Location Not Provided"
    try:
        r = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers={"User-Agent": "JanSeva_DPI"}, timeout=3).json()
        return f"{r.get('display_name', 'Address unknown')} ([Map](https://maps.google.com/?q={lat},{lon}))"
    except Exception: return f"Coordinates: {lat:.4f}, {lon:.4f}"

def load_data():
    records = get_all_complaints()
    if not records: return pd.DataFrame()
    df = pd.DataFrame(records)
    df["budget_allocated"] = pd.to_numeric(df.get("budget_allocated", 0), errors="coerce").fillna(0)
    df["amount_spent"]     = pd.to_numeric(df.get("amount_spent", 0), errors="coerce").fillna(0)
    df["timestamp_dt"]     = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    return df

# ==========================================
# UI RENDER
# ==========================================
st.markdown('<div class="gov-banner">🇮🇳 Government of India | JanSeva DPI Platform</div><div class="tricolor-strip"></div>', unsafe_allow_html=True)

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=70)
    st.title("JanSeva DPI")
    if st.session_state.role == "public":
        page = st.radio("Navigation", ["🌐 Public Transparency Board", "📊 Open Data Ledger", "📍 Live Incident Map", "🔐 Officer Gateway"])
    else:
        st.success(f"Logged in as: {st.session_state.role.upper()} ({st.session_state.dept})")
        page = st.radio("Navigation", ["⚙️ Command Dashboard", "🌐 Public Transparency Board", "📊 Open Data Ledger", "📍 Live Incident Map"])
        if st.button("Sign Out", use_container_width=True):
            st.session_state.update({"role": "public", "dept": None})
            st.rerun()

df = load_data()

if page == "🌐 Public Transparency Board":
    st.header("Public Transparency Ledger")
    
    if df.empty:
        st.info("No grievances in the database yet. Send a message to your Telegram bot to create one.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card"><div class="stat-label">Total Logged</div><div class="stat-val">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card"><div class="stat-label">Sanctioned</div><div class="stat-val">₹{df["budget_allocated"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card"><div class="stat-label">Disbursed</div><div class="stat-val">₹{df["amount_spent"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card"><div class="stat-label">Resolved</div><div class="stat-val" style="color:#059669;">{len(df[df["status"].str.contains("Resolved", na=False)])}</div></div>', unsafe_allow_html=True)

        st.write("---")
        
        # Single Unified Feed (No Audit Tab)
        for _, item in df.iterrows():
            is_res = "Resolved" in str(item["status"])
            badge = f'<span class="badge-resolved">✓ {item["status"]}</span>' if is_res else f'<span class="badge-pending">⏳ {item["status"]}</span>'
            
            st.markdown(f"""
            <div class="dpi-card">
                <div style="display:flex; justify-content:space-between;">
                    <b>#{item['id']}</b> {badge}
                </div>
                <p style="margin-top:10px; font-size:16px;"><b>Issue:</b> {item['raw_text']}</p>
                <p style="color:#64748B; font-size:14px;">📍 {fetch_address(item['lat'], item['lon'])}</p>
                <hr>
                <p style="font-size:13px; color:#475569;">Sector: <b>{item.get('category', 'Civil')}</b> | Budget: <b>₹{item['budget_allocated']:,.0f}</b></p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("View Media Evidence"):
                img_url = get_telegram_url(item.get("media_file_id"))
                if img_url: 
                    st.image(img_url, use_container_width=True, caption="Initial Citizen Report")
                else: 
                    st.write("No media attached by citizen.")
                    
                if is_res:
                    res_url = get_telegram_url(item.get("resolution_media_id"))
                    if res_url:
                        st.image(res_url, use_container_width=True, caption="Government Resolution Proof")

elif page == "📊 Open Data Ledger":
    st.header("National Open Data Ledger")
    if df.empty: st.warning("No data available.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Grievances by Sector")
            fig_pie = go.Figure(go.Pie(labels=df["category"].value_counts().index, values=df["category"].value_counts().values, hole=0.4))
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            st.subheader("Sanctioned vs Disbursed Fiscal Ledger")
            fiscal = df.groupby("category", as_index=False)[["budget_allocated", "amount_spent"]].sum()
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(name="Sanctioned", x=fiscal["category"], y=fiscal["budget_allocated"], marker_color="#111827"))
            fig_bar.add_trace(go.Bar(name="Spent", x=fiscal["category"], y=fiscal["amount_spent"], marker_color="#10B981"))
            st.plotly_chart(fig_bar, use_container_width=True)

elif page == "📍 Live Incident Map":
    st.header("Live Geospatial Incident Map")
    if not df.empty and 'lat' in df.columns and 'lon' in df.columns:
        # Strictly clean data to prevent map errors
        map_df = df.dropna(subset=['lat', 'lon']).copy()
        map_df['latitude'] = pd.to_numeric(map_df['lat'], errors='coerce')
        map_df['longitude'] = pd.to_numeric(map_df['lon'], errors='coerce')
        map_df = map_df.dropna(subset=['latitude', 'longitude'])
        
        # Filter out 0.0 coordinates which break map framing
        map_df = map_df[(map_df['latitude'] != 0.0) & (map_df['longitude'] != 0.0)]
        
        if not map_df.empty:
            st.map(map_df, zoom=11)
        else:
            st.warning("No valid coordinate data points found.")
    else:
        st.warning("No geospatial data available.")

elif page == "🔐 Officer Gateway":
    st.header("Officer Authentication")
    with st.form("login_form"):
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if user in AUTH_DB and AUTH_DB[user]["pass"] == pwd:
                st.session_state.role = AUTH_DB[user]["role"]
                st.session_state.dept = AUTH_DB[user]["dept"]
                st.rerun()
            else:
                st.error("Invalid credentials.")

elif page == "⚙️ Command Dashboard":
    st.header(f"Command Dashboard — {st.session_state.dept}")
    if df.empty: st.info("No active data.")
    else:
        active_df = df if st.session_state.role == "admin" else df[df["category"].str.contains(st.session_state.dept, na=False, case=False)]
        active_df = active_df[~active_df["status"].str.contains("Resolved", na=False)]
        
        if active_df.empty: st.success("All queues clear!")
        else:
            sel_id = st.selectbox("Select Grievance:", active_df["id"].tolist())
            row = active_df[active_df["id"] == sel_id].iloc[0]
            
            st.write(f"**Issue:** {row['raw_text']}")
            
            if st.session_state.role == "admin":
                with st.form("admin_act"):
                    cat = st.text_input("Category (e.g. Roads, Sanitation):", value=row.get('category', 'Roads'))
                    stage = st.selectbox("Stage:", ["2. Survey", "3. Admin Sanction", "4. Tender Awarded"])
                    budget = st.number_input("Sanction Budget (₹):", value=float(row['budget_allocated']), step=5000.0)
                    if st.form_submit_button("Lock Sanction"):
                        execute_admin_sanction(sel_id, stage, budget, "Govt Dept", cat, "Zonal Office", "Nodal Officer")
                        st.success("Sanctioned!")
                        st.rerun()
            elif st.session_state.role == "field":
                st.info(f"Budget Available: ₹{row['budget_allocated']:,.0f}")
                with st.form("field_act"):
                    spent = st.number_input("Amount Spent (₹):", value=float(row['budget_allocated']))
                    materials = st.text_area("Measurement Book (BOQ):")
                    proof = st.file_uploader("Upload Completion Photo:")
                    if st.form_submit_button("Submit Resolution"):
                        execute_field_resolution(sel_id, spent, materials, "local_upload_placeholder")
                        st.success("Resolved!")
                        st.rerun()