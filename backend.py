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
    # Create base table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS janseva_tickets (
            id TEXT PRIMARY KEY, timestamp TIMESTAMPTZ DEFAULT NOW(),
            chat_id TEXT, user_name TEXT, raw_text TEXT, 
            media_type TEXT, media_file_id TEXT, lat DOUBLE PRECISION, lon DOUBLE PRECISION,
            category TEXT, severity TEXT, summary TEXT, status TEXT DEFAULT '1. Pending Review'
        );
    """)
    # Auto-Migrator: Inject Enterprise DPI Columns
    new_columns = [
        ("office_name", "TEXT"), ("assigned_officer", "TEXT"),
        ("budget_allocated", "NUMERIC DEFAULT 0"), ("amount_spent", "NUMERIC DEFAULT 0"),
        ("contractor_name", "TEXT"), ("materials_used", "TEXT"),
        ("resolution_media_id", "TEXT"), ("resolved_at", "TIMESTAMPTZ")
    ]
    for col_name, col_type in new_columns:
        cur.execute(f"ALTER TABLE janseva_tickets ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
    conn.commit()
    cur.close()
    conn.close()

def analyze_and_route_grievance(text):
    """Uses AI to dynamically map to real Pan-India statutory bodies."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    Analyze this civic grievance: "{text}"
    Based on the Indian administrative structure, generate a JSON object with:
    - "category": [Sanitation, Roads, Water, Electricity, Health, Cyber Crime, Civil]
    - "severity": "High" | "Medium" | "Low"
    - "summary": 1 concise sentence summary
    - "office_name": The specific statutory body that handles this (e.g., "State PWD Highway Division", "GHMC Circle 10", "Cyberabad Cyber Cell", "BBMP Ward Office").
    - "assigned_officer": A realistic title and name for the nodal officer (e.g., "Er. S. Reddy, Executive Engineer", "Inspector K. Sharma").
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        clean = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except:
        return {
            "category": "General", "severity": "Medium", "summary": text[:80],
            "office_name": "Municipal Corporation Branch", "assigned_officer": "Nodal Officer"
        }

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def save_grievance(chat_id, user_name, raw_text, media_type, media_file_id, lat, lon):
    init_db()
    ai_data = analyze_and_route_grievance(raw_text if raw_text else f"{media_type} uploaded")
    
    ticket_id = f"GRV-{datetime.now().strftime('%m%d%H%M%S')}"
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO janseva_tickets (
            id, chat_id, user_name, raw_text, media_type, media_file_id, lat, lon, 
            category, severity, summary, office_name, assigned_officer, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '1. Pending Review')
    """, (ticket_id, str(chat_id), user_name, raw_text, media_type, media_file_id, lat, lon, 
          ai_data.get("category"), ai_data.get("severity"), ai_data.get("summary"), 
          ai_data.get("office_name"), ai_data.get("assigned_officer")))
    conn.commit()
    cur.close()
    conn.close()
    return {"ticket_id": ticket_id, **ai_data}

def get_all_complaints():
    init_db()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, timestamp::text, chat_id, user_name, raw_text, media_type, media_file_id, 
               lat, lon, category, severity, summary, status, 
               office_name, assigned_officer, budget_allocated, amount_spent, 
               contractor_name, materials_used, resolution_media_id, resolved_at::text 
        FROM janseva_tickets ORDER BY timestamp DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def execute_admin_sanction(ticket_id, status, budget, contractor):
    """Executive triggers sanction & floating of tender."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE janseva_tickets 
        SET status = %s, budget_allocated = %s, contractor_name = %s 
        WHERE id = %s
    """, (status, budget, contractor, ticket_id))
    conn.commit()
    cur.close()
    conn.close()

def execute_field_resolution(ticket_id, spent, materials, media_id):
    """Field Officer triggers Measurement Book entry and Final Handover."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE janseva_tickets 
        SET status = '6. Resolved (Social Audit)', amount_spent = %s, materials_used = %s, 
            resolution_media_id = %s, resolved_at = NOW()
        WHERE id = %s
    """, (spent, materials, media_id, ticket_id))
    conn.commit()
    cur.close()
    conn.close()