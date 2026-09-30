import os
import random
import string
from typing import Optional, List
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))

app = FastAPI(
    title="TravelVista API",
    description="Backend API connected to Neon PostgreSQL for TravelVista booking holds, travel enquiries, newsletter subscribers, and catalog data.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for cross-origin requests if accessed from different ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    """Create a new database connection with dictionary cursor."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def generate_booking_ref() -> str:
    """Generate unambiguous alphanumeric booking reference like TV-7X9KW."""
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    code = "".join(random.choice(chars) for _ in range(5))
    return f"TV-{code}"

# Pydantic Request Models
class BookingRequest(BaseModel):
    tripName: str = Field(..., min_length=2, description="Name of the trip or package")
    tripPrice: Optional[str] = Field(None, description="Starting or quoted price")
    customerName: str = Field(..., min_length=2, description="Full name of traveller")
    customerEmail: str = Field(..., description="Email address for itinerary and confirmation")
    customerPhone: Optional[str] = Field(None, description="Contact phone number")
    departureDate: str = Field(..., description="Target departure date (YYYY-MM-DD)")
    travelersCount: Optional[int] = Field(1, ge=1, le=50, description="Number of seats to hold")
    specialNotes: Optional[str] = Field(None, description="Dietary or accessibility notes")

class EnquiryRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Full name")
    phone: str = Field(..., min_length=6, description="Contact phone")
    email: str = Field(..., description="Email address")
    destinationInterest: Optional[str] = Field(None, description="Selected destination or custom route")
    travelMonth: Optional[str] = Field(None, description="Planned departure window")
    message: str = Field(..., min_length=10, description="Enquiry details")

class NewsletterRequest(BaseModel):
    email: str = Field(..., description="Subscriber email address")

# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.get("/api/health", summary="Health check and DB status")
def health_check():
    """Verify backend status and Neon PostgreSQL database connectivity."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            ver = cur.fetchone()["version"]

            cur.execute("SELECT COUNT(*) AS count FROM bookings;")
            bookings_count = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM enquiries;")
            enquiries_count = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM newsletter_subscribers;")
            subscribers_count = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) AS count FROM destinations;")
            destinations_count = cur.fetchone()["count"]

        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "neon_connected": True,
            "neon_db_version": ver,
            "db_version": ver,
            "counts": {
                "bookings": bookings_count,
                "enquiries": enquiries_count,
                "newsletter_subscribers": subscribers_count,
                "destinations": destinations_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}"
        )

@app.post("/api/bookings", status_code=status.HTTP_201_CREATED, summary="Create a new booking seat hold")
def create_booking(booking: BookingRequest):
    """Store booking request in Neon DB and return hold confirmation."""
    booking_ref = generate_booking_ref()

    try:
        # Validate date is strictly future
        dep_date = datetime.strptime(booking.departureDate, "%Y-%m-%d").date()
        if dep_date <= date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Departure date must be in the future."
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Expected YYYY-MM-DD."
        )

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bookings (
                    booking_ref, trip_name, trip_price, customer_name,
                    customer_email, customer_phone, departure_date,
                    travelers_count, special_notes, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'HELD_48H')
                RETURNING id, booking_ref, trip_name, customer_name, customer_email, departure_date, created_at;
                """,
                (
                    booking_ref,
                    booking.tripName,
                    booking.tripPrice,
                    booking.customerName.strip(),
                    booking.customerEmail.strip().lower(),
                    booking.customerPhone.strip() if booking.customerPhone else None,
                    dep_date,
                    booking.travelersCount,
                    booking.specialNotes.strip() if booking.specialNotes else None
                )
            )
            saved = cur.fetchone()
            conn.commit()
        conn.close()

        return {
            "success": True,
            "bookingRef": saved["booking_ref"],
            "tripName": saved["trip_name"],
            "customerName": saved["customer_name"],
            "customerEmail": saved["customer_email"],
            "holdHours": 48,
            "message": f"Seats held for 48 hours. Itinerary and payment link dispatched to {saved['customer_email']}."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record booking: {str(e)}"
        )

