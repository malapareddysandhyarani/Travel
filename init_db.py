import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in environment or .env file.")
    sys.exit(1)

SCHEMA_SQL = """
-- 1. Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    booking_ref VARCHAR(20) UNIQUE NOT NULL,
    trip_name VARCHAR(255) NOT NULL,
    trip_price VARCHAR(100),
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(50),
    departure_date DATE NOT NULL,
    travelers_count INTEGER DEFAULT 1,
    special_notes TEXT,
    status VARCHAR(50) DEFAULT 'HELD_48H',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bookings_ref ON bookings(booking_ref);
CREATE INDEX IF NOT EXISTS idx_bookings_email ON bookings(customer_email);

-- 2. Enquiries Table (Contact Form)
CREATE TABLE IF NOT EXISTS enquiries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    destination_interest VARCHAR(255),
    travel_month VARCHAR(100),
    message TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'NEW',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_enquiries_email ON enquiries(email);

-- 3. Newsletter Subscribers Table
CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    subscribed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Destinations Catalogue Table
CREATE TABLE IF NOT EXISTS destinations (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    price INTEGER NOT NULL,
    duration VARCHAR(50) NOT NULL,
    rating NUMERIC(3,1) NOT NULL,
    category VARCHAR(100) NOT NULL,
    tags TEXT[] NOT NULL,
    image_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

DESTINATIONS_DATA = [
    ('ladakh', 'Ladakh High Passes', 'India', 38500, '7 Days', 4.9, 'Mountains', ['High Altitude', 'Monasteries'], 'https://images.unsplash.com/photo-1581793745862-99fde7fa73d2?auto=format&fit=crop&w=800&q=80'),
    ('kyoto', 'Ancient Kyoto & Arashiyama', 'Japan', 124000, '8 Days', 4.9, 'Cultural', ['Temples', 'Gardens', 'Tea'], 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=800&q=80'),
    ('amalfi', 'Amalfi Coast & Positano', 'Italy', 168000, '6 Days', 4.8, 'Beaches', ['Cliffside', 'Wine', 'Sea'], 'https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&w=800&q=80'),
    ('serengeti', 'Serengeti & Ngorongoro', 'Tanzania', 215000, '9 Days', 4.9, 'Wildlife', ['Big Five', 'Migration', 'Camp'], 'https://images.unsplash.com/photo-1516426122078-c23e76319801?auto=format&fit=crop&w=800&q=80'),
    ('tromso', 'Tromsø & Aurora Fjords', 'Norway', 185000, '5 Days', 4.7, 'Mountains', ['Northern Lights', 'Fjords'], 'https://images.unsplash.com/photo-1517411032315-54ef2cb783bb?auto=format&fit=crop&w=800&q=80'),
    ('rajasthan', 'Royal Forts of Mewar', 'India', 42000, '7 Days', 4.8, 'Cultural', ['Palaces', 'Haveli', 'Art'], 'https://images.unsplash.com/photo-1599661046289-e31897846e41?auto=format&fit=crop&w=800&q=80'),
    ('bali', 'Ubud & Nusa Coastlines', 'Indonesia', 68000, '7 Days', 4.8, 'Beaches', ['Rice Terraces', 'Reefs'], 'https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=800&q=80'),
    ('wadirum', 'Wadi Rum Desert Marshes', 'Jordan', 95000, '6 Days', 4.9, 'Desert', ['Red Sand', 'Bedouin', 'Stars'], 'https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=800&q=80'),
    ('queenstown', 'Southern Alps Traverse', 'New Zealand', 198000, '8 Days', 4.9, 'Mountains', ['Glacial Lakes', 'Treks'], 'https://images.unsplash.com/photo-1507699622108-4be3abd695ad?auto=format&fit=crop&w=800&q=80'),
    ('kerala', 'Kerala Backwaters & Rainforest', 'India', 32000, '5 Days', 4.8, 'Cultural', ['Houseboats', 'Ayurveda'], 'https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?auto=format&fit=crop&w=800&q=80'),
    ('banff', 'Banff & Lake Louise', 'Canada', 175000, '7 Days', 4.8, 'Mountains', ['Rockies', 'Glacier Trails'], 'https://images.unsplash.com/photo-1503614472-8c93d56e92ce?auto=format&fit=crop&w=800&q=80'),
    ('samui', 'Koh Samui Secret Coves', 'Thailand', 54000, '6 Days', 4.7, 'Beaches', ['Island Hopping', 'Coral'], 'https://images.unsplash.com/photo-1537956965359-7573183d1f57?auto=format&fit=crop&w=800&q=80')
]

def init_database():
    print(f"Connecting to Neon PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("Creating tables in Neon DB...")
    cur.execute(SCHEMA_SQL)
    print("[OK] Schema created successfully.")

    print("Seeding destinations...")
    insert_sql = """
    INSERT INTO destinations (id, name, country, price, duration, rating, category, tags, image_url)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        name = EXCLUDED.name,
        country = EXCLUDED.country,
        price = EXCLUDED.price,
        duration = EXCLUDED.duration,
        rating = EXCLUDED.rating,
        category = EXCLUDED.category,
        tags = EXCLUDED.tags,
        image_url = EXCLUDED.image_url;
    """
    for dest in DESTINATIONS_DATA:
        cur.execute(insert_sql, dest)
    print(f"[OK] Seeded {len(DESTINATIONS_DATA)} destinations.")

    # Verification query
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    tables = [row[0] for row in cur.fetchall()]
    print("Live public tables in Neon DB:", tables)

    cur.close()
    conn.close()
    print("Database initialization complete!")

if __name__ == "__main__":
    init_database()
