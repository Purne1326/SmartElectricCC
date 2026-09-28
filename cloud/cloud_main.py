import sys
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

# Import SQLAlchemy configs and models
from cloud_db import get_session, EdgeDevice, CloudSensorData, CloudDhtData, CloudLog

app = FastAPI(
    title="SmartElectric Cloud API",
    description="Centralized cloud receiver endpoint for SmartElectric local Edge gateways",
    version="1.0.0"
)

# Enable CORS for remote dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schemas for requests
class RegisterDeviceRequest(BaseModel):
    device_id: str
    name: str
    location: Optional[str] = "Home"

class SensorRecord(BaseModel):
    appliance_name: str
    current: float
    power: float
    voltage: float
    timestamp: str  # ISO string or YYYY-MM-DD HH:MM:SS

class DhtRecord(BaseModel):
    temperature: float
    humidity: float
    timestamp: str

class LogRecord(BaseModel):
    level: str
    message: str
    timestamp: str

class SyncPayloadRequest(BaseModel):
    device_id: str
    sensor_records: List[SensorRecord]
    dht_records: List[DhtRecord]
    log_records: List[LogRecord]

# Dependency to get session
def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "SmartElectric Cloud Sync Receiver",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/cloud/register")
def register_device(req: RegisterDeviceRequest, db: Session = Depends(get_db)):
    """Registers a new Jetson Nano edge device or updates its metadata."""
    device = db.query(EdgeDevice).filter(EdgeDevice.device_id == req.device_id).first()
    
    if not device:
        # Create new device
        device = EdgeDevice(
            device_id=req.device_id,
            name=req.name,
            location=req.location
        )
        db.add(device)
        msg = f"Registered new device: {req.name} ({req.device_id})"
    else:
        # Update existing
        device.name = req.name
        device.location = req.location
        msg = f"Updated device: {req.name} ({req.device_id})"
        
    try:
        db.commit()
        return {"status": "success", "message": msg}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database registration failure: {e}")

@app.post("/api/cloud/sync")
def sync_device_data(payload: SyncPayloadRequest, db: Session = Depends(get_db)):
    """Receives batched historical sensor data, DHT readings, and log events from an edge gateway."""
    device_id = payload.device_id
    
    # 1. Ensure the device is registered. If not, auto-register with default name
    device = db.query(EdgeDevice).filter(EdgeDevice.device_id == device_id).first()
    if not device:
        device = EdgeDevice(
            device_id=device_id,
            name=f"Auto-Registered Edge ({device_id[:6]})",
            location="Unknown"
        )
        db.add(device)
        db.flush()

    sensor_inserts = 0
    dht_inserts = 0
    log_inserts = 0

    try:
        # 2. Process and insert sensor telemetry records
        for rec in payload.sensor_records:
            try:
                dt = datetime.fromisoformat(rec.timestamp.replace("Z", "+00:00"))
            except ValueError:
                dt = datetime.strptime(rec.timestamp, '%Y-%m-%d %H:%M:%S')

            sensor_data = CloudSensorData(
                device_id=device_id,
                appliance_name=rec.appliance_name,
                current=rec.current,
                power=rec.power,
                voltage=rec.voltage,
                timestamp=dt
            )
            db.add(sensor_data)
            sensor_inserts += 1

        # 3. Process and insert DHT telemetry records
        for rec in payload.dht_records:
            try:
                dt = datetime.fromisoformat(rec.timestamp.replace("Z", "+00:00"))
            except ValueError:
                dt = datetime.strptime(rec.timestamp, '%Y-%m-%d %H:%M:%S')

            dht_data = CloudDhtData(
                device_id=device_id,
                temperature=rec.temperature,
                humidity=rec.humidity,
                timestamp=dt
            )
            db.add(dht_data)
            dht_inserts += 1

        # 4. Process and insert log records
        for rec in payload.log_records:
            try:
                dt = datetime.fromisoformat(rec.timestamp.replace("Z", "+00:00"))
            except ValueError:
                dt = datetime.strptime(rec.timestamp, '%Y-%m-%d %H:%M:%S')

            log_data = CloudLog(
                device_id=device_id,
                level=rec.level,
                message=rec.message,
                timestamp=dt
            )
            db.add(log_data)
            log_inserts += 1

        # Commit all inserts inside a single database transaction
        db.commit()
        return {
            "status": "success",
            "device_id": device_id,
            "records_synced": {
                "sensors": sensor_inserts,
                "dht": dht_inserts,
                "logs": log_inserts
            }
        }

    except Exception as e:
        db.rollback()
        print(f"Cloud Sync failed: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Database synchronization error: {e}")

@app.get("/api/cloud/devices")
def get_devices(db: Session = Depends(get_db)):
    """Retrieves all registered devices and counts of their stored telemetry records."""
    devices = db.query(EdgeDevice).all()
    results = []
    
    for d in devices:
        sensor_count = db.query(CloudSensorData).filter(CloudSensorData.device_id == d.device_id).count()
        dht_count = db.query(CloudDhtData).filter(CloudDhtData.device_id == d.device_id).count()
        log_count = db.query(CloudLog).filter(CloudLog.device_id == d.device_id).count()
        
        # Determine last sync timestamp
        last_sensor = db.query(CloudSensorData.timestamp).filter(CloudSensorData.device_id == d.device_id).order_by(CloudSensorData.timestamp.desc()).first()
        last_sync = last_sensor[0].isoformat() if last_sensor else None

        results.append({
            "device_id": d.device_id,
            "name": d.name,
            "location": d.location,
            "registered_at": d.registered_at.isoformat(),
            "telemetry_counts": {
                "sensors": sensor_count,
                "dht": dht_count,
                "logs": log_count
            },
            "last_sync": last_sync
        })
        
    return results

@app.get("/api/cloud/telemetry")
def get_telemetry(
    device_id: str,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """Retrieves combined telemetry history for a specific registered device."""
    sensors = db.query(CloudSensorData).filter(CloudSensorData.device_id == device_id).order_by(CloudSensorData.timestamp.desc()).limit(limit).all()
    dht = db.query(CloudDhtData).filter(CloudDhtData.device_id == device_id).order_by(CloudDhtData.timestamp.desc()).limit(limit).all()
    logs = db.query(CloudLog).filter(CloudLog.device_id == device_id).order_by(CloudLog.timestamp.desc()).limit(50).all()

    return {
        "device_id": device_id,
        "sensor_data": [
            {
                "appliance_name": s.appliance_name,
                "current": s.current,
                "power": s.power,
                "voltage": s.voltage,
                "timestamp": s.timestamp.isoformat()
            } for s in sensors
        ],
        "dht_data": [
            {
                "temperature": d.temperature,
                "humidity": d.humidity,
                "timestamp": d.timestamp.isoformat()
            } for d in dht
        ],
        "logs": [
            {
                "level": l.level,
                "message": l.message,
                "timestamp": l.timestamp.isoformat()
            } for l in logs
        ]
    }
