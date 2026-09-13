import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from backend import get_all_complaints, update_ticket_status

st.set_page_config(page_title="JanSeva Dashboard", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f9fafb; font-family: sans-serif; }
    .kpi-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-top: 4px solid #4b5563; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🏛️ JanSeva AI")
    page = st.radio("Navigation", ["Overview", "Spatial Map", "Action Board"])

rows = get_all_complaints()
cols = ["ID", "Time", "ChatID", "User", "RawText", "MediaType", "MediaID", "Lat", "Lon", "Ward", "Cat", "Dept", "Sev", "Sum", "Status"]
df = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)

if page == "Overview":
    st.title("Municipal Operations")
    
    total = len(df)
    pending = len(df[df["Status"] == "Pending"]) if not df.empty else 0
    critical = len(df[df["Sev"].astype(str).str.contains("CRITICAL")]) if not df.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="kpi-card">Total Tickets<h2>{total}</h2></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card" style="border-top-color:#f59e0b;">Pending<h2>{pending}</h2></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card" style="border-top-color:#ef4444;">Critical (50m)<h2>{critical}</h2></div>', unsafe_allow_html=True)
    
    st.write("---")
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.bar(df["Cat"].value_counts().reset_index(), x="Cat", y="count", title="Categories"), use_container_width=True)
        with col2:
            st.plotly_chart(px.pie(df["Status"].value_counts().reset_index(), values="count", names="Status", title="Resolution Status"), use_container_width=True)
    else:
        st.info("The dashboard is ready. Open your Telegram Bot and send a complaint to see the charts!")

elif page == "Spatial Map":
    st.title("50m Density Hotspots")
    if not df.empty and not df['Lat'].isnull().all():
        st.map(df.dropna(subset=['Lat', 'Lon']).rename(columns={"Lat": "latitude", "Lon": "longitude"}))
    else:
        st.warning("No GPS locations submitted yet.")

elif page == "Action Board":
    st.title("Update SLA & Inspect Evidence")
    if not df.empty:
        st.dataframe(df[["ID", "Cat", "Sev", "Status", "Sum"]], use_container_width=True, hide_index=True)
        st.divider()
        colA, colB = st.columns(2)
        with colA:
            sel_id = st.selectbox("Select Ticket ID:", df["ID"])
            row = df[df["ID"] == sel_id].iloc[0]
            st.write(f"**Report:** {row['RawText']}")
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if pd.notna(row["MediaID"]) and token:
                try:
                    f_info = requests.get(f"https://api.telegram.org/bot{token}/getFile?file_id={row['MediaID']}").json()
                    if f_info.get("ok"):
                        url = f"https://api.telegram.org/file/bot{token}/{f_info['result']['file_path']}"
                        m_type = str(row["MediaType"]).lower()
                        
                        # Added support for animation (GIFs), audio, and documents
                        if m_type == "photo": st.image(url, width=300)
                        elif m_type in ["video", "animation"]: st.video(url)
                        elif m_type in ["voice", "audio"]: st.audio(url)
                        else: st.markdown(f"[📥 Download Attached File]({url})")
                except: st.warning("Media load failed.")
        with colB:
            new_stat = st.selectbox("New Status:", ["Pending", "In Progress", "Resolved"])
            if st.button("Update & Notify"):
                update_ticket_status(sel_id, new_stat)
                if row["ChatID"] and token:
                    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": row["ChatID"], "text": f"🔔 Ticket `{sel_id}` is now {new_stat}."})
                st.success("Updated!")
                st.rerun()
    else:
        st.info("No tickets to manage yet.")