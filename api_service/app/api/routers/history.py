import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter(prefix="/history", tags=["history"])

def get_db():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "postgres"),
            database=os.getenv("DB_NAME", "fleet_db"),
            user=os.getenv("DB_USER", "fleet_user"),
            password=os.getenv("DB_PASSWORD", "fleet_password")
        )
        return conn
    except Exception as e:
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@router.get("/alerts")
def get_alerts(
    trip_id: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT time as timestamp, trip_id, type, severity, reason FROM alerts"
            params = []
            
            if trip_id:
                query += " WHERE trip_id = %s"
                params.append(trip_id)
                
            query += " ORDER BY time DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, tuple(params))
            results = cur.fetchall()
            return {"data": results}
    finally:
        conn.close()

@router.get("/stats")
def get_stats():
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT type as name, COUNT(*) as value 
                FROM alerts 
                GROUP BY type 
                ORDER BY value DESC
            """)
            results = cur.fetchall()
            return {"data": results}
    finally:
        conn.close()
