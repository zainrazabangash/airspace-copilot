"""
Data Store Manager
Handles storage and retrieval of flight snapshots and alerts
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataStore:
    """Manages flight data snapshots and alerts storage"""
    
    def __init__(self, snapshots_dir: str = "./data/snapshots", alerts_dir: str = "./data/alerts"):
        self.snapshots_dir = Path(snapshots_dir)
        self.alerts_dir = Path(alerts_dir)
        
        # Create directories if they don't exist
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"DataStore initialized: snapshots={self.snapshots_dir}, alerts={self.alerts_dir}")
    
    def save_snapshot(self, region_name: str, data: Dict) -> str:
        """Save a flight snapshot for a region"""
        timestamp = datetime.now().isoformat()
        filename = f"{region_name}_{timestamp.replace(':', '-')}.json"
        filepath = self.snapshots_dir / filename
        
        snapshot = {
            "region": region_name,
            "timestamp": timestamp,
            "data": data
        }
        
        with open(filepath, 'w') as f:
            json.dump(snapshot, f, indent=2)
        
        logger.info(f"Saved snapshot: {filename}")
        return str(filepath)
    
    def get_latest_snapshot(self, region_name: str) -> Optional[Dict]:
        """Get the most recent snapshot for a region"""
        snapshots = list(self.snapshots_dir.glob(f"{region_name}_*.json"))
        
        if not snapshots:
            logger.warning(f"No snapshots found for region: {region_name}")
            return None
        
        # Get the most recent file
        latest = max(snapshots, key=os.path.getmtime)
        
        with open(latest, 'r') as f:
            data = json.load(f)
        
        logger.info(f"Retrieved latest snapshot for {region_name}: {latest.name}")
        return data
    
    def get_snapshot_by_timestamp(self, region_name: str, timestamp: str) -> Optional[Dict]:
        """Get a specific snapshot by timestamp"""
        filename = f"{region_name}_{timestamp.replace(':', '-')}.json"
        filepath = self.snapshots_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Snapshot not found: {filename}")
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def get_flight_by_callsign(self, callsign: str) -> Optional[Dict]:
        """Search for a flight by callsign across all recent snapshots"""
        # Get all snapshots
        snapshots = sorted(self.snapshots_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        
        # Search through recent snapshots (last 10)
        for snapshot_file in snapshots[:10]:
            with open(snapshot_file, 'r') as f:
                snapshot = json.load(f)
            
            if "data" in snapshot and "states" in snapshot["data"]:
                for state in snapshot["data"]["states"]:
                    # OpenSky state format: [icao24, callsign, origin_country, ...]
                    if len(state) > 1 and state[1] and state[1].strip() == callsign.strip():
                        return {
                            "callsign": state[1].strip() if state[1] else None,
                            "icao24": state[0],
                            "origin_country": state[2],
                            "longitude": state[5],
                            "latitude": state[6],
                            "altitude": state[7],
                            "velocity": state[9],
                            "heading": state[10],
                            "vertical_rate": state[11],
                            "on_ground": state[8],
                            "timestamp": snapshot["timestamp"],
                            "region": snapshot["region"]
                        }
        
        logger.warning(f"Flight not found: {callsign}")
        return None
    
    def get_flight_by_icao24(self, icao24: str) -> Optional[Dict]:
        """Search for a flight by ICAO24 address"""
        snapshots = sorted(self.snapshots_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        
        for snapshot_file in snapshots[:10]:
            with open(snapshot_file, 'r') as f:
                snapshot = json.load(f)
            
            if "data" in snapshot and "states" in snapshot["data"]:
                for state in snapshot["data"]["states"]:
                    if len(state) > 0 and state[0] == icao24:
                        return {
                            "callsign": state[1].strip() if state[1] else None,
                            "icao24": state[0],
                            "origin_country": state[2],
                            "longitude": state[5],
                            "latitude": state[6],
                            "altitude": state[7],
                            "velocity": state[9],
                            "heading": state[10],
                            "vertical_rate": state[11],
                            "on_ground": state[8],
                            "timestamp": snapshot["timestamp"],
                            "region": snapshot["region"]
                        }
        
        logger.warning(f"Flight not found: {icao24}")
        return None
    
    def save_alert(self, alert_data: Dict) -> str:
        """Save an anomaly alert"""
        timestamp = datetime.now().isoformat()
        alert_id = f"alert_{timestamp.replace(':', '-')}"
        filename = f"{alert_id}.json"
        filepath = self.alerts_dir / filename
        
        alert = {
            "alert_id": alert_id,
            "timestamp": timestamp,
            **alert_data
        }
        
        with open(filepath, 'w') as f:
            json.dump(alert, f, indent=2)
        
        logger.info(f"Saved alert: {alert_id}")
        return alert_id
    
    def get_active_alerts(self, max_age_hours: int = 24) -> List[Dict]:
        """Get all active alerts within the specified time window"""
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        alerts = []
        
        for alert_file in self.alerts_dir.glob("alert_*.json"):
            with open(alert_file, 'r') as f:
                alert = json.load(f)
            
            alert_time = datetime.fromisoformat(alert["timestamp"])
            if alert_time >= cutoff_time:
                alerts.append(alert)
        
        # Sort by timestamp, most recent first
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        
        logger.info(f"Retrieved {len(alerts)} active alerts")
        return alerts
    
    def cleanup_old_snapshots(self, max_snapshots: int = 100):
        """Remove old snapshots, keeping only the most recent ones"""
        snapshots = sorted(self.snapshots_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        
        if len(snapshots) > max_snapshots:
            for old_snapshot in snapshots[max_snapshots:]:
                old_snapshot.unlink()
                logger.info(f"Deleted old snapshot: {old_snapshot.name}")


# Example usage
if __name__ == "__main__":
    store = DataStore()
    
    # Test saving a snapshot
    test_data = {
        "time": 1234567890,
        "states": [
            ["abc123", "UAL123", "United States", 1234567890, 1234567890, -122.4, 37.8, 10000, False, 250, 90, 0]
        ]
    }
    
    store.save_snapshot("test_region", test_data)
    
    # Test retrieving
    latest = store.get_latest_snapshot("test_region")
    print(f"Latest snapshot: {latest}")
    
    # Test alert
    alert = {
        "callsign": "UAL123",
        "anomaly_type": "high_altitude_low_speed",
        "severity": "medium"
    }
    store.save_alert(alert)
    
    # Get active alerts
    active = store.get_active_alerts()
    print(f"Active alerts: {len(active)}")
