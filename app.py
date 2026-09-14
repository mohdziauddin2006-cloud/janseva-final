import os
import time
import hashlib
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from backend import get_all_complaints, execute_admin_sanction, execute_field_resolution

st.set_page_config(page_title="JanSeva DPI | Govt of India", layout="wide", page_icon="🇮🇳")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# SOVEREIGN UI OVERHAUL (Tricolor accents, Official Typography)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .main { background-color: #f0f4f8; }
    
    /* Sovereign Top Bar */
    .gov-banner { background-color: #0f172a; color: #f8fafc; padding: 6px 20px; font-size: 13px; font-weight: 500; display: flex; justify-content: space-between; align-items: center; }
    .tricolor-strip { height: 4px; width: 100%; background: linear-gradient(to right, #FF9933 0%, #FF9933 33.3%, #FFFFFF 33.3%, #FFFFFF 66.6%, #138808 66.6%, #138808 100%); }
    
    .stat-card { background: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0; border-left: 5px solid #FF9933; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .stat-label { font-size: 13px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-val { font-size: 32px; font-weight: 800; color: #0f172a; margin-top: 4px; }
    
    .ticket-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }
    
    .badge { display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;}
    .badge-pending { background-color: #fff7ed; color: #c2410c; border: 1px solid #ffedd5;}
    .badge-progress { background-color: #eff6ff; color: #1d4ed8; border: 1px solid #dbeafe;}
    .badge-resolved { background-color: #f0fdf4; color: #15803d; border: 1px solid #dcfce7;}
    .badge-emergency { background-color: #fef2f2; color: #b91c1c; border: 1px solid #fecaca;}
    
    .timeline-container { display: flex; justify-content: space-between; align-items: center; margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;}
    .step { font-size: 12px; font-weight: 600; color: #94a3b8; text-align: center; flex: 1; text-transform: uppercase; letter-spacing: 0.5px;}
    .step.active { color: #FF9933; font-weight: 800; }
    .step.completed { color: #138808; }
    
    .photo-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; text-align: center; height: 100%;}
    .hash-box { background: #0f172a; color: #34d399; font-family: monospace; padding: 8px 12px; border-radius: 4px; font-size: 13px; display: inline-block; margin-top: 10px;}
    </style>
""", unsafe_allow_html=True)

# Ingest Sovereign Header
st.markdown('<div class="gov-banner"><div>🇮🇳 भारत सरकार | Government of India</div><div>Digital Public Infrastructure | JanSeva</div></div><div class="tricolor-strip"></div><br>', unsafe_allow_html=True)

# State Management
if "role" not in st.session_state: st.session_state.role = "public"
if "dept" not in st.session_state: st.session_state.dept = None
if "login_attempts" not in st.session_state: st.session_state.login_attempts = 0
if "lockout_time" not in st.session_state: st.session_state.lockout_time = 0

DEPT_DIRECTORY = {
    "Roads": {"office": "State PWD Roads & Bridges Division", "officer": "Er. Rajesh Varma, JE (Civil)"},
    "Water": {"office": "Municipal Water Supply Board", "officer": "Er. K. Ramesh, AEE (Water)"},
    "Electricity": {"office": "Power Distribution Corp (DISCOM)", "officer": "Er. M. Praveen, SDE (Power)"},
    "Sanitation": {"office": "Solid Waste Management Bureau", "officer": "Dr. A. Rao, Chief Sanitary Inspector"},
    "Cyber Crime": {"office": "Cyber Crime Police Station", "officer": "Inspector S. Reddy, Cyber Cell"},
    "Civil": {"office": "Municipal Zonal Engineering Office", "officer": "Er. P. Naidu, Executive Engineer"}
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
    if not file_id or str(file_id).strip().lower() in ['none', 'nan', 'null', '']: return None
    try:
        res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
        if res.get("ok"): return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{res['result']['file_path']}"
    except: pass
    return None

def display_media(file_url, media_type, is_officer=False):
    if not file_url: return
    m = str(media_type).lower()
    try:
        if 'photo' in m or media_type is None or m in ['nan', 'none']:
            st.image(file_url, use_container_width=True)
            if is_officer: st.markdown(f"<div align='center'><a href='{file_url}' target='_blank' style='font-size:13px; font-weight:bold; color:#2563eb;'>🔍 View Original Govt Scan</a></div>", unsafe_allow_html=True)
        elif 'video' in m or 'animation' in m:
            st.video(file_url)
            st.markdown(f"<div align='center'><a href='{file_url}' target='_blank' style='font-size:13px; font-weight:bold; color:#dc2626;'>🎥 If video fails, click to download</a></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"📎 <a href='{file_url}' target='_blank'>Download Evidence File</a>", unsafe_allow_html=True)
    except: st.markdown(f"📎 <a href='{file_url}' target='_blank'>View Media File</a>", unsafe_allow_html=True)

@st.cache_data(ttl=86400)
def fetch_address(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return "GPS Location Not Provided"
    try:
        headers = {'User-Agent': 'JanSeva_DPI_India'}
        res = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers=headers, timeout=5).json()
        return f"{res.get('display_name', 'Address unknown')} <a href='https://maps.google.com/?q={lat},{lon}' target='_blank' style='color:#2563eb;'>📍 Map</a>"
    except: return f"Coords: {lat}, {lon}"

def render_status_badge(status, hours_open=0):
    if "Resolved" in status: return f'<span class="badge badge-resolved">✓ {status}</span>'
    if hours_open > 48 and "Pending" in status: return f'<span class="badge badge-emergency">🚨 SLA BREACH</span>'
    if "Tender" in status or "Survey" in status or "Sanction" in status: return f'<span class="badge badge-progress">↻ {status}</span>'
    return f'<span class="badge badge-pending">⏳ {status}</span>'

def render_timeline(status):
    stages = ["1. Pending Review", "2. Survey & Estimation", "3. Administrative Sanction", "4. Tender Awarded", "6. Resolved (Social Audit)"]
    current_idx = next((i for i, s in enumerate(stages) if s[:2] in status[:2]), 0)
    html = '<div class="timeline-container">'
    for i, stage in enumerate(stages):
        cls = "completed" if i < current_idx else "active" if i == current_idx else ""
        html += f'<div class="step {cls}">{stage[3:]}</div>'
    html += '</div>'
    return html

def get_audit_hash(ticket_id, amount_spent):
    raw_str = f"GOI_DPI_{ticket_id}_{amount_spent}_VERIFIED"
    return hashlib.sha256(raw_str.encode()).hexdigest()[:16].upper()

# Sidebar Navigation
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=70)
    st.markdown("## **JanSeva DPI**")
    st.caption("Empowering Citizens, Enabling Transparency.")
    st.divider()
    
    if st.session_state.role == "public":
        page = st.radio("Access Portals", ["🌐 Citizens' Public Portal", "📊 Open Data Analytics", "📍 Geospatial Incident Map", "🔐 Officer Gateway"])
    else:
        st.success(f"**Authority:** {st.session_state.role.upper()}\n\n**Scope:** {st.session_state.dept}")
        page = st.radio("Access Portals", ["⚙️ Officer Command Dashboard", "🌐 Citizens' Public Portal", "📊 Open Data Analytics"])
        if st.button("🚪 Secure Sign Out", use_container_width=True):
            st.session_state.role = "public"
            st.session_state.dept = None
            st.rerun()

# Ingest Records
records = get_all_complaints()
df = pd.DataFrame(records) if records else pd.DataFrame()

if not df.empty:
    df['budget_allocated'] = pd.to_numeric(df.get('budget_allocated', 0)).fillna(0)
    df['amount_spent'] = pd.to_numeric(df.get('amount_spent', 0)).fillna(0)
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df['hours_open'] = (pd.Timestamp.now(tz='UTC') - df['timestamp_dt']).dt.total_seconds() / 3600
    df['category'] = df['category'].astype(str).replace(['nan', 'None'], 'Civil')
    df['office_name'] = df['office_name'].astype(str).replace(['nan', 'None', ''], 'Pending Assignment')
    df['assigned_officer'] = df['assigned_officer'].astype(str).replace(['nan', 'None', ''], 'Awaiting Nodal Officer')
    df['materials_used'] = df['materials_used'].astype(str).replace(['nan', 'None', ''], 'Standard operations.')
    if 'resolution_media_id' in df.columns: df['resolution_media_id'] = df['resolution_media_id'].astype(str).replace(['nan', 'None', ''], None)
    if 'media_file_id' in df.columns: df['media_file_id'] = df['media_file_id'].astype(str).replace(['nan', 'None', ''], None)

if page == "🌐 Citizens' Public Portal":
    st.title("Public Transparency & Social Audit Ledger")
    
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card"><div class="stat-label">Total Logged</div><div class="stat-val">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card" style="border-left-color: #2563eb;"><div class="stat-label">Public Sanctioned</div><div class="stat-val">₹{df["budget_allocated"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card" style="border-left-color: #FF9933;"><div class="stat-label">Actual Spent</div><div class="stat-val">₹{df["amount_spent"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card" style="border-left-color: #138808;"><div class="stat-label">Verified Audits</div><div class="stat-val" style="color:#138808;">{len(df[df["status"].str.contains("Resolved", na=False)])}</div></div>', unsafe_allow_html=True)
        
        st.write("<br>", unsafe_allow_html=True)
        tab_all, tab_resolved = st.tabs(["📋 Live Grievance Registry", "📸 Immutable Social Audit Feed"])
        
        with tab_all:
            for _, item in df.iterrows():
                loc_str = fetch_address(item['lat'], item['lon'])
                is_resolved = "Resolved" in item['status']
                
                st.markdown(f"""
                    <div class="ticket-container">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div><span style="font-size:18px; font-weight:800;">Ticket #{item['id']}</span> <span style="margin-left:10px;">{render_status_badge(item['status'], item['hours_open'])}</span></div>
                            <span style="font-size:13px; color:#64748b;">📅 {item['timestamp_dt'].strftime('%d %b %Y')}</span>
                        </div>
                        <div style="margin-top:10px; font-size:15px; color:#334155; line-height:1.6;">
                            <b>Reported Issue:</b> {item['raw_text']}<br><b>Location:</b> {loc_str}
                        </div>
                        <hr style="border-top:1px solid #f1f5f9;">
                        <div style="display:flex; flex-wrap:wrap; gap:20px; font-size:13px; color:#475569; margin-bottom: 15px;">
                            <div><b>Sector:</b> {item['category']}</div>
                            <div><b>Office:</b> {item['office_name']}</div>
                            <div><b>Officer:</b> {item['assigned_officer']}</div>
                            <div><b>Budget:</b> ₹{item['budget_allocated']:,.0f}</div>
                        </div>
                """, unsafe_allow_html=True)
                
                if is_resolved:
                    st.markdown("##### 📸 Official Resolution Evidence")
                    col_ev1, col_ev2 = st.columns(2)
                    with col_ev1:
                        st.markdown('<div class="photo-box"><b>🔴 Citizen Report</b>', unsafe_allow_html=True)
                        c_url = get_telegram_url(item.get('media_file_id'))
                        if c_url: display_media(c_url, item.get('media_type'))
                        else: st.caption("No media.")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with col_ev2:
                        st.markdown('<div class="photo-box"><b style="color:#138808;">🟢 Govt Resolution</b>', unsafe_allow_html=True)
                        r_url = get_telegram_url(item.get('resolution_media_id'))
                        if r_url: display_media(r_url, 'photo', is_officer=True)
                        else: st.caption("No photo.")
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    with st.expander(f"View Citizen Evidence Media for #{item['id']}"):
                        media_url = get_telegram_url(item.get('media_file_id'))
                        if media_url: display_media(media_url, item.get('media_type'))
                        else: st.caption("No media attached.")
                st.markdown("</div>", unsafe_allow_html=True)

        with tab_resolved:
            resolved_subset = df[df['status'].str.contains("Resolved", na=False)]
            if not resolved_subset.empty:
                for _, r in resolved_subset.iterrows():
                    h_val = get_audit_hash(r['id'], r['amount_spent'])
                    st.markdown(f"""
                        <div class="ticket-container">
                            <div style="display:flex; justify-content:space-between;">
                                <span style="font-weight:800; font-size:16px;">{r['category']} — {r['office_name']}</span>
                                <span style="font-size:14px; color:#138808; font-weight:700;">✅ Audited & Verified</span>
                            </div>
                            <div style="margin-top:10px; font-size:14px; color:#334155;">
                                <b>Bill of Quantities (BOQ):</b> {r['materials_used']}<br>
                                <b>Fiscal Audit:</b> Sanctioned ₹{r['budget_allocated']:,.0f} | Treasury Payout: <b style="color:#2563eb;">₹{r['amount_spent']:,.0f}</b>
                                <br><div class="hash-box">🛡️ SHA-256 Audit Hash: 0x{h_val}</div>
                            </div>
                            <hr>
                    """, unsafe_allow_html=True)
                    
                    c_before, c_after = st.columns(2)
                    with c_before:
                        st.markdown('<div class="photo-box"><b>🔴 Before (Citizen)</b>', unsafe_allow_html=True)
                        b_url = get_telegram_url(r.get('media_file_id'))
                        if b_url: display_media(b_url, r.get('media_type'))
                        else: st.caption("No photo.")
                        st.markdown('</div>', unsafe_allow_html=True)
                    with c_after:
                        st.markdown('<div class="photo-box"><b style="color:#138808;">🟢 After (Official Proof)</b>', unsafe_allow_html=True)
                        a_url = get_telegram_url(r.get('resolution_media_id'))
                        if a_url: display_media(a_url, 'photo', is_officer=True)
                        else: st.caption("No photo.")
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            else: st.info("No resolved grievances yet.")
    else: st.info("Database is empty. Submit via Telegram.")

elif page == "📊 Open Data Analytics":
    st.title("National Data Analytics")
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="ticket-container"><b>Grievances by Sector</b>', unsafe_allow_html=True)
            fig1 = px.pie(df, names='category', hole=0.4, color_discrete_sequence=['#FF9933', '#138808', '#0f172a', '#2563eb', '#94a3b8'])
            st.plotly_chart(fig1, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="ticket-container"><b>Status Lifecycle Pipeline</b>', unsafe_allow_html=True)
            fig2 = px.bar(df['status'].value_counts().reset_index(), x='status', y='count', color='status')
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else: st.warning("Not enough data.")

elif page == "🔐 Officer Gateway":
    st.title("Secure Authentication Gateway")
    if time.time() < st.session_state.lockout_time:
        st.error(f"🚨 Security Lockout: Try again in {int(st.session_state.lockout_time - time.time())}s.")
    else:
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            st.subheader("GovID Login")
            with st.form("auth"):
                uid = st.text_input("Username")
                pwd = st.text_input("Passkey", type="password")
                if st.form_submit_button("Authenticate", use_container_width=True):
                    if uid in AUTH_DB and AUTH_DB[uid]["pass"] == pwd:
                        st.session_state.update({"role": AUTH_DB[uid]["role"], "dept": AUTH_DB[uid]["dept"], "login_attempts": 0})
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        if st.session_state.login_attempts >= 3:
                            st.session_state.lockout_time = time.time() + 60
                            st.rerun()
                        else: st.error("Access Denied.")
            st.markdown('</div>', unsafe_allow_html=True)

elif page == "⚙️ Officer Command Dashboard":
    st.title(f"Command Dashboard — {st.session_state.dept.upper()}")
    
    if not df.empty:
        working_df = df[df['category'].str.contains(st.session_state.dept, case=False, na=False)] if st.session_state.role == "field" else df
        active_df = working_df[~working_df['status'].str.contains("Resolved", na=False)]
        
        if not active_df.empty:
            sel_id = st.selectbox("Select Grievance to Process:", active_df["id"].tolist())
            row = active_df[active_df["id"] == sel_id].iloc[0]
            
            st.markdown(render_timeline(row['status']), unsafe_allow_html=True)
            
            st.markdown(f"""
                <div class="ticket-container">
                    <h4>Ticket #{row['id']} {render_status_badge(row['status'], row['hours_open'])}</h4>
                    <p><b>Issue:</b> {row['raw_text']}<br><b>Location:</b> {fetch_address(row['lat'], row['lon'])}</p>
                </div>
            """, unsafe_allow_html=True)
            
            c_url = get_telegram_url(row.get('media_file_id'))
            if c_url: display_media(c_url, row.get('media_type'))
            
            if st.session_state.role == "admin":
                with st.form("admin_form"):
                    current_cat = row['category'] if row['category'] in DEPT_DIRECTORY else "Roads"
                    dept_keys = list(DEPT_DIRECTORY.keys())
                    selected_dept = st.selectbox("Route to Department:", dept_keys, index=dept_keys.index(current_cat))
                    
                    c1, c2 = st.columns(2)
                    with c1: target_office = st.text_input("Office Name:", value=DEPT_DIRECTORY[selected_dept]["office"])
                    with c2: target_officer = st.text_input("Assigned Officer:", value=DEPT_DIRECTORY[selected_dept]["officer"])
                    
                    c3, c4 = st.columns(2)
                    with c3: new_stage = st.selectbox("Advance Lifecycle:", ["2. Survey & Estimation", "3. Administrative Sanction", "4. Tender Awarded"])
                    with c4: budget_alloc = st.number_input("Sanction Budget (₹):", value=float(row['budget_allocated']), step=5000.0)
                    
                    contractor = st.text_input("Awarded Contractor:", value=str(row.get('contractor_name') or ''))
                    
                    if st.form_submit_button("Lock Sanction & Dispatch", type="primary", use_container_width=True):
                        execute_admin_sanction(sel_id, new_stage, budget_alloc, contractor, selected_dept, target_office, target_officer)
                        if pd.notna(row['chat_id']) and BOT_TOKEN:
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": row['chat_id'], "text": f"🇮🇳 **Govt Update**\nTicket `{sel_id}` routed to {target_office}.\n🚥 {new_stage}\n💰 Sanctioned: ₹{budget_alloc:,.0f}"})
                        st.success("Dispatched successfully!")
                        st.rerun()

            elif st.session_state.role == "field":
                st.info(f"💰 **Locked Budget:** ₹{row['budget_allocated']:,.0f} | **Contractor:** {row.get('contractor_name') or 'Internal Department'}")
                with st.form("field_form"):
                    materials = st.text_area("Measurement Book (BOQ & Materials Used):", placeholder="Enter official actions taken...")
                    spent = st.number_input("Final Treasury Payout (Amount Spent ₹):", value=float(row['budget_allocated']), step=1000.0)
                    proof = st.file_uploader("Upload Photographic Resolution Proof:", type=['jpg', 'jpeg', 'png'])
                    
                    if st.form_submit_button("Submit Resolution Proof", type="primary", use_container_width=True):
                        if not proof: st.error("❌ Proof photograph is mandatory.")
                        else:
                            media_id = None
                            if pd.notna(row['chat_id']) and BOT_TOKEN:
                                res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": row['chat_id'], "caption": f"✅ **Resolved!**\nTicket: `{sel_id}`\nSpent: ₹{spent:,.0f}"}, files={"photo": proof.getvalue()}).json()
                                if res.get("ok"): media_id = res["result"]["photo"][-1]["file_id"]
                            execute_field_resolution(sel_id, spent, materials, media_id)
                            st.success("Work verified and published to Social Audit.")
                            st.rerun()
        else: st.success("Queue is clear.")
    else: st.info("No complaints found.")

elif page == "📍 Geospatial Incident Map":
    st.title("Live Incident Map")
    if not df.empty and not df['lat'].isnull().all():
        st.map(df.dropna(subset=['lat', 'lon']).rename(columns={"lat": "latitude", "lon": "longitude"}))
    else: st.warning("No geospatial telemetry available.")

st.markdown("<hr><center><p style='font-size:12px; color:#94a3b8;'>Designed & Developed for Citizen Empowerment | Digital India Initiative 🇮🇳</p></center>", unsafe_allow_html=True)