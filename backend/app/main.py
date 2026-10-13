import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .database import engine, Base
from .routers import users, records, consent, audit, clinical, fhir

# Create database tables
Base.metadata.create_all(bind=engine)

# Automatically add missing columns (simple migration for existing db)
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE users DROP COLUMN mfa_secret"))
        conn.commit()
    except Exception:
        conn.rollback()
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN verification_status VARCHAR DEFAULT 'pending'"))
        conn.commit()
    except Exception:
        conn.rollback()
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN license_number VARCHAR"))
        conn.commit()
    except Exception:
        conn.rollback()
    try:
        conn.execute(text("ALTER TABLE medical_records ADD COLUMN doctor_id INTEGER REFERENCES users(id)"))
        conn.commit()
    except Exception:
        conn.rollback()
    try:
        conn.execute(text("ALTER TABLE medical_records ALTER COLUMN doctor_id DROP NOT NULL"))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("MIGRATION ERROR (drop not null):", e)
    try:
        conn.execute(text("ALTER TABLE medical_records ADD COLUMN description VARCHAR"))
        conn.commit()
    except Exception:
        conn.rollback()
    try:
        # Delete any records that failed blockchain verification (tx_hash is NULL) or are corrupted
        conn.execute(text("DELETE FROM medical_records WHERE blockchain_tx_hash IS NULL OR blockchain_tx_hash = '' OR created_at IS NULL OR file_type IS NULL OR file_type = ''"))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("MIGRATION ERROR (cleanup pending records):", e)

import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

import asyncio
from contextlib import asynccontextmanager

async def keep_alive_task():
    while True:
        try:
            # Check Neon
            from sqlalchemy import text
            from .database import SessionLocal
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            
            # Check Supabase
            from .services.storage import storage_service
            storage_service.client.storage.get_bucket("medical-documents")
            
            print("Keep-alive ping successful")
        except Exception as e:
            print(f"Keep-alive ping failed: {e}")
            
        await asyncio.sleep(4 * 60)  # 4 minutes

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(keep_alive_task())
    yield
    task.cancel()

app = FastAPI(
    title="Decentralized Patient Record System API",
    description="API for managing patient records, consent, and blockchain verification",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc), "traceback": traceback.format_exc()},
        headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "true"}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(users.router)
app.include_router(records.router)
app.include_router(consent.router)
app.include_router(audit.router)
app.include_router(clinical.router)
app.include_router(fhir.router)

from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db

@app.get("/health")
def health_check():
    status_neon = False
    status_supabase = False
    
    # Check Neon
    try:
        from sqlalchemy import text
        from .database import SessionLocal
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            status_neon = True
    except Exception:
        pass
        
    # Check Supabase
    try:
        from .services.storage import storage_service
        # Checking the bucket is a good way to see if the project is awake
        storage_service.client.storage.get_bucket("medical-documents")
        status_supabase = True
    except Exception:
        pass

    return {
        "status": "ok" if status_neon and status_supabase else "error",
        "neon_active": status_neon,
        "supabase_active": status_supabase
    }

# Mount the frontend dist folder if it exists
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{catchall:path}")
    def serve_frontend(catchall: str):
        if catchall and os.path.exists(os.path.join(frontend_dist, catchall)):
            return FileResponse(os.path.join(frontend_dist, catchall))
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Decentralized Patient Record System API"}