@app.get("/api/bookings", summary="List recent booking holds")
def list_bookings(limit: int = 50):
    """Retrieve recent booking holds stored in Neon DB."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, booking_ref, trip_name, trip_price, customer_name, customer_email, departure_date, travelers_count, status, created_at FROM bookings ORDER BY id DESC LIMIT %s;",
                (limit,)
            )
            rows = cur.fetchall()
        conn.close()
        return {"bookings": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/enquiries", status_code=status.HTTP_201_CREATED, summary="Submit a custom trip enquiry")
def create_enquiry(enquiry: EnquiryRequest):
    """Store contact/custom trip enquiry in Neon DB."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO enquiries (name, phone, email, destination_interest, travel_month, message, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'NEW')
                RETURNING id, name, email, created_at;
                """,
                (
                    enquiry.name.strip(),
                    enquiry.phone.strip(),
                    enquiry.email.strip().lower(),
                    enquiry.destinationInterest.strip() if enquiry.destinationInterest else None,
                    enquiry.travelMonth.strip() if enquiry.travelMonth else None,
                    enquiry.message.strip()
                )
            )
            saved = cur.fetchone()
            conn.commit()
        conn.close()

        return {
            "success": True,
            "enquiryId": saved["id"],
            "message": "Thank you. Our senior expedition designer will connect with you within 24 business hours."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit enquiry: {str(e)}")

@app.get("/api/enquiries", summary="List recent enquiries")
def list_enquiries(limit: int = 50):
    """Retrieve recent enquiries stored in Neon DB."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, phone, email, destination_interest, travel_month, message, status, created_at FROM enquiries ORDER BY id DESC LIMIT %s;",
                (limit,)
            )
            rows = cur.fetchall()
        conn.close()
        return {"enquiries": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/newsletter", status_code=status.HTTP_201_CREATED, summary="Subscribe to newsletter")
def subscribe_newsletter(sub: NewsletterRequest):
    """Store newsletter subscriber email in Neon DB."""
    clean_email = sub.email.strip().lower()
    if "@" not in clean_email or "." not in clean_email:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO newsletter_subscribers (email)
                VALUES (%s)
                ON CONFLICT (email) DO NOTHING
                RETURNING id, email, subscribed_at;
                """,
                (clean_email,)
            )
            row = cur.fetchone()
            conn.commit()
        conn.close()

        return {
            "success": True,
            "email": clean_email,
            "message": "You have been successfully subscribed to the TravelVista Dispatch."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to subscribe: {str(e)}")

@app.get("/api/subscribers", summary="List newsletter subscribers")
def list_subscribers(limit: int = 100):
    """Retrieve newsletter subscribers from Neon DB for Admin Panel."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, subscribed_at FROM newsletter_subscribers ORDER BY id DESC LIMIT %s;",
                (limit,)
            )
            rows = cur.fetchall()
        conn.close()
        return {"subscribers": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/bookings/{booking_id}", summary="Delete a booking hold")
def delete_booking(booking_id: int):
    """Delete a booking hold record from Neon DB."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bookings WHERE id = %s RETURNING id, booking_ref;", (booking_id,))
            deleted = cur.fetchone()
            conn.commit()
        conn.close()
        if not deleted:
            raise HTTPException(status_code=404, detail="Booking not found.")
        return {"success": True, "message": f"Booking {deleted['booking_ref']} deleted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/destinations", summary="Get destinations catalog from Neon DB")
def get_destinations():
    """Retrieve destinations seeded in Neon DB."""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, country, price, duration, rating, category, tags, image_url FROM destinations ORDER BY id ASC;"
            )
            rows = cur.fetchall()
        conn.close()
        return {"destinations": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# STATIC FILE SERVING (FRONTEND)
# ==========================================
TRAVEL_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/", include_in_schema=False)
def serve_root():
    """Serve index.html at root."""
    return FileResponse(os.path.join(TRAVEL_DIR, "index.html"))

# Mount directory to serve all static assets, images, etc.
app.mount("/", StaticFiles(directory=TRAVEL_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print(f"Starting TravelVista full-stack server on http://{HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
