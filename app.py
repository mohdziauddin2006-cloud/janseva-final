import os
import time
import requests
import streamlit as st
import pandas as pd
from backend import get_all_complaints, execute_admin_sanction, execute_field_resolution

st.set_page_config(page_title="JanSeva DPI - National Grievance Infrastructure", layout="wide", page_icon="🏛️")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Design System CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    .main { background-color: #f8fafc; }
    
    .stat-card {
        background: #ffffff;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #0f766e;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .stat-label { font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-val { font-size: 26px; font-weight: 700; color: #0f172a; margin-top: 4px; }
    
    .ticket-container {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 16px;
        transition: border-color 0.15s ease;
    }
    .ticket-container:hover { border-color: #cbd5e1; }
    
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-pending { background-color: #fef3c7; color: #92400e; }
    .badge-progress { background-color: #e0f2fe; color: #0369a1; }
    .badge-resolved { background-color: #dcfce7; color: #15803d; }
    .badge-emergency { background-color: #fee2e2; color: #b91c1c; }
    
    .media-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 12px;
        margin-top: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# State Management
if "role" not in st.session_state: st.session_state.role = "public"
if "dept" not in st.session_state: st.session_state.dept = None
if "login_attempts" not in st.session_state: st.session_state.login_attempts = 0
if "lockout_time" not in st.session_state: st.session_state.lockout_time = 0

# Department Routing Directory
DEPT_DIRECTORY = {
    "Roads": {
        "office": "State PWD Roads & Bridges Division",
        "officer": "Er. Rajesh Varma, Junior Engineer (Civil)"
    },
    "Water": {
        "office": "Municipal Water Supply & Sewerage Board",
        "officer": "Er. K. Ramesh, Assistant Executive Engineer (Water)"
    },
    "Electricity": {
        "office": "State Power Distribution Corporation (DISCOM)",
        "officer": "Er. M. Praveen, Sub-Divisional Engineer (Power)"
    },
    "Sanitation": {
        "office": "Solid Waste Management & Public Health Bureau",
        "officer": "Dr. A. Rao, Chief Sanitary Inspector"
    },
    "Cyber Crime": {
        "office": "State Cyber Crime Investigation Police Station",
        "officer": "Inspector S. Reddy, Cyber Cell"
    },
    "Civil": {
        "office": "Municipal Corporation Zonal Engineering Office",
        "officer": "Er. P. Naidu, Executive Engineer"
    }
}

# Role Credentials
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
        res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=4).json()
        if res.get("ok"):
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{res['result']['file_path']}"
    except Exception:
        pass
    return None

def render_status_badge(status):
    if "Resolved" in status:
        return f'<span class="badge badge-resolved">{status}</span>'
    elif "Tender" in status or "Survey" in status or "Sanction" in status:
        return f'<span class="badge badge-progress">{status}</span>'
    elif "CRITICAL" in status or "High" in status:
        return f'<span class="badge badge-emergency">{status}</span>'
    return f'<span class="badge badge-pending">{status}</span>'

# Sidebar Navigation
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=60)
    st.markdown("### **JanSeva DPI**")
    st.caption("National Grievance Infrastructure")
    st.divider()
    
    if st.session_state.role == "public":
        page = st.radio("Navigation", ["🌐 Citizens' Public Portal", "📍 Geospatial Incident Map", "🔐 Officer Gateway"])
    else:
        st.success(f"**Authenticated:** {st.session_state.role.upper()}\n\n**Jurisdiction:** {st.session_state.dept}")
        page = st.radio("Navigation", ["⚙️ Officer Command Dashboard", "🌐 Citizens' Public Portal"])
        if st.button("🚪 Sign Out", use_container_width=True):
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
    # Normalize empty or None fields
    df['category'] = df['category'].fillna("Civil").replace("None", "Civil")
    df['office_name'] = df['office_name'].fillna("Pending Assignment").replace("None", "Pending Assignment")
    df['assigned_officer'] = df['assigned_officer'].fillna("Awaiting Nodal Officer").replace("None", "Awaiting Nodal Officer")

# =========================================================
# 1. CITIZENS' PUBLIC PORTAL (NO LOGIN)
# =========================================================
if page == "🌐 Citizens' Public Portal":
    st.title("Public Transparency & Social Audit Ledger")
    st.caption("Open municipal record of registered grievances, verified repairs, and audited fiscal expenditure.")
    
    if not df.empty:
        total_cases = len(df)
        total_sanctioned = df['budget_allocated'].sum()
        total_spent = df['amount_spent'].sum()
        resolved_count = len(df[df['status'].str.contains("Resolved", case=False, na=False)])
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-card"><div class="stat-label">Total Grievances</div><div class="stat-val">{total_cases}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card"><div class="stat-label">Sanctioned Funds</div><div class="stat-val">₹{total_sanctioned:,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card"><div class="stat-label">Actual Spent</div><div class="stat-val">₹{total_spent:,.0f}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-card"><div class="stat-label">Verified Resolved</div><div class="stat-val" style="color:#15803d;">{resolved_count}</div></div>', unsafe_allow_html=True)
        
        st.write("<br>", unsafe_allow_html=True)
        
        tab_all, tab_resolved = st.tabs(["📋 All Registered Grievances", "📸 Verified Before/After Proof Feed"])
        
        # TAB 1: ALL COMPLAINTS WITH DATE AND FULL TEXT
        with tab_all:
            st.subheader("Public Grievance Registry")
            st.caption("Inspect live status, lodged timestamps, and assigned statutory offices for every report.")
            
            for _, item in df.iterrows():
                time_str = item['timestamp_dt'].strftime('%d %b %Y, %I:%M %p') if pd.notna(item['timestamp_dt']) else str(item['timestamp'])[:16]
                
                st.markdown(f"""
                    <div class="ticket-container">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <div>
                                <span style="font-size:16px; font-weight:700; color:#0f172a;">Ticket #{item['id']}</span>
                                <span style="margin-left:8px;">{render_status_badge(item['status'])}</span>
                            </div>
                            <span style="font-size:13px; color:#64748b; font-weight:500;">📅 Lodged: {time_str}</span>
                        </div>
                        <div style="margin-top:10px; font-size:14px; color:#334155; line-height:1.5;">
                            <b>Reported Problem:</b> {item['raw_text']}
                        </div>
                        <hr style="margin:12px 0; border:0; border-top:1px solid #f1f5f9;">
                        <div style="display:flex; flex-wrap:wrap; gap:20px; font-size:13px; color:#475569;">
                            <div><b>Department:</b> {item['category']}</div>
                            <div><b>Assigned Office:</b> {item['office_name']}</div>
                            <div><b>Nodal Officer:</b> {item['assigned_officer']}</div>
                            <div><b>Sanctioned:</b> ₹{item['budget_allocated']:,.0f}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Expandable media drawer
                with st.expander(f"Inspect Attached Media for #{item['id']}"):
                    media_url = get_telegram_url(item['media_file_id'])
                    if media_url:
                        if str(item.get('media_type')).lower() == 'photo':
                            st.image(media_url, caption="Citizen Submitted Photograph", width=380)
                        elif str(item.get('media_type')).lower() in ['video', 'animation']:
                            st.video(media_url)
                        else:
                            st.markdown(f"[📥 Download Citizen File]({media_url})")
                    else:
                        st.caption("No media attached with this complaint.")

        # TAB 2: RESOLUTION PROOF (BEFORE AND AFTER)
        with tab_resolved:
            st.subheader("Social Audit Proof Feed")
            st.caption("Side-by-side photographic evidence showing original conditions against official government repairs.")
            
            resolved_subset = df[df['status'].str.contains("Resolved", case=False, na=False)]
            if not resolved_subset.empty:
                for _, r in resolved_subset.iterrows():
                    res_time_str = str(r.get('resolved_at'))[:16] if pd.notna(r.get('resolved_at')) else "Completed"
                    
                    st.markdown(f"""
                        <div class="ticket-container">
                            <div style="display:flex; justify-content:space-between;">
                                <span style="font-weight:700; color:#0f172a;">{r['category']} — {r['office_name']}</span>
                                <span style="font-size:13px; color:#15803d; font-weight:600;">✅ Verified Resolved: {res_time_str}</span>
                            </div>
                            <div style="margin-top:8px; font-size:14px; color:#334155;">
                                <b>Original Issue:</b> {r['raw_text']}<br>
                                <b>Measurement Book (BOQ / Materials):</b> {r.get('materials_used') or 'Standard repair specifications'}<br>
                                <b>Fiscal Audit:</b> Sanctioned ₹{r['budget_allocated']:,.0f} | Actual Treasury Spent: <b>₹{r['amount_spent']:,.0f}</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    c_before, c_after = st.columns(2)
                    with c_before:
                        st.markdown('<div class="media-card"><b>1. Citizen Complaint (Before)</b>', unsafe_allow_html=True)
                        before_url = get_telegram_url(r['media_file_id'])
                        if before_url:
                            st.image(before_url, use_container_width=True)
                        else:
                            st.caption("No initial photo provided.")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    with c_after:
                        st.markdown('<div class="media-card"><b>2. Government Resolution Proof (After)</b>', unsafe_allow_html=True)
                        after_url = get_telegram_url(r['resolution_media_id'])
                        if after_url:
                            st.image(after_url, use_container_width=True)
                        else:
                            st.caption("Completion photo pending upload.")
                        st.markdown('</div>', unsafe_allow_html=True)
                    st.write("---")
            else:
                st.info("No grievances have been marked as resolved yet.")
    else:
        st.info("Central database is ready. Submit a complaint via Telegram to generate the live audit trail.")

# =========================================================
# 2. OFFICER AUTHENTICATION GATEWAY
# =========================================================
elif page == "🔐 Officer Gateway":
    st.title("Administrative Access Gateway")
    st.caption("Single Sign-On for District Collectors, Zonal Commissioners, and Field Engineers.")
    
    current_time = time.time()
    if current_time < st.session_state.lockout_time:
        remaining = int(st.session_state.lockout_time - current_time)
        st.error(f"🚨 Security Lockout: Too many failed attempts. Try again in {remaining} seconds.")
    else:
        col_pad1, col_center, col_pad2 = st.columns([1, 1.4, 1])
        with col_center:
            st.markdown('<div class="stat-card" style="border-top: 4px solid #0f172a;">', unsafe_allow_html=True)
            st.subheader("Officer Verification")
            with st.form("auth_form"):
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
                        else:
                            st.error(f"Access Denied. Incorrect credentials ({st.session_state.login_attempts}/3).")
            st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 3. OFFICER COMMAND DASHBOARD (EXECUTIVE & FIELD)
# =========================================================
elif page == "⚙️ Officer Command Dashboard":
    st.title(f"Command Dashboard — {st.session_state.dept.upper()}")
    
    if not df.empty:
        # FILTER: If field officer, only display tickets matching their department
        if st.session_state.role == "field":
            working_df = df[df['category'].str.contains(st.session_state.dept, case=False, na=False)].copy()
        else:
            working_df = df.copy() # Collector sees all
            
        active_df = working_df[~working_df['status'].str.contains("Resolved", case=False, na=False)]
        
        if not active_df.empty:
            sel_id = st.selectbox("Select Active Grievance to Process:", active_df["id"].tolist())
            row = active_df[active_df["id"] == sel_id].iloc[0]
            
            # Show ticket context
            st.markdown(f"""
                <div class="ticket-container">
                    <h4>Ticket #{row['id']}</h4>
                    <p><b>Citizen Grievance:</b> {row['raw_text']}</p>
                    <p><b>Current Category:</b> {row['category']} | <b>Current Office:</b> {row['office_name']}</p>
                    <p><b>Assigned Officer:</b> {row['assigned_officer']} | <b>Status:</b> {row['status']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Show original complaint photo
            c_url = get_telegram_url(row['media_file_id'])
            if c_url:
                st.image(c_url, width=350, caption="Citizen Submitted Photograph")
            
            # ----------------------------------------------------
            # TIER A: DISTRICT EXECUTIVE / COLLECTOR ACTIONS
            # ----------------------------------------------------
            if st.session_state.role == "admin":
                st.subheader("🏛️ Executive Jurisdictional Routing & Sanctions")
                st.caption("Re-route this grievance to the responsible department, sanction funding, and issue tenders.")
                
                with st.form("collector_form"):
                    # Select Department
                    current_cat = row['category'] if row['category'] in DEPT_DIRECTORY else "Roads"
                    dept_keys = list(DEPT_DIRECTORY.keys())
                    selected_dept = st.selectbox(
                        "Route to Statutory Department:", 
                        dept_keys, 
                        index=dept_keys.index(current_cat) if current_cat in dept_keys else 0
                    )
                    
                    # Auto-mapped default values
                    default_office = DEPT_DIRECTORY[selected_dept]["office"]
                    default_officer = DEPT_DIRECTORY[selected_dept]["officer"]
                    
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        target_office = st.text_input("Designated Office Name:", value=default_office)
                    with col_d2:
                        target_officer = st.text_input("Assigned Nodal Officer:", value=default_officer)
                    
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        stages = ["2. Survey & Estimation", "3. Administrative Sanction", "4. Tender Awarded"]
                        new_stage = st.selectbox("Advance Policy Lifecycle:", stages, index=0)
                    with col_s2:
                        budget_alloc = st.number_input("Sanction Budget (₹):", value=float(row['budget_allocated']), step=5000.0)
                    
                    contractor = st.text_input("Awarded Contractor / Agency:", value=str(row.get('contractor_name') or ''))
                    
                    if st.form_submit_button("Lock Sanction & Dispatch to Department", use_container_width=True):
                        execute_admin_sanction(
                            sel_id, 
                            new_stage, 
                            budget_alloc, 
                            contractor, 
                            selected_dept, 
                            target_office, 
                            target_officer
                        )
                        
                        # Notify citizen via Telegram
                        if pd.notna(row['chat_id']) and BOT_TOKEN:
                            msg = (
                                f"🏛️ **JanSeva Official Update**\n"
                                f"🎫 Ticket: `{sel_id}`\n"
                                f"🏢 **Routed To:** {target_office}\n"
                                f"👤 **Officer:** {target_officer}\n"
                                f"🚥 **Lifecycle:** {new_stage}\n"
                                f"💰 **Budget Sanctioned:** ₹{budget_alloc:,.2f}"
                            )
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": row['chat_id'], "text": msg, "parse_mode": "Markdown"})
                            
                        st.success(f"Ticket #{sel_id} successfully dispatched to {selected_dept} Department!")
                        st.rerun()

            # ----------------------------------------------------
            # TIER B: FIELD OFFICER ACTIONS (PWD, JAL, POWER, ETC.)
            # ----------------------------------------------------
            elif st.session_state.role == "field":
                st.subheader("👷 Field Execution & Measurement Book")
                st.caption(f"Log materials used, record actual expenditure, and upload visual proof of resolution.")
                st.info(f"💰 **Locked Sanction Budget:** ₹{row['budget_allocated']:,.2f} | **Contractor:** {row.get('contractor_name') or 'Departmental Work'}")
                
                with st.form("field_resolve_form"):
                    materials_consumed = st.text_area("Measurement Book (BOQ & Materials Used):", placeholder="e.g. 50mm Bituminous concrete laid, 200m pipeline replaced...")
                    actual_spent = st.number_input("Final Treasury Payout (Amount Spent ₹):", value=float(row['budget_allocated']), step=1000.0)
                    proof_photo = st.file_uploader("Upload Photographic Resolution Proof:", type=['jpg', 'jpeg', 'png'])
                    
                    if st.form_submit_button("Submit Resolution & Pass to Social Audit", use_container_width=True):
                        if not proof_photo:
                            st.error("Physical proof photograph is mandatory to close this grievance.")
                        else:
                            media_id = None
                            if pd.notna(row['chat_id']) and BOT_TOKEN:
                                caption = (
                                    f"✅ **Grievance Resolved!**\n"
                                    f"🎫 **Ticket ID:** `{sel_id}`\n"
                                    f"🏢 **Office:** {row['office_name']}\n"
                                    f"📉 **Final Cost:** ₹{actual_spent:,.2f}\n"
                                    f"📦 **Materials:** {materials_consumed}"
                                )
                                res = requests.post(
                                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                                    data={"chat_id": row['chat_id'], "caption": caption, "parse_mode": "Markdown"},
                                    files={"photo": proof_photo.getvalue()}
                                ).json()
                                if res.get("ok"):
                                    media_id = res["result"]["photo"][-1]["file_id"]
                                    
                            execute_field_resolution(sel_id, actual_spent, materials_consumed, media_id)
                            st.success("Work completed and verified. Record published to Public Social Audit.")
                            st.rerun()
        else:
            st.success(f"No pending grievances in {st.session_state.dept} jurisdiction.")
    else:
        st.info("No complaints found in the database.")

# =========================================================
# 4. GEOSPATIAL MAP (PUBLIC ACCESS)
# =========================================================
elif page == "📍 Geospatial Incident Map":
    st.title("Geospatial Incident & Density Map")
    if not df.empty and not df['lat'].isnull().all():
        valid_map = df.dropna(subset=['lat', 'lon']).copy()
        st.map(valid_map.rename(columns={"lat": "latitude", "lon": "longitude"}))
        st.subheader("Geotagged Incident Registry")
        st.dataframe(valid_map[["id", "timestamp", "category", "office_name", "status", "lat", "lon"]], use_container_width=True, hide_index=True)
    else:
        st.warning("No geospatial telemetry available.")