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
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS janseva_tickets (
                id TEXT PRIMARY KEY, timestamp TIMESTAMPTZ DEFAULT NOW(),
                chat_id TEXT, user_name TEXT, raw_text TEXT, 
                media_type TEXT, media_file_id TEXT, lat DOUBLE PRECISION, lon DOUBLE PRECISION,
                category TEXT, severity TEXT, summary TEXT, status TEXT DEFAULT '1. Pending Review',
                office_name TEXT, assigned_officer TEXT,
                budget_allocated NUMERIC DEFAULT 0, amount_spent NUMERIC DEFAULT 0,
                contractor_name TEXT, materials_used TEXT,
                resolution_media_id TEXT, resolved_at TIMESTAMPTZ
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def analyze_and_route(text):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    Analyze this civic grievance: "{text}"
    Generate a JSON object:
    - "category": Strictly ONE of [Roads, Water, Electricity, Sanitation, Cyber Crime, Civil]
    - "severity": "High" | "Medium" | "Low"
    - "summary": 1 concise sentence
    - "office_name": Exact statutory body (e.g., "State PWD Roads Division").
    - "assigned_officer": Realistic title (e.g., "Er. S. Reddy, JE (Civil)").
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        clean = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        return {
            "category": "Civil", "severity": "Medium", "summary": text[:80] if text else "Civic issue",
            "office_name": "Municipal Engineering Division", "assigned_officer": "Nodal Officer"
        }

def save_grievance(chat_id, user_name, raw_text, media_type, media_file_id, lat, lon):
    init_db()
    ai_data = analyze_and_route(raw_text if raw_text else f"{media_type} attached")
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
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM janseva_tickets ORDER BY timestamp DESC")
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return [dict(zip(cols, row)) for row in rows]
    except:
        return []

def execute_admin_sanction(ticket_id, status, budget, contractor, category, office_name, assigned_officer):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE janseva_tickets SET status = %s, budget_allocated = %s, contractor_name = %s,
        category = %s, office_name = %s, assigned_officer = %s WHERE id = %s
    """, (status, budget, contractor, category, office_name, assigned_officer, ticket_id))
    conn.commit()
    cur.close()
    conn.close()

def execute_field_resolution(ticket_id, spent, materials, media_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE janseva_tickets SET status = '6. Resolved (Social Audit)', amount_spent = %s, 
        materials_used = %s, resolution_media_id = %s, resolved_at = NOW() WHERE id = %s
    """, (spent, materials, media_id, ticket_id))
    conn.commit()
    cur.close()
    conn.close()