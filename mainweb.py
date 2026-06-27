import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import pyodbc

app = FastAPI(
    title="GesturePulse Telemetry Core", 
    description="Enterprise Edge Data Collection Routing Engine linked to MS SQL Server",
    version="2.0.0"
)

# Allow browser frontends to stream live data frames cross-origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQL Server Structured Connection Configuration String
# Points directly to your SQLEXPRESS node using standard native Windows Authentication
SQL_CONNECTION_STRING = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost\\SQLEXPRESS;"
    "Database=GesturePulseDB;"
    "Trusted_Connection=yes;"
)

def insert_telemetry_to_db(session_id: str, client_id: str, location_id: str, gesture: str, score: int, duration: float):
    """Establishes an atomic transaction loop connection pool to log values safely to SQL Server."""
    conn = None
    try:
        conn = pyodbc.connect(SQL_CONNECTION_STRING)
        cursor = conn.cursor()
        
        insert_query = """
            INSERT INTO KioskTelemetry (SessionID, ClientID, LocationID, DetectedGesture, SatisfactionScore, StreakDurationSec)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        
        cursor.execute(insert_query, (session_id, client_id, location_id, gesture, score, duration))
        conn.commit()  # Push the row transaction live to storage blocks
        
    except Exception as db_error:
        print(f"❌ DATABASE INSERTION FAILURE EXCEPTION: {db_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal relational data storage routing loop exception encountered."
        )
    finally:
        if conn:
            conn.close()

class TelemetryPayload(BaseModel):
    client_id: str = Field(..., json_schema_extra={"example": "WEB_AR_KIOSK"})
    location_id: str = Field(..., json_schema_extra={"example": "MAIN_FRONT_EXIT"})
    detected_gesture: str = Field(..., json_schema_extra={"example": "Super Good"})
    satisfaction_score: int = Field(..., ge=1, le=5, json_schema_extra={"example": 5})
    streak_duration_sec: float = Field(..., ge=0.0, json_schema_extra={"example": 3.20})

@app.post("/api/v1/telemetry", status_code=status.HTTP_201_CREATED)
async def log_telemetry(payload: TelemetryPayload):
    # Generate unique operational session tracking IDs for this transaction context
    session_id = str(uuid.uuid4())
    
    # Process transactional insertion to SQL Server
    insert_telemetry_to_db(
        session_id=session_id,
        client_id=payload.client_id,
        location_id=payload.location_id,
        gesture=payload.detected_gesture,
        score=payload.satisfaction_score,
        duration=payload.streak_duration_sec
    )
    
    print("\n" + "="*50)
    print("🚀 DB PERSISTENCE COMMITTED!")
    print(f"Assigned Session : {session_id}")
    print(f"Pose Registered  : {payload.detected_gesture}")
    print(f"Score Ingested   : {payload.satisfaction_score} ⭐")
    print(f"Hold Streak Time : {payload.streak_duration_sec}s")
    print("="*50 + "\n")
    
    return {
        "status": "success", 
        "message": "Telemetry row successfully committed to SQL Server storage engine pipeline.",
        "session_id": session_id
    }

if __name__ == "__main__":
    # Boots server onto local loopback binding port assigned inside index.html configuration variables
    uvicorn.run(app, host="127.0.0.2", port=8000)