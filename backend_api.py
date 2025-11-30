"""
Backend API - Reads flight data files
Called by n8n workflows for file operations
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path
from datetime import datetime, timedelta

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DATA_DIR = Path(__file__).parent / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
ALERTS_DIR = DATA_DIR / "alerts"

@app.get("/api/snapshot")
def get_snapshot(region_name: str = "USA_East_Coast"):
    """Get latest snapshot"""
    files = list(SNAPSHOT_DIR.glob(f"{region_name}_*.json"))
    if not files:
        return {"success": False, "error": f"No data for {region_name}", "flights": []}
    
    latest = max(files, key=lambda f: f.stat().st_mtime)
    data = json.loads(latest.read_text())
    
    flights = []
    if "data" in data and "states" in data["data"]:
        for s in data["data"]["states"]:
            if len(s) >= 12:
                flights.append({"icao24": s[0], "callsign": s[1].strip() if s[1] else None, "origin_country": s[2], 
                               "longitude": s[5], "latitude": s[6], "altitude": s[7], "on_ground": s[8],
                               "velocity": s[9], "heading": s[10], "vertical_rate": s[11]})
    
    return {"success": True, "region": region_name, "timestamp": data.get("timestamp"), 
            "total_flights": len(flights), "flights": flights}

@app.get("/api/flight")
def get_flight(callsign: str):
    """Find flight by callsign"""
    callsign = callsign.strip().upper()
    for file in sorted(SNAPSHOT_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]:
        data = json.loads(file.read_text())
        if "data" in data and "states" in data["data"]:
            for s in data["data"]["states"]:
                if len(s) >= 12:
                    cs = s[1].strip().upper() if s[1] else ""
                    if cs == callsign or s[0].upper() == callsign:
                        return {"success": True, "flight": {"icao24": s[0], "callsign": s[1].strip() if s[1] else None,
                                "origin_country": s[2], "longitude": s[5], "latitude": s[6], "altitude": s[7],
                                "on_ground": s[8], "velocity": s[9], "heading": s[10], "vertical_rate": s[11]}}
    return {"success": False, "error": f"Flight {callsign} not found"}

@app.get("/api/alerts")
def get_alerts(max_age_hours: int = 24):
    """Get active alerts"""
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    alerts = [json.loads(f.read_text()) for f in ALERTS_DIR.glob("*.json") 
              if datetime.fromtimestamp(f.stat().st_mtime) >= cutoff]
    alerts.sort(key=lambda a: a.get("timestamp", ""), reverse=True)
    return {"success": True, "total_alerts": len(alerts), "alerts": alerts}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Backend API on port 8003")
    uvicorn.run(app, host="0.0.0.0", port=8003, log_level="warning")
