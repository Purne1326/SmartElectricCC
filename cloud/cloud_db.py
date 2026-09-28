import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

# SQLAlchemy Base
Base = declarative_base()

class EdgeDevice(Base):
    __tablename__ = "edge_devices"

    device_id = Column(String(50), primary_key=True) # Unique MAC address or machine-id
    name = Column(String(100), nullable=False)
    location = Column(String(100), default="Home")
    registered_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sensor_data = relationship("CloudSensorData", back_populates="device", cascade="all, delete-orphan")
    dht_data = relationship("CloudDhtData", back_populates="device", cascade="all, delete-orphan")
    logs = relationship("CloudLog", back_populates="device", cascade="all, delete-orphan")

class CloudSensorData(Base):
    __tablename__ = "cloud_sensor_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), ForeignKey("edge_devices.device_id", ondelete="CASCADE"), nullable=False)
    appliance_name = Column(String(50), nullable=False)
    current = Column(Float, nullable=False)
    power = Column(Float, nullable=False)
    voltage = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    device = relationship("EdgeDevice", back_populates="sensor_data")

class CloudDhtData(Base):
    __tablename__ = "cloud_dht_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), ForeignKey("edge_devices.device_id", ondelete="CASCADE"), nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    device = relationship("EdgeDevice", back_populates="dht_data")

class CloudLog(Base):
    __tablename__ = "cloud_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), ForeignKey("edge_devices.device_id", ondelete="CASCADE"), nullable=False)
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    device = relationship("EdgeDevice", back_populates="logs")

# Database connection setup
# PostgreSQL URL default: postgresql://postgres:password@localhost:5432/smartelectric_cloud
# We fall back to a local sqlite file for easy testing if no Postgres server is active.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/smartelectric_cloud"
)

# SQLite fallback option for development/testing environments
if not DATABASE_URL.startswith("postgresql"):
    # Allow local SQLite fallback testing
    DATABASE_URL = "sqlite:///smartelectric_cloud.db"

def get_engine():
    """Returns database connection engine."""
    return create_engine(DATABASE_URL, echo=False)

def get_session():
    """Returns a new session context."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_cloud_db():
    """Initializes tables in PostgreSQL/SQLite database."""
    engine = get_engine()
    print(f"Initializing Cloud Database at: {DATABASE_URL}")
    Base.metadata.create_all(engine)
    print("Cloud Database tables initialized successfully.")

if __name__ == "__main__":
    init_cloud_db()
