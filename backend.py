import os
import json
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from datetime import datetime
from google import genai
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

try:
    db_pool = pool.ThreadedConnectionPool(1, 10, DATABASE_URL)
except (Exception, psycopg2.DatabaseError) as error:
    print("Error while connecting to PostgreSQL", error)
    db_pool = None

@contextmanager
def get_db_connection():
    if db_pool is None:
        raise Exception("Database connection pool is not initialized. Check DATABASE_URL.")
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)

def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS departments (
                        id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, tier TEXT NOT NULL CHECK (tier IN ('State', 'District', 'Local')), parent_id INTEGER REFERENCES departments(id)
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS officers (
                        id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, passkey TEXT NOT NULL, full_name TEXT NOT NULL, department_id INTEGER REFERENCES departments(id), role TEXT NOT NULL CHECK (role IN ('admin', 'field'))
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id TEXT PRIMARY KEY, timestamp TIMESTAMPTZ DEFAULT NOW(), chat_id TEXT, user_name TEXT, raw_text TEXT, media_type TEXT, media_file_id TEXT, lat DOUBLE PRECISION, lon DOUBLE PRECISION, category TEXT, severity TEXT, summary TEXT, status TEXT DEFAULT '1. Pending Review', assigned_department_id INTEGER REFERENCES departments(id), assigned_officer_id INTEGER REFERENCES officers(id)
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS budget_ledgers (
                        id SERIAL PRIMARY KEY, ticket_id TEXT REFERENCES tickets(id) ON DELETE CASCADE, budget_allocated NUMERIC DEFAULT 0, amount_spent NUMERIC DEFAULT 0, contractor_name TEXT, materials_used TEXT, resolution_media_id TEXT, audit_hash TEXT, updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)

                cur.execute("SELECT count(*) FROM departments")
                if cur.fetchone()[0] == 0:
                    departments = [('Govt of India', 'State', None), ('Roads', 'Local', 1), ('Water', 'Local', 1), ('Electricity', 'Local', 1), ('Sanitation', 'Local', 1), ('Cyber Crime', 'Local', 1), ('Civil', 'Local', 1)]
                    cur.executemany("INSERT INTO departments (name, tier, parent_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", departments)
                
                cur.execute("SELECT count(*) FROM officers")
                if cur.fetchone()[0] == 0:
                    officers = [('collector', 'ias@india2026', 'District Collector', 1, 'admin'), ('pwd_roads', 'pwd@infra2026', 'Er. Rajesh Varma', 2, 'field'), ('water_board', 'jal@clean2026', 'Er. K. Ramesh', 3, 'field'), ('electricity', 'power@grid2026', 'Er. M. Praveen', 4, 'field'), ('sanitation', 'swm@clean2026', 'Dr. A. Rao', 5, 'field'), ('cyber_cop', 'cyber@cell2026', 'Inspector S. Reddy', 6, 'field')]
                    cur.executemany("INSERT INTO officers (username, passkey, full_name, department_id, role) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING", officers)
                
                # BUG FIX: Historical Data Restoration for Sept 13/14 Tickets
                cur.execute("SELECT count(*) FROM tickets WHERE id = 'GRV-0913124104'")
                if cur.fetchone()[0] == 0:
                    cur.execute("""
                        INSERT INTO tickets (id, chat_id, user_name, raw_text, lat, lon, category, severity, status, assigned_department_id) 
                        VALUES 
                        ('GRV-0913124104', '0', 'Citizen', 'Leaking drainage water', 17.350, 78.530, 'Sanitation', 'High', '2. Survey & Estimation', 5),
                        ('GRV-0913123149', '0', 'Citizen', 'traffic break', 17.340, 78.520, 'Roads', 'Medium', '6. Resolved (Social Audit)', 2),
                        ('GRV-0913122402', '0', 'Citizen', 'pothole', 17.345, 78.525, 'Roads', 'Low', '1. Pending Review', 2)
                        ON CONFLICT DO NOTHING
                    """)
                    cur.execute("""
                        INSERT INTO budget_ledgers (ticket_id, budget_allocated, amount_spent)
                        VALUES 
                        ('GRV-0913124104', 50000, 0),
                        ('GRV-0913123149', 0, 0),
                        ('GRV-0913122402', 0, 0)
                        ON CONFLICT DO NOTHING
                    """)
            conn.commit()
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
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM departments WHERE name = %s", (ai_data.get("category"),))
            dept_row = cur.fetchone()
            dept_id = dept_row[0] if dept_row else None
            
            officer_id = None
            if dept_id:
                cur.execute("SELECT id FROM officers WHERE department_id = %s LIMIT 1", (dept_id,))
                off_row = cur.fetchone()
                officer_id = off_row[0] if off_row else None
            
            cur.execute("""
                INSERT INTO tickets (id, chat_id, user_name, raw_text, media_type, media_file_id, lat, lon, category, severity, summary, status, assigned_department_id, assigned_officer_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '1. Pending Review', %s, %s)
            """, (ticket_id, str(chat_id), user_name, raw_text, media_type, media_file_id, lat, lon, ai_data.get("category"), ai_data.get("severity"), ai_data.get("summary"), dept_id, officer_id))
            
            cur.execute("INSERT INTO budget_ledgers (ticket_id) VALUES (%s)", (ticket_id,))
            
            cur.execute("SELECT name FROM departments WHERE id = %s", (dept_id,))
            d_res = cur.fetchone()
            dept_name = d_res[0] if d_res else "Pending Assignment"
            
            cur.execute("SELECT full_name FROM officers WHERE id = %s", (officer_id,))
            o_res = cur.fetchone()
            officer_name = o_res[0] if o_res else "Awaiting Nodal Officer"
            
        conn.commit()
    return {"ticket_id": ticket_id, "office_name": dept_name, "assigned_officer": officer_name, **ai_data}

def get_all_complaints():
    init_db()
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT t.id, t.timestamp, t.chat_id, t.user_name, t.raw_text, t.media_type, t.media_file_id, t.lat, t.lon, t.category, t.severity, t.summary, t.status, d.name AS office_name, o.full_name AS assigned_officer, bl.budget_allocated, bl.amount_spent, bl.contractor_name, bl.materials_used, bl.resolution_media_id, bl.updated_at AS resolved_at, bl.audit_hash
                    FROM tickets t
                    LEFT JOIN departments d ON t.assigned_department_id = d.id
                    LEFT JOIN officers o ON t.assigned_officer_id = o.id
                    LEFT JOIN budget_ledgers bl ON t.id = bl.ticket_id
                    ORDER BY t.timestamp DESC
                """)
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        print(f"Error fetching complaints: {e}")
        return []

def execute_admin_sanction(ticket_id, status, budget, contractor, category, office_name, assigned_officer):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM departments WHERE name = %s", (category,))
            dept_row = cur.fetchone()
            dept_id = dept_row[0] if dept_row else None
            officer_id = None
            if dept_id:
                cur.execute("SELECT id FROM officers WHERE full_name = %s", (assigned_officer,))
                off_row = cur.fetchone()
                if off_row: officer_id = off_row[0]
                else:
                    cur.execute("SELECT id FROM officers WHERE department_id = %s LIMIT 1", (dept_id,))
                    fallback = cur.fetchone()
                    officer_id = fallback[0] if fallback else None

            cur.execute("UPDATE tickets SET status = %s, category = %s, assigned_department_id = %s, assigned_officer_id = %s WHERE id = %s", (status, category, dept_id, officer_id, ticket_id))
            cur.execute("UPDATE budget_ledgers SET budget_allocated = %s, contractor_name = %s, updated_at = NOW() WHERE ticket_id = %s", (budget, contractor, ticket_id))
        conn.commit()

def execute_field_resolution(ticket_id, spent, materials, media_id):
    import hashlib
    raw_str = f"GOI_DPI_{ticket_id}_{spent}_VERIFIED"
    audit_hash = hashlib.sha256(raw_str.encode()).hexdigest()[:16].upper()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE tickets SET status = '6. Resolved (Social Audit)' WHERE id = %s", (ticket_id,))
            cur.execute("UPDATE budget_ledgers SET amount_spent = %s, materials_used = %s, resolution_media_id = %s, audit_hash = %s, updated_at = NOW() WHERE ticket_id = %s", (spent, materials, media_id, audit_hash, ticket_id))
        conn.commit()