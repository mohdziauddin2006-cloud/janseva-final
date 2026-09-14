import os, time, requests
import streamlit as st
import pandas as pd
from backend import get_all_complaints, execute_admin_sanction, execute_field_resolution

st.set_page_config(page_title="JanSeva DPI", layout="wide", page_icon="🏛️")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Styling: Institutional Aesthetic & Grid
st.markdown("""
    <style>
    .main { background-color: #f8fafc; font-family: 'Segoe UI', Tahoma, sans-serif; }
    .kpi-card { background: white; padding: 20px; border-radius: 8px; border-top: 4px solid #0f172a; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .kpi-val { font-size: 28px; font-weight: 700; color: #0f172a; }
    .evidence-box { border: 1px solid #e2e8f0; padding: 10px; border-radius: 6px; background: #fff; }
    </style>
""", unsafe_allow_html=True)

# State Management for Security Citadel
if "role" not in st.session_state: st.session_state.role = "public"
if "dept" not in st.session_state: st.session_state.dept = None
if "login_attempts" not in st.session_state: st.session_state.login_attempts = 0
if "lockout_time" not in st.session_state: st.session_state.lockout_time = 0

# Auth Dictionary
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
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}", timeout=3).json()
        return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
    except: return None

# Sidebar Navigation
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=65)
    st.title("JanSeva DPI")
    
    if st.session_state.role == "public":
        page = st.radio("Navigation", ["🌐 Public Transparency Portal", "📍 Live Geospatial Map", "🔐 Secure Officer Login"])
    else:
        st.success(f"🔐 Authenticated: {st.session_state.role.upper()}\n🏢 Dept: {st.session_state.dept}")
        page = st.radio("Navigation", ["⚙️ Officer Command Dashboard", "🌐 Public Transparency Portal"])
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.role, st.session_state.dept = "public", None
            st.rerun()

# Load Data
df = pd.DataFrame(get_all_complaints())
if not df.empty:
    df['budget_allocated'] = pd.to_numeric(df['budget_allocated']).fillna(0)
    df['amount_spent'] = pd.to_numeric(df['amount_spent']).fillna(0)

