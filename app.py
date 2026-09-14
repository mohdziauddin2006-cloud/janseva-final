import os
import requests
import streamlit as st
import pandas as pd
from backend import get_all_complaints, execute_admin_sanction, execute_field_resolution

st.set_page_config(page_title="JanSeva DPI", layout="wide", page_icon="🏛️")

# Figma-Style UI Tokens
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; font-family: 'Inter', sans-serif; }
    .metric-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; border-top: 4px solid #0f172a; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
    .metric-label { font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 28px; font-weight: 800; color: #0f172a; }
    .audit-card { background: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# Authentication State
if "role" not in st.session_state: st.session_state.role = "public"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Data Ingestion & Formatting
rows = get_all_complaints()
cols = ["ID", "Time", "ChatID", "User", "RawText", "MediaType", "MediaID", "Lat", "Lon", "Cat", "Sev", "Sum", "Status", "Office", "Officer", "BudgetAlloc", "AmtSpent", "Contractor", "Materials", "ResMediaID", "ResTime"]
df = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)

if not df.empty:
    df['BudgetAlloc'] = pd.to_numeric(df['BudgetAlloc']).fillna(0)
    df['AmtSpent'] = pd.to_numeric(df['AmtSpent']).fillna(0)

# Sidebar Routing
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=60)
    st.title("JanSeva DPI")
    st.caption("Digital Public Infrastructure")
    st.divider()

    if st.session_state.role == "public":
        st.subheader("Public Audit Mode")
        page = st.radio("Navigation", ["🌐 Social Audit Ledger", "📍 Jurisdictional Map"])
        st.divider()
        with st.form("login"):
            st.caption("Secure Portal Access")
            user = st.text_input("GovID")
            pwd = st.text_input("Passkey", type="password")
            if st.form_submit_button("Authenticate"):
                if user == "admin" and pwd == "admin123":
                    st.session_state.role = "executive"
                    st.rerun()
                elif user == "field" and pwd == "field123":
                    st.session_state.role = "field_officer"
                    st.rerun()
                else:
                    st.error("Invalid GovID")
    else:
        st.success(f"🔐 Secured as: {st.session_state.role.upper()}")
        if st.session_state.role == "executive":
            page = st.radio("Navigation", ["🏛️ Executive Sanctions", "🌐 Social Audit Ledger"])
        else:
            page = st.radio("Navigation", ["👷 Field Execution (MB)", "🌐 Social Audit Ledger"])
        if st.button("Logout"):
            st.session_state.role = "public"
            st.rerun()

