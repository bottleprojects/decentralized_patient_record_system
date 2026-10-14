import os
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .database import engine, Base
from .routers import users, records, consent, audit, clinical, fhir, metrics

# Create database tables
Base.metadata.create_all(bind=engine)

# Automatically add missing columns (simple migration for existing db)
from sqlalchemy import text
is_postgres = engine.dialect.name == "postgresql"
with engine.connect() as conn:
    if is_postgres:
        pg_migrations = [
            "ALTER TABLE users DROP COLUMN IF EXISTS mfa_secret",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_status VARCHAR DEFAULT 'pending'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS license_number VARCHAR",
            "ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS doctor_id INTEGER REFERENCES users(id)",
            "ALTER TABLE medical_records ALTER COLUMN doctor_id DROP NOT NULL",
            "ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS description VARCHAR",
            "ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS ipfs_cid VARCHAR",
            "ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS ipfs_file_name VARCHAR",
            "ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS ipfs_file_size INTEGER",
            "ALTER TABLE medical_records ADD COLUMN IF NOT EXISTS blockchain_status VARCHAR DEFAULT 'confirmed'",
            "ALTER TABLE medical_records ALTER COLUMN supabase_file_path DROP NOT NULL",
            "ALTER TABLE medical_records ALTER COLUMN record_hash DROP NOT NULL",
            "DELETE FROM medical_records WHERE blockchain_tx_hash IS NULL OR blockchain_tx_hash = '' OR created_at IS NULL OR file_type IS NULL OR file_type = ''",
        ]
        for stmt in pg_migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()
    else:
        # SQLite compatible migrations
        sqlite_migrations = [
            "ALTER TABLE users ADD COLUMN verification_status VARCHAR DEFAULT 'pending'",
            "ALTER TABLE users ADD COLUMN license_number VARCHAR",
            "ALTER TABLE medical_records ADD COLUMN doctor_id INTEGER",
            "ALTER TABLE medical_records ADD COLUMN description VARCHAR",
            "ALTER TABLE medical_records ADD COLUMN ipfs_cid VARCHAR",
            "ALTER TABLE medical_records ADD COLUMN ipfs_file_name VARCHAR",
            "ALTER TABLE medical_records ADD COLUMN ipfs_file_size INTEGER",
            "ALTER TABLE medical_records ADD COLUMN blockchain_status VARCHAR DEFAULT 'confirmed'",
            "DELETE FROM medical_records WHERE blockchain_tx_hash IS NULL OR blockchain_tx_hash = '' OR created_at IS NULL OR file_type IS NULL OR file_type = ''",
        ]
        for stmt in sqlite_migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                conn.rollback()

import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

import asyncio
from contextlib import asynccontextmanager

async def keep_alive_task():
    while True:
        try:
            # Check Database
            from sqlalchemy import text
            from .database import SessionLocal
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            
            print("Keep-alive ping successful")
        except Exception as e:
            print(f"Keep-alive ping failed: {e}")
            
        await asyncio.sleep(4 * 60)  # 4 minutes

def bootstrap_admin_user():
    admin_email = os.getenv("ADMIN_EMAIL", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not admin_email or not admin_password:
        return

    from .database import SessionLocal
    from .models import User, RoleEnum
    from .services.auth import get_password_hash

    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                full_name="System Administrator",
                role=RoleEnum.admin,
                verification_status="verified",
            )
            db.add(admin_user)
            db.commit()
            print(f"INFO [Bootstrap]: Created admin user '{admin_email}'.")
        else:
            print(f"INFO [Bootstrap]: Admin user '{admin_email}' already exists.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_admin_user()
    task = asyncio.create_task(keep_alive_task())
    yield
    task.cancel()

app = FastAPI(
    title="Decentralized Patient Record System API",
    description="API for managing patient records, consent, and blockchain verification",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()

if ENVIRONMENT == "production":
    if not FRONTEND_URL or FRONTEND_URL == "*":
        raise RuntimeError(
            "FATAL: In production, FRONTEND_URL must be set to the allowed frontend origin(s) "
            "(e.g. 'https://my-app.vercel.app') and wildcard '*' is not allowed."
        )
    allowed_origins = [o.strip() for o in FRONTEND_URL.split(",") if o.strip()]
else:
    if FRONTEND_URL and FRONTEND_URL != "*":
        allowed_origins = [o.strip() for o in FRONTEND_URL.split(",") if o.strip()]
    else:
        allowed_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin")
    headers = {}
    if origin and (allowed_origins == ["*"] or origin in allowed_origins):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc), "traceback": traceback.format_exc()},
        headers=headers
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Integrity-Verified", "X-IPFS-CID", "X-Record-Hash"],
)

app.include_router(users.router)
app.include_router(records.router)
app.include_router(consent.router)
app.include_router(audit.router)
app.include_router(clinical.router)
app.include_router(fhir.router)
app.include_router(metrics.router)

from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db

@app.get("/health")
def health_check(response: Response):
    db_healthy = False
    db_detail = "disconnected"
    try:
        from sqlalchemy import text
        from .database import SessionLocal
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_healthy = True
            db_detail = "connected"
    except Exception as e:
        db_detail = f"Database connection error: {str(e)}"

    from .services.ipfs import ipfs_service
    pinata_status = ipfs_service.check_health()

    if not db_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if (db_healthy and pinata_status.get("authenticated")) else ("degraded" if db_healthy else "unhealthy"),
        "database": {
            "connected": db_healthy,
            "detail": db_detail,
        },
        "pinata": pinata_status,
        "database_active": db_healthy,
        "ipfs_active": pinata_status.get("authenticated", False),
    }

# Mount the frontend dist folder if it exists
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{catchall:path}")
    def serve_frontend(catchall: str):
        file_path = os.path.join(frontend_dist, catchall)
        if catchall and os.path.isfile(file_path):
            return FileResponse(file_path)
        # If requesting a specific file/asset with an extension that does not exist, return 404
        if "." in os.path.basename(catchall):
            return JSONResponse(status_code=404, content={"detail": f"Asset '{catchall}' not found"})
        # Otherwise serve SPA entry point index.html
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return JSONResponse(status_code=404, content={"detail": "Frontend index.html not found"})
else:
    @app.get("/")
    def read_root():
        return {"message": "Welcome to the Decentralized Patient Record System API"}