# ==========================================
# PAGE: PUBLIC TRANSPARENCY & EVIDENCE TRAY
# ==========================================
if page == "🌐 Public Transparency Portal":
    st.title("Citizens' Social Audit Ledger")
    
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="kpi-card">Total Logged<div class="kpi-val">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="kpi-card">Public Funds Sanctioned<div class="kpi-val">₹{df["budget_allocated"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="kpi-card">Verified Resolved<div class="kpi-val" style="color:#059669;">{len(df[df["status"].str.contains("Resolved")])}</div></div>', unsafe_allow_html=True)
        
        st.divider()
        st.subheader("📸 Public Evidence & Audit Feed")
        resolved_df = df[df["status"].str.contains("Resolved")]
        
        if not resolved_df.empty:
            for _, r in resolved_df.iterrows():
                with st.expander(f"✅ {r['category']} - {r['office_name']} | Ticket: {r['id']}"):
                    st.write(f"**Action Taken / BOQ:** {r['materials_used']}")
                    st.write(f"**Budget:** Allocated ₹{r['budget_allocated']:,.0f} | Spent: ₹{r['amount_spent']:,.0f}")
                    
                    # Live Photo Evidence Side-by-Side
                    pic_col1, pic_col2 = st.columns(2)
                    with pic_col1:
                        st.markdown('<div class="evidence-box"><b>Citizen Complaint Photo</b>', unsafe_allow_html=True)
                        cit_url = get_telegram_url(r['media_file_id'])
                        if cit_url: st.image(cit_url, use_container_width=True)
                        else: st.caption("No photo provided.")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    with pic_col2:
                        st.markdown('<div class="evidence-box"><b>Govt Resolution Proof</b>', unsafe_allow_html=True)
                        gov_url = get_telegram_url(r['resolution_media_id'])
                        if gov_url: st.image(gov_url, use_container_width=True)
                        else: st.caption("No repair photo attached.")
                        st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No resolved tickets yet.")
    else:
        st.info("Database is empty.")

# ==========================================
# PAGE: SECURE OFFICER LOGIN (THE CITADEL)
# ==========================================
elif page == "🔐 Secure Officer Login":
    st.title("Central Authentication Gateway")
    
    # Check Lockout Timer
    current_time = time.time()
    if current_time < st.session_state.lockout_time:
        st.error(f"🚨 Security Lockout Active. Please wait {int(st.session_state.lockout_time - current_time)} seconds.")
    else:
        # 3-Column Layout to hide the login box centrally
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
            st.subheader("Officer Login")
            with st.form("auth_form"):
                uid = st.text_input("GovID (e.g., collector, pwd_roads)")
                pwd = st.text_input("Passkey", type="password")
                
                if st.form_submit_button("Authenticate", use_container_width=True):
                    if uid in AUTH_DB and AUTH_DB[uid]["pass"] == pwd:
                        st.session_state.role = AUTH_DB[uid]["role"]
                        st.session_state.dept = AUTH_DB[uid]["dept"]
                        st.session_state.login_attempts = 0 # Reset on success
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        if st.session_state.login_attempts >= 3:
                            st.session_state.lockout_time = time.time() + 60
                            st.session_state.login_attempts = 0
                            st.rerun()
                        else:
                            st.error(f"Invalid credentials. Attempt {st.session_state.login_attempts}/3.")
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# PAGE: OFFICER COMMAND (EXECUTIVE & FIELD)
# ==========================================
elif page == "⚙️ Officer Command Dashboard":
    st.title(f"{st.session_state.dept} Command Center")
    
    if not df.empty:
        # Filter tickets for Field Officers based on their Department
        if st.session_state.role == "field":
            df = df[df["category"].str.contains(st.session_state.dept, case=False, na=False)]
            
        active_df = df[~df["status"].str.contains("Resolved")]
        if not active_df.empty:
            sel_id = st.selectbox("Select Active Ticket:", active_df["id"])
            row = active_df[active_df["id"] == sel_id].iloc[0]
            
            st.write(f"**Issue:** {row['raw_text']}")
            st.write(f"**Office:** {row['office_name']} | **Officer:** {row['assigned_officer']}")
            
            # Show Original Complaint Photo to the Officer
            c_url = get_telegram_url(row['media_file_id'])
            if c_url: st.image(c_url, width=300)
            
            # ROLE: EXECUTIVE (District Magistrate)
            if st.session_state.role == "admin":
                with st.form("admin_form"):
                    new_stage = st.selectbox("Advance Stage:", ["2. Survey", "3. Admin Sanction", "4. Tender Awarded"])
                    budget = st.number_input("Sanction Budget (₹)", value=float(row['budget_allocated']), step=5000.0)
                    contractor = st.text_input("Awarded Contractor", value=str(row['contractor_name']) if pd.notna(row['contractor_name']) else "")
                    
                    if st.form_submit_button("Lock Sanction"):
                        execute_admin_sanction(sel_id, new_stage, budget, contractor)
                        if row["chat_id"] and BOT_TOKEN:
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": row["chat_id"], "text": f"🏛️ Ticket `{sel_id}` advanced to {new_stage}.\n💰 Sanctioned: ₹{budget:,.0f}"})
                        st.success("Sanction applied.")
                        st.rerun()
            
            # ROLE: FIELD OFFICER (Engineers / Police)
            elif st.session_state.role == "field":
                st.info(f"💰 **Locked Sanction Budget:** ₹{row['budget_allocated']:,.0f} | **Contractor:** {row['contractor_name']}")
                with st.form("field_form"):
                    spent = st.number_input("Amount Spent (₹)", value=float(row['budget_allocated']), step=1000.0)
                    materials = st.text_area("Measurement Book (Materials Used/Action Taken)", required=True)
                    proof_img = st.file_uploader("Upload Completion Photo (Visible to Public)", type=['jpg', 'png'])
                    
                    if st.form_submit_button("Submit Proof & Resolve"):
                        media_id = None
                        if proof_img and row["chat_id"] and BOT_TOKEN:
                            caption = f"✅ **Project Executed!**\n🎫 Ticket: `{sel_id}`\n📉 Total Cost: ₹{spent:,.0f}\n📦 BOQ: {materials}"
                            res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={'chat_id': row["chat_id"], 'caption': caption}, files={'photo': proof_img.getvalue()}).json()
                            if res.get("ok"): media_id = res['result']['photo'][-1]['file_id']
                        
                        execute_field_resolution(sel_id, spent, materials, media_id)
                        st.success("Ticket resolved. Added to Social Audit ledger.")
                        st.rerun()
        else:
            st.success("No active tickets in your jurisdiction.")
            
elif page == "📍 Live Geospatial Map":
    if not df.empty and not df['lat'].isnull().all():
        st.map(df.dropna(subset=['lat', 'lon']).rename(columns={"lat": "latitude", "lon": "longitude"}))
    else:
        st.warning("No GPS data available.")