# -------------------------------------------------------------
# TIER 1: PUBLIC TRANSPARENCY (SOCIAL AUDIT)
# -------------------------------------------------------------
if page == "🌐 Social Audit Ledger":
    st.title("Citizens' Social Audit Ledger")
    st.caption("End-to-end transparency: Track physical resolutions, engineering specifications, and fiscal spending.")
    
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        resolved = df[df["Status"].str.contains("Resolved")]
        c1.markdown(f'<div class="metric-card"><div class="metric-label">Total Projects Sanctioned</div><div class="metric-value">{len(df)}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><div class="metric-label">Public Funds Allocated</div><div class="metric-value">₹{df["BudgetAlloc"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><div class="metric-label">Completed & Audited</div><div class="metric-value" style="color:#10b981;">{len(resolved)}</div></div>', unsafe_allow_html=True)
        
        st.write("<br>", unsafe_allow_html=True)
        
        for _, row in df.iterrows():
            with st.container():
                st.markdown(f'''
                    <div class="audit-card">
                        <h4 style="margin:0; color:#0f172a;">{row['Office']}</h4>
                        <span style="color:#64748b; font-size:14px;">Ticket: {row['ID']} | Current Stage: <b>{row['Status']}</b></span>
                        <hr style="margin:10px 0;">
                        <div style="display:flex; justify-content:space-between; font-size:14px;">
                            <div><b>Officer:</b> {row['Officer']}</div>
                            <div><b>Contractor:</b> {row['Contractor'] if row['Contractor'] else 'Awaiting Tender'}</div>
                            <div><b>Allocated:</b> ₹{row['BudgetAlloc']:,.0f}</div>
                            <div><b>Spent:</b> ₹{row['AmtSpent']:,.0f}</div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                # Show Proof for Resolved
                if "Resolved" in row["Status"] and pd.notna(row["ResMediaID"]) and BOT_TOKEN:
                    try:
                        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={row['ResMediaID']}").json()
                        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
                        st.image(url, width=400, caption=f"Physical Completion Proof | Materials: {row['Materials']}")
                    except: pass
    else:
        st.info("Central ledger is currently empty.")

# -------------------------------------------------------------
# TIER 2: EXECUTIVE COMMAND (ADMIN SANCTION)
# -------------------------------------------------------------
elif page == "🏛️ Executive Sanctions":
    st.title("Executive Command: Admin & Technical Sanction")
    st.caption("Release budgets and float tenders. You cannot modify physical execution or upload proof.")
    
    active_df = df[~df["Status"].str.contains("Resolved")] if not df.empty else pd.DataFrame()
    
    if not active_df.empty:
        sel_id = st.selectbox("Select Project for Sanction:", active_df["ID"])
        row = active_df[active_df["ID"] == sel_id].iloc[0]
        
        st.write(f"**Jurisdiction:** {row['Office']} | **Request:** {row['RawText']}")
        
        with st.form("executive_form"):
            new_stage = st.selectbox("Advance Policy Lifecycle:", [
                "2. Preliminary Survey", "3. Administrative Sanction", "4. Tender Awarded"
            ], index=0)
            
            budget = st.number_input("Sanction Budget (₹)", value=float(row['BudgetAlloc']), step=5000.0)
            contractor = st.text_input("Awarded Contractor / Agency", value=str(row['Contractor']) if pd.notna(row['Contractor']) else "")
            
            if st.form_submit_button("Lock Sanction & Dispatch to Field"):
                execute_admin_sanction(sel_id, new_stage, budget, contractor)
                if row["ChatID"] and BOT_TOKEN:
                    msg = f"🏛️ **JanSeva Gov Update**\n🎫 Ticket `{sel_id}` advanced to:\n🚥 **{new_stage}**\n💰 Sanctioned: ₹{budget:,.2f}"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": row["ChatID"], "text": msg})
                st.success("Sanction officially locked in ledger.")
                st.rerun()
    else:
        st.success("No pending policy actions.")

# -------------------------------------------------------------
# TIER 3: FIELD OFFICER COMMAND (MEASUREMENT BOOK)
# -------------------------------------------------------------
elif page == "👷 Field Execution (MB)":
    st.title("Field Engineering: Measurement Book & Handover")
    st.caption("Upload physical proof, log materials, and finalize expenditure. You cannot alter sanctioned budgets.")
    
    # Field officer only works on Tendered projects
    field_df = df[df["Status"].str.contains("4. Tender Awarded|5. In Execution")] if not df.empty else pd.DataFrame()
    
    if not field_df.empty:
        sel_id = st.selectbox("Select Assigned Project:", field_df["ID"])
        row = field_df[field_df["ID"] == sel_id].iloc[0]
        
        st.info(f"💰 **Locked Sanction Budget:** ₹{row['BudgetAlloc']:,.2f} | **Contractor:** {row['Contractor']}")
        
        with st.form("field_form"):
            materials = st.text_area("Measurement Book (BOQ/Materials Consumed)", placeholder="e.g., Bitumen VG-30, M25 Concrete...")
            spent = st.number_input("Final Treasury Payout (Amount Spent ₹)", value=float(row['BudgetAlloc']), step=1000.0)
            proof_img = st.file_uploader("Upload Photographic Proof of Execution", type=['jpg', 'png'])
            
            if st.form_submit_button("Finalize MB & Submit to Social Audit"):
                media_id = None
                if proof_img and row["ChatID"] and BOT_TOKEN:
                    caption = f"✅ **Project Executed!**\n🎫 Ticket: `{sel_id}`\n🏢 {row['Office']}\n📉 Total Cost: ₹{spent:,.2f}\n📦 BOQ: {materials}"
                    res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={'chat_id': row["ChatID"], 'caption': caption}, files={'photo': proof_img.getvalue()}).json()
                    if res.get("ok"): media_id = res['result']['photo'][-1]['file_id']
                
                execute_field_resolution(sel_id, spent, materials, media_id)
                st.success("Measurement Book locked. Handed over to Public Social Audit.")
                st.rerun()
    else:
        st.success("No assigned tasks pending physical execution.")

elif page == "📍 Jurisdictional Map":
    st.title("Live Geospatial Map")
    if not df.empty and not df['Lat'].isnull().all():
        st.map(df.dropna(subset=['Lat', 'Lon']).rename(columns={"Lat": "latitude", "Lon": "longitude"}))
    else:
        st.warning("No geospatial telemetry available.")