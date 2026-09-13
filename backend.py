import os
import json
import math
import psycopg2
from datetime import datetime
from google import genai

DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # Using a brand new table name to guarantee a clean slate
    cur.execute("""
        CREATE TABLE IF NOT EXISTS janseva_tickets (
            id TEXT PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            chat_id TEXT,
            user_name TEXT,
            raw_text TEXT,
            media_type TEXT,
            media_file_id TEXT,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION,
            ward TEXT,
            category TEXT,
            department TEXT,
            severity TEXT,
            summary TEXT,
            status TEXT DEFAULT 'Pending'
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def analyze_grievance(text):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    Analyze this civic grievance: "{text}"
    Return ONLY a valid JSON object with keys:
    - "category": [Sanitation, Roads, Water, Electricity, Health]
    - "department": [Waste Dept, Public Works, Water Board, Power Bureau, Health Dept]
    - "severity": "High" | "Medium" | "Low"
    - "summary": 1 concise sentence summary
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        clean = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except:
        return {"category": "General", "department": "Civic Body", "severity": "Medium", "summary": text[:80] if text else "Media attached"}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def check_50m_density(lat, lon):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT lat, lon FROM janseva_tickets WHERE status != 'Resolved' AND lat IS NOT NULL AND lon IS NOT NULL")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    cluster_count = sum(1 for r_lat, r_lon in rows if haversine(lat, lon, r_lat, r_lon) <= 50)
    return "🔥 CRITICAL" if cluster_count >= 3 else None

def save_grievance(chat_id, user_name, raw_text, media_type, media_file_id, lat, lon):
    init_db()
    ai_data = analyze_grievance(raw_text if raw_text else f"{media_type} uploaded")
    
    density_sev = check_50m_density(lat, lon) if (lat and lon) else None
    final_sev = density_sev if density_sev else ai_data.get("severity", "Medium")
    
    ticket_id = f"GRV-{datetime.now().strftime('%m%d%H%M%S')}"
    ward = "Ward 1 - Central" 
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO janseva_tickets (id, chat_id, user_name, raw_text, media_type, media_file_id, lat, lon, ward, category, department, severity, summary, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
    """, (ticket_id, str(chat_id), user_name, raw_text, media_type, media_file_id, lat, lon, ward, ai_data.get("category"), ai_data.get("department"), final_sev, ai_data.get("summary")))
    conn.commit()
    cur.close()
    conn.close()
    
    return {"ticket_id": ticket_id, "category": ai_data.get("category"), "severity": final_sev, "summary": ai_data.get("summary")}

def get_all_complaints():
    init_db()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, timestamp::text, chat_id, user_name, raw_text, media_type, media_file_id, lat, lon, ward, category, department, severity, summary, status FROM janseva_tickets ORDER BY timestamp DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def update_ticket_status(ticket_id, new_status):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE janseva_tickets SET status = %s WHERE id = %s", (new_status, ticket_id))
    conn.commit()
    cur.close()
    conn.close()