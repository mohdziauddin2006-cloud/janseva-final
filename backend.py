import os
import json
import psycopg2
from datetime import datetime
from google import genai
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Create Core Tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS departments (
                    id SERIAL PRIMARY KEY, 
                    name TEXT UNIQUE NOT NULL, 
                    tier TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS officers (
                    id SERIAL PRIMARY KEY, 
                    username TEXT UNIQUE NOT NULL, 
                    passkey TEXT NOT NULL, 
                    full_name TEXT NOT NULL, 
                    department_id INTEGER REFERENCES departments(id), 
                    role TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS janseva_tickets (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    chat_id TEXT, user_name TEXT, raw_text TEXT, 
                    media_type TEXT, media_file_id TEXT, lat DOUBLE PRECISION, lon DOUBLE PRECISION,
                    category TEXT, severity TEXT, summary TEXT, 
                    status TEXT DEFAULT '1. Pending Review',
                    office_name TEXT, assigned_officer TEXT,
                    budget_allocated NUMERIC DEFAULT 0, amount_spent NUMERIC DEFAULT 0,
                    contractor_name TEXT, materials_used TEXT,
                    resolution_media_id TEXT, resolved_at TIMESTAMPTZ
                );
            """)
            
            # 2. Seed All 16+ Departments
            departments = [
                "Roads & Infrastructure", "Water & Sanitation", "Electricity & Power", 
                "Transport (RTO)", "Revenue & Land", "Food & Civil Supplies", 
                "Police & Law Enforcement", "Public Health", "Urban Development", 
                "Pollution Control", "Fire & Rescue", "Women & Child Development", 
                "Labour Welfare", "Disaster Management", "Telecom & Postal", "Civil"
            ]
            for dept in departments:
                cur.execute("INSERT INTO departments (name, tier) VALUES (%s, 'Local') ON CONFLICT DO NOTHING", (dept,))
            cur.execute("INSERT INTO departments (name, tier) VALUES ('Govt of India', 'State') ON CONFLICT DO NOTHING")

            # 3. Seed All 16 Nodal Officers safely linked to their Departments
            officer_seed_data = [
                ('collector', 'ias2026', 'District Collector', 'Govt of India', 'admin'),
                ('rto_admin', 'rto2026', 'Transport Inspector', 'Transport (RTO)', 'field'),
                ('revenue_land', 'rev2026', 'Mandal Revenue Officer', 'Revenue & Land', 'field'),
                ('civil_supplies', 'pds2026', 'PDS Nodal Officer', 'Food & Civil Supplies', 'field'),
                ('police_hq', 'ips2026', 'Station House Officer', 'Police & Law Enforcement', 'field'),
                ('health_welfare', 'cmo2026', 'Chief Medical Officer', 'Public Health', 'field'),
                ('urban_dev', 'udp2026', 'Zonal Commissioner', 'Urban Development', 'field'),
                ('pollution_board', 'epb2026', 'Environmental Engineer', 'Pollution Control', 'field'),
                ('fire_rescue', 'fire2026', 'District Fire Officer', 'Fire & Rescue', 'field'),
                ('wcd_unit', 'wcd2026', 'Protection Officer', 'Women & Child Development', 'field'),
                ('labour_board', 'labour2026', 'Labour Commissioner', 'Labour Welfare', 'field'),
                ('disaster_mgmt', 'ndrf2026', 'NDRF Nodal Head', 'Disaster Management', 'field'),
                ('telecom_post', 'dot2026', 'Telecom Reg. Officer', 'Telecom & Postal', 'field'),
                ('pwd_roads', 'pwd2026', 'Executive Engineer', 'Roads & Infrastructure', 'field'),
                ('water_board', 'jal2026', 'Sanitary Inspector', 'Water & Sanitation', 'field'),
                ('electricity', 'power2026', 'Superintending Engineer', 'Electricity & Power', 'field')
            ]
            
            for uname, pwd, fname, dept_name, role in officer_seed_data:
                cur.execute("SELECT id FROM departments WHERE name = %s", (dept_name,))
                d_id = cur.fetchone()
                if d_id:
                    cur.execute("""
                        INSERT INTO officers (username, passkey, full_name, department_id, role) 
                        VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
                    """, (uname, pwd, fname, d_id[0], role))
            
            # Clean any ghost test data
            cur.execute("DELETE FROM janseva_tickets WHERE id IN ('111', '222', '333')")
        conn.commit()

def analyze_and_route(text):
    client = genai.Client(api_key=GEMINI_API_KEY)
    departments = [
        "Roads & Infrastructure", "Water & Sanitation", "Electricity & Power", 
        "Transport (RTO)", "Revenue & Land", "Food & Civil Supplies", 
        "Police & Law Enforcement", "Public Health", "Urban Development", 
        "Pollution Control", "Fire & Rescue", "Women & Child Development", 
        "Labour Welfare", "Disaster Management", "Telecom & Postal", "Civil"
    ]
    prompt = f"""
    Analyze this civic grievance: "{text}"
    Generate a JSON object:
    - "category": Strictly select the most relevant department from this list: {departments}
    - "severity": "High" | "Medium" | "Low"
    - "summary": 1 concise sentence summarizing the core issue.
    """
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        clean = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception:
        return {"category": "Civil", "severity": "Medium", "summary": text[:80] if text else "Civic issue"}

def save_grievance(chat_id, user_name, raw_text, media_type, media_file_id, lat, lon):
    init_db()
    ai_data = analyze_and_route(raw_text if raw_text else f"{media_type} attached")
    ticket_id = f"GRV-{datetime.now().strftime('%m%d%H%M%S')}"
    
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO janseva_tickets (
                    id, chat_id, user_name, raw_text, media_type, media_file_id, 
                    lat, lon, category, severity, summary, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '1. Pending Review')
            """, (ticket_id, str(chat_id), user_name, raw_text, media_type, media_file_id, 
                  float(lat) if lat else None, float(lon) if lon else None, 
                  ai_data.get("category"), ai_data.get("severity"), ai_data.get("summary")))
        conn.commit()
    return {"ticket_id": ticket_id, **ai_data}

def get_all_complaints():
    init_db()
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM janseva_tickets ORDER BY timestamp DESC")
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in rows]
    except Exception: return []

def execute_admin_sanction(ticket_id, status, budget, contractor, category, office_name, assigned_officer):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE janseva_tickets 
                SET status = %s, budget_allocated = %s, contractor_name = %s,
                    category = %s, office_name = %s, assigned_officer = %s
                WHERE id = %s
            """, (status, budget, contractor, category, office_name, assigned_officer, ticket_id))
        conn.commit()

def execute_field_resolution(ticket_id, spent, materials, media_id):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE janseva_tickets 
                SET status = '6. Resolved (Social Audit)', amount_spent = %s, materials_used = %s, 
                    resolution_media_id = %s, resolved_at = NOW() 
                WHERE id = %s
            """, (spent, materials, media_id, ticket_id))
        conn.commit()