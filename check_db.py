import psycopg2
from app.core.config import DB_CONFIG

def check_tables():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Search for tables that might contain 'location' in their name
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name ILIKE '%location%'
    """)
    tables = cur.fetchall()
    print("Found tables:", tables)
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_tables()
