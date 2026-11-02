import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment variables
os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = "sqlite:///./test_records.db"
os.environ["ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=" # 32-byte test key
os.environ["SIMULATE_BLOCKCHAIN"] = "true"
os.environ["JWT_SECRET_KEY"] = "test_super_secret_jwt_key_2026_antigravity"

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import User, RoleEnum, Consent, Device
from backend.app.services.auth import get_password_hash, create_access_token

TEST_DB_URL = "sqlite:///./test_records.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_records.db"):
        try:
            os.remove("./test_records.db")
        except OSError:
            pass

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_users(db_session):
    # Patient A
    p_a = User(
        email="patient_a@vit.edu",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Patient Alpha",
        role=RoleEnum.patient,
        verification_status="verified",
    )
    # Patient B
    p_b = User(
        email="patient_b@vit.edu",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Patient Beta",
        role=RoleEnum.patient,
        verification_status="verified",
    )
    # Doctor A (Verified)
    d_a = User(
        email="doctor_a@vit.edu",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Dr. Alice Smith",
        role=RoleEnum.doctor,
        license_number="DOC-IND-9912",
        verification_status="verified",
    )
    # Doctor B (Unverified)
    d_b = User(
        email="doctor_b@vit.edu",
        hashed_password=get_password_hash("Pass123!"),
        full_name="Dr. Bob Unverified",
        role=RoleEnum.doctor,
        license_number="DOC-IND-4421",
        verification_status="pending",
    )
    db_session.add_all([p_a, p_b, d_a, d_b])
    db_session.commit()
    db_session.refresh(p_a)
    db_session.refresh(p_b)
    db_session.refresh(d_a)
    db_session.refresh(d_b)

    # Pre-register device for Patient A
    dev_a = Device(
        device_id="ESP32-PATIENT-A",
        patient_id=p_a.id,
        device_status="active",
        device_model="ESP32-VITALS-01",
        firmware_version="1.2.0",
        secret_key_hash="test_secret_hash",
    )
    # Pre-register device for Patient B
    dev_b = Device(
        device_id="ESP32-PATIENT-B",
        patient_id=p_b.id,
        device_status="active",
        device_model="ESP32-VITALS-01",
        firmware_version="1.2.0",
        secret_key_hash="test_secret_hash",
    )
    db_session.add_all([dev_a, dev_b])
    db_session.commit()

    return {
        "patient_a": p_a,
        "patient_b": p_b,
        "doctor_a": d_a,
        "doctor_b": d_b,
        "token_p_a": create_access_token({"sub": p_a.email, "role": p_a.role.value}),
        "token_p_b": create_access_token({"sub": p_b.email, "role": p_b.role.value}),
        "token_d_a": create_access_token({"sub": d_a.email, "role": d_a.role.value}),
        "token_d_b": create_access_token({"sub": d_b.email, "role": d_b.role.value}),
    }

