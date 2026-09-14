import os
import time
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from backend import get_all_complaints, execute_admin_sanction, execute_field_resolution

st.set_page_config(page_title="JanSeva DPI - National Grievance Infrastructure", layout="wide", page_icon="🏛️")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# UI Overhaul
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .main { background-color: #f4f7fb; }
    .stat-card { background: #ffffff; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; border-top: 4px solid #2563eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: transform 0.2s ease; }
    .stat-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08); }
    .stat-label { font-size: 14px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-val { font-size: 32px; font-weight: 800; color: #0f172a; margin-top: 8px; }
    .ticket-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; }
    .badge-pending { background-color: #fef3c7; color: #b45309; }
    .badge-progress { background-color: #dbeafe; color: #1d4ed8; }
    .badge-resolved { background-color: #dcfce7; color: #15803d; }
    .badge-emergency { background-color: #fee2e2; color: #b91c1c; border: 1px solid #f87171;}
    .timeline-container { display: flex; justify-content: space-between; align-items: center; margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;}
    .step { font-size: 13px; font-weight: 600; color: #94a3b8; text-align: center; flex: 1; position: relative;}
    .step.active { color: #2563eb; font-weight: 800; }
    .step.completed { color: #10b981; }
    .media-btn { margin-top: 10px; font-size: 14px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

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
    if not file_id or not BOT_TOKEN: return None
    try:
        res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=3).json()
        if res.get("ok"): return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{res['result']['file_path']}"
    except: pass
    return None

# UNIVERSAL MEDIA RENDERER FIX
def display_media(file_url, media_type):
    if not file_url: return
    m_type = str(media_type).lower()
    
    if 'photo' in m_type:
        st.image(file_url, use_container_width=True)
    elif 'video' in m_type or 'animation' in m_type:
        st.video(file_url)
        # Bulletproof fallback for Telegram streaming limits
        st.markdown(f"<div class='media-btn'>🎥 <a href='{file_url}' target='_blank'>If video doesn't play, Click Here to View / Download</a></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='media-btn'>📎 <a href='{file_url}' target='_blank'>Download Attached Evidence File</a></div>", unsafe_allow_html=True)

@st.cache_data(ttl=86400)
def fetch_address(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return "GPS Location Not Provided"
    try:
        headers = {'User-Agent': 'JanSeva_DPI_Hackathon'}
        res = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}", headers=headers, timeout=3).json()
        address = res.get('display_name', 'Address resolution failed.')
        return f"{address} <a href='https://maps.google.com/?q={lat},{lon}' target='_blank'>🌍 Map</a>"
    except: return f"Coords: {lat}, {lon} <a href='https://maps.google.com/?q={lat},{lon}' target='_blank'>🌍 Map</a>"

def render_status_badge(status, hours_open=0):
    if "Resolved" in status: return f'<span class="badge badge-resolved">✓ {status}</span>'
    if hours_open > 48 and "Pending" in status: return f'<span class="badge badge-emergency">🚨 SLA BREACH (>48h)</span>'
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

# Sidebar Navigation
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=65)
    st.markdown("## **JanSeva DPI**")
    st.caption("National Public Infrastructure")
    st.divider()
    
    if st.session_state.role == "public":
        page = st.radio("Navigation", ["🌐 Citizens' Public Portal", "📊 Open Data Analytics", "📍 Geospatial Incident Map", "🔐 Officer Gateway"])
    else:
        st.success(f"**Auth:** {st.session_state.role.upper()}\n\n**Scope:** {st.session_state.dept}")
        page = st.radio("Navigation", ["⚙️ Officer Command Dashboard", "🌐 Citizens' Public Portal", "📊 Open Data Analytics"])
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
    df['category'] = df['category'].fillna("Civil").replace("None", "Civil")

if page == "🌐 Citizens' Public Portal":
    st.title("Public Transparency & Social Audit Ledger")
    
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card"><div class="stat-label">Total Grievances</div><div class="stat-val">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card"><div class="stat-label">Sanctioned Funds</div><div class="stat-val">₹{df["budget_allocated"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card"><div class="stat-label">Actual Spent</div><div class="stat-val">₹{df["amount_spent"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card"><div class="stat-label">Verified Resolved</div><div class="stat-val" style="color:#10b981;">{len(df[df["status"].str.contains("Resolved", na=False)])}</div></div>', unsafe_allow_html=True)
        
        st.write("<br>", unsafe_allow_html=True)
        tab_all, tab_resolved = st.tabs(["📋 Live Grievance Registry", "📸 Verified Social Audit Feed"])
        
        with tab_all:
            for _, item in df.iterrows():
                time_str = item['timestamp_dt'].strftime('%d %b %Y, %I:%M %p')
                loc_str = fetch_address(item['lat'], item['lon'])
                
                st.markdown(f"""
                    <div class="ticket-container">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div><span style="font-size:18px; font-weight:800;">Ticket #{item['id']}</span> <span style="margin-left:10px;">{render_status_badge(item['status'], item['hours_open'])}</span></div>
                            <span style="font-size:13px; color:#64748b;">📅 {time_str}</span>
                        </div>
                        <div style="margin-top:10px; font-size:15px; color:#334155; line-height:1.6;">
                            <b>Issue:</b> {item['raw_text']}<br><b>Location:</b> {loc_str}
                        </div>
                        <hr style="border-top:1px solid #f1f5f9;">
                        <div style="display:flex; gap:20px; font-size:13px; color:#475569;">
                            <div><b>Dept:</b> {item['category']}</div>
                            <div><b>Office:</b> {item['office_name']}</div>
                            <div><b>Officer:</b> {item['assigned_officer']}</div>
                            <div><b>Budget:</b> ₹{item['budget_allocated']:,.0f}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"View Evidence Media for #{item['id']}"):
                    media_url = get_telegram_url(item['media_file_id'])
                    if media_url: 
                        # USING NEW DISPLAY METHOD
                        display_media(media_url, item.get('media_type'))
                    else: 
                        st.caption("No media attached.")

        with tab_resolved:
            resolved_subset = df[df['status'].str.contains("Resolved", na=False)]
            if not resolved_subset.empty:
                for _, r in resolved_subset.iterrows():
                    st.markdown(f"""
                        <div class="ticket-container">
                            <div style="display:flex; justify-content:space-between;">
                                <span style="font-weight:800; font-size:16px;">{r['category']} — {r['office_name']}</span>
                                <span style="font-size:14px; color:#15803d; font-weight:700;">✅ Audited</span>
                            </div>
                            <div style="margin-top:10px; font-size:14px; color:#334155;">
                                <b>Resolution / BOQ:</b> {r.get('materials_used') or 'Standard operations.'}<br>
                                <b>Fiscal Audit:</b> Sanctioned ₹{r['budget_allocated']:,.0f} | Actual Spent: <b style="color:#2563eb;">₹{r['amount_spent']:,.0f}</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    c_before, c_after = st.columns(2)
                    with c_before:
                        st.caption("🔴 Before (Citizen Report)")
                        b_url = get_telegram_url(r['media_file_id'])
                        if b_url: display_media(b_url, r.get('media_type'))
                    with c_after:
                        st.caption("🟢 After (Govt Proof)")
                        a_url = get_telegram_url(r['resolution_media_id'])
                        if a_url: display_media(a_url, 'photo')
                    st.write("---")
            else: st.info("No resolved grievances yet.")
    else: st.info("Database is empty. Submit via Telegram.")

elif page == "📊 Open Data Analytics":
    st.title("Live Municipal Analytics")
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Grievances by Department")
            fig1 = px.pie(df, names='category', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            st.subheader("Status Pipeline")
            fig2 = px.bar(df['status'].value_counts().reset_index(), x='status', y='count', color='status')
            st.plotly_chart(fig2, use_container_width=True)
    else: st.warning("Not enough data to render analytics.")

elif page == "🔐 Officer Gateway":
    st.title("Administrative Access Gateway")
    if time.time() < st.session_state.lockout_time:
        st.error(f"🚨 Security Lockout: Try again in {int(st.session_state.lockout_time - time.time())}s.")
    else:
        _, col, _ = st.columns([1, 1.2, 1])
        with col:
            st.markdown('<div class="stat-card">', unsafe_allow_html=True)
            st.subheader("Secure Verification")
            with st.form("auth"):
                uid = st.text_input("GovID")
                pwd = st.text_input("Passkey", type="password")
                if st.form_submit_button("Access Portal", use_container_width=True):
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
            
            # Use universal display for Officer view too
            c_url = get_telegram_url(row['media_file_id'])
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
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": row['chat_id'], "text": f"🏛️ Ticket `{sel_id}` routed to {target_office}.\n🚥 {new_stage}\n💰 Sanctioned: ₹{budget_alloc:,.0f}"})
                        st.success("Dispatched successfully!")
                        st.rerun()

            elif st.session_state.role == "field":
                st.info(f"💰 **Locked Budget:** ₹{row['budget_allocated']:,.0f} | **Contractor:** {row.get('contractor_name') or 'Internal'}")
                with st.form("field_form"):
                    materials = st.text_area("Measurement Book (BOQ & Materials Used):", placeholder="Enter actions taken...")
                    spent = st.number_input("Final Treasury Payout (Amount Spent ₹):", value=float(row['budget_allocated']), step=1000.0)
                    proof = st.file_uploader("Upload Photographic Resolution Proof:", type=['jpg', 'jpeg', 'png'])
                    
                    if st.form_submit_button("Submit Resolution Proof", type="primary", use_container_width=True):
                        if not proof: st.error("Proof photograph is mandatory.")
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
    st.title("Geospatial Map")
    if not df.empty and not df['lat'].isnull().all():
        st.map(df.dropna(subset=['lat', 'lon']).rename(columns={"lat": "latitude", "lon": "longitude"}))
    else: st.warning("No geospatial telemetry available.")