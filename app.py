import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from backend import get_all_complaints, update_ticket_status

st.set_page_config(page_title="JanSeva National Command", layout="wide")

# Custom CSS matching institutional Figma design
st.markdown("""
    <style>
    .main { background-color: #f7f7f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .kpi-container {
        background-color: white;
        padding: 16px 20px;
        border-radius: 8px;
        border: 1px solid #e8e8e8;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .kpi-label { font-size: 14px; font-weight: 500; color: #555; display: flex; align-items: center; gap: 8px; }
    .kpi-val { font-size: 24px; font-weight: 700; }
    .val-total { color: #111; }
    .val-pending { color: #f59e0b; }
    .val-review { color: #3b82f6; }
    .val-resolved { color: #10b981; }
    .val-critical { color: #ef4444; }
    .dept-card {
        background-color: #fdfcf7;
        border: 1px solid #f0e6db;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        margin-bottom: 10px;
    }
    .dept-title { color: #800000; font-weight: 700; font-size: 16px; margin-bottom: 4px; }
    .dept-stat { font-size: 12px; color: #666; margin-bottom: 2px; }
    .dept-res { font-size: 12px; color: #10b981; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg", width=65)
    st.title("JanSeva AI")
    st.caption("National Grievance Portal")
    st.divider()
    page = st.radio("Navigation", ["Overview", "Spatial Map", "All Grievances"])

rows = get_all_complaints()
cols = ["ID", "Time", "ChatID", "User", "RawText", "MediaType", "MediaID", "Lat", "Lon", "Ward", "Cat", "Dept", "Sev", "Sum", "Status"]
df = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)

if page == "Overview":
    st.markdown("## Admin Dashboard")
    st.caption("Grievance Management — National Command Center")
    st.write("")

    total = len(df)
    pending = len(df[df["Status"] == "Pending"]) if not df.empty else 0
    review = len(df[df["Status"] == "In Progress"]) if not df.empty else 0
    resolved = len(df[df["Status"] == "Resolved"]) if not df.empty else 0
    critical = len(df[df["Sev"].astype(str).str.contains("CRITICAL")]) if not df.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(f'<div class="kpi-container"><div class="kpi-label">📄 Total</div><div class="kpi-val val-total">{total}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-container"><div class="kpi-label"><span style="color:#f59e0b;">🕒</span> Pending</div><div class="kpi-val val-pending">{pending}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-container"><div class="kpi-label"><span style="color:#3b82f6;">👁️</span> In Review</div><div class="kpi-val val-review">{review}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-container"><div class="kpi-label"><span style="color:#10b981;">✅</span> Resolved</div><div class="kpi-val val-resolved">{resolved}</div></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="kpi-container"><div class="kpi-label"><span style="color:#ef4444;">🚨</span> Critical</div><div class="kpi-val val-critical">{critical}</div></div>', unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)

    if not df.empty:
        col_bar, col_pie = st.columns([1.5, 1])
        with col_bar:
            st.markdown('<div style="background:white; padding:15px; border-radius:8px; border:1px solid #e8e8e8;"><b>Grievances by Category</b><br>', unsafe_allow_html=True)
            cat_df = df["Cat"].value_counts().reset_index()
            cat_df.columns = ["Category", "Count"]
            fig_bar = px.bar(cat_df, x="Category", y="Count", color_discrete_sequence=["#800000"])
            fig_bar.update_layout(plot_bgcolor="white", paper_bgcolor="white", margin=dict(t=20, l=0, r=0, b=0), height=280)
            fig_bar.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_pie:
            st.markdown('<div style="background:white; padding:15px; border-radius:8px; border:1px solid #e8e8e8;"><b>Status Distribution</b><br>', unsafe_allow_html=True)
            status_df = df["Status"].value_counts().reset_index()
            status_df.columns = ["Status", "Count"]
            color_map = {"Resolved": "#10b981", "Pending": "#f59e0b", "In Progress": "#3b82f6"}
            fig_pie = px.pie(status_df, values="Count", names="Status", color="Status", color_discrete_map=color_map, hole=0.0)
            fig_pie.update_layout(margin=dict(t=20, l=0, r=0, b=0), height=280, showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.write("<br>", unsafe_allow_html=True)

        st.markdown('<div style="background:white; padding:20px; border-radius:8px; border:1px solid #e8e8e8;"><b>Department-wise Summary</b><br><br>', unsafe_allow_html=True)
        depts = ["Waste Dept", "Public Works", "Water Board", "Power Bureau", "Health Dept", "Transport", "Civil", "Parks"]
        
        d_cols1 = st.columns(4)
        d_cols2 = st.columns(4)
        all_cols = d_cols1 + d_cols2
        
        for i, d in enumerate(depts):
            d_total = len(df[df["Dept"].astype(str).str.contains(d, case=False)])
            d_res = len(df[(df["Dept"].astype(str).str.contains(d, case=False)) & (df["Status"] == "Resolved")])
            rate = int((d_res / d_total * 100)) if d_total > 0 else 0
            
            with all_cols[i]:
                st.markdown(f'''
                    <div class="dept-card">
                        <div class="dept-title">{d.upper()}</div>
                        <div class="dept-stat">{d_total} total</div>
                        <div class="dept-res">{rate}% resolved</div>
                    </div>
                ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("The national dashboard is ready. Open your Telegram Bot and send a complaint to populate the UI.")

elif page == "Spatial Map":
    st.markdown("## Live 50m Density Hotspot Map")
    if not df.empty and not df['Lat'].isnull().all():
        valid_df = df.dropna(subset=['Lat', 'Lon']).copy()
        map_df = valid_df.rename(columns={"Lat": "latitude", "Lon": "longitude"})
        
        st.map(map_df)
        
        st.subheader("Coordinates Registry")
        st.dataframe(valid_df[["ID", "Ward", "Cat", "Sev", "Lat", "Lon", "Status"]], use_container_width=True, hide_index=True)
    else:
        st.warning("No GPS locations submitted yet.")

elif page == "All Grievances":
    st.markdown("## Recent Grievances")
    if not df.empty:
        def style_status(val):
            if val == "Resolved": return 'background-color: #d1fae5; color: #065f46; font-weight: bold; border-radius: 10px;'
            elif val == "Pending": return 'background-color: #fef3c7; color: #92400e; font-weight: bold; border-radius: 10px;'
            else: return 'background-color: #dbeafe; color: #1e40af; font-weight: bold; border-radius: 10px;'
            
        def style_priority(val):
            if "CRITICAL" in str(val) or "High" in str(val): return 'color: #ef4444; font-weight: bold;'
            elif "Medium" in str(val): return 'color: #f59e0b; font-weight: bold;'
            else: return 'color: #3b82f6; font-weight: bold;'

        display_df = df[["ID", "User", "Sum", "Cat", "Status", "Sev", "Time"]].copy()
        display_df.columns = ["ID", "Citizen", "Subject", "Category", "Status", "Priority", "Date"]
        
        styled_table = display_df.style.map(style_status, subset=['Status']).map(style_priority, subset=['Priority'])
        st.dataframe(styled_table, use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown("### Action Panel")
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
                        if m_type == "photo": st.image(url, width=300)
                        elif m_type in ["video", "animation"]: st.video(url)
                        elif m_type in ["voice", "audio"]: st.audio(url)
                        else: st.markdown(f"[📥 Download Attached File]({url})")
                except: st.warning("Media load failed.")
        with colB:
            new_stat = st.selectbox("Update SLA Status:", ["Pending", "In Progress", "Resolved"])
            if st.button("Save & Notify Citizen"):
                update_ticket_status(sel_id, new_stat)
                if row["ChatID"] and token:
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage", 
                        json={"chat_id": row["ChatID"], "text": f"🔔 Ticket `{sel_id}` is now {new_stat}."}
                    )
                st.success("Updated!")
                st.rerun()
    else:
        st.info("No tickets to manage yet.")