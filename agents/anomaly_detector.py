"""
Anomaly Detection Logic
Detects unusual flight patterns and behaviors
"""
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies in flight data"""
    
    # Thresholds for anomaly detection
    THRESHOLDS = {
        "max_altitude_meters": 15000,  # ~49,000 feet
        "min_velocity_kmh": 100,  # Very slow for cruising
        "max_velocity_kmh": 1000,  # Unusually fast
        "min_altitude_high_speed": 3000,  # Low altitude threshold for high speed
        "high_speed_threshold": 600,  # km/h
        "stationary_time_seconds": 300,  # 5 minutes
        "max_vertical_rate": 20,  # m/s (very rapid climb/descent)
    }
    
    def __init__(self):
        self.previous_states = {}  # Track flight states over time
        logger.info("Anomaly Detector initialized")
    
    def detect_anomalies(self, flights: List[Dict]) -> List[Dict]:
        """
        Analyze flights and detect anomalies
        
        Returns list of dicts with:
        - flight: original flight data
        - anomaly_type: type of anomaly
        - severity: low, medium, high
        - description: human-readable description
        """
        anomalies = []
        
        for flight in flights:
            flight_anomalies = self._check_flight(flight)
            if flight_anomalies:
                anomalies.extend(flight_anomalies)
        
        logger.info(f"Detected {len(anomalies)} anomalies out of {len(flights)} flights")
        return anomalies
    
    def _check_flight(self, flight: Dict) -> List[Dict]:
        """Check a single flight for anomalies"""
        anomalies = []
        
        # Skip if on ground
        if flight.get("on_ground"):
            return anomalies
        
        callsign = flight.get("callsign") or flight.get("icao24")
        altitude = flight.get("altitude")
        velocity = flight.get("velocity")
        vertical_rate = flight.get("vertical_rate")
        
        # Check 1: High altitude with low speed
        if altitude and velocity:
            if altitude > 8000 and velocity < self.THRESHOLDS["min_velocity_kmh"]:
                anomalies.append({
                    "flight": flight,
                    "anomaly_type": "high_altitude_low_speed",
                    "severity": "medium",
                    "description": f"Flight {callsign} at {altitude}m with only {velocity} km/h"
                })
        
        # Check 2: Extremely high altitude
        if altitude and altitude > self.THRESHOLDS["max_altitude_meters"]:
            anomalies.append({
                "flight": flight,
                "anomaly_type": "excessive_altitude",
                "severity": "high",
                "description": f"Flight {callsign} at unusual altitude: {altitude}m"
            })
        
        # Check 3: High speed at low altitude
        if altitude and velocity:
            if altitude < self.THRESHOLDS["min_altitude_high_speed"] and velocity > self.THRESHOLDS["high_speed_threshold"]:
                anomalies.append({
                    "flight": flight,
                    "anomaly_type": "low_altitude_high_speed",
                    "severity": "high",
                    "description": f"Flight {callsign} at {velocity} km/h at only {altitude}m altitude"
                })
        
        # Check 4: Rapid vertical movement
        if vertical_rate and abs(vertical_rate) > self.THRESHOLDS["max_vertical_rate"]:
            direction = "climbing" if vertical_rate > 0 else "descending"
            anomalies.append({
                "flight": flight,
                "anomaly_type": "rapid_vertical_movement",
                "severity": "medium",
                "description": f"Flight {callsign} {direction} rapidly at {abs(vertical_rate)} m/s"
            })
        
        # Check 5: Unusual velocity
        if velocity:
            if velocity > self.THRESHOLDS["max_velocity_kmh"]:
                anomalies.append({
                    "flight": flight,
                    "anomaly_type": "excessive_speed",
                    "severity": "medium",
                    "description": f"Flight {callsign} traveling at {velocity} km/h (unusually fast)"
                })
        
        # Check 6: Stationary in air (checking with historical data)
        if callsign and velocity is not None and velocity < 50:
            # Check if this is consistent over time
            if callsign in self.previous_states:
                prev_lat = self.previous_states[callsign].get("latitude")
                prev_lon = self.previous_states[callsign].get("longitude")
                curr_lat = flight.get("latitude")
                curr_lon = flight.get("longitude")
                
                if prev_lat and prev_lon and curr_lat and curr_lon:
                    # Simple distance check (very rough approximation)
                    lat_diff = abs(curr_lat - prev_lat)
                    lon_diff = abs(curr_lon - prev_lon)
                    
                    if lat_diff < 0.01 and lon_diff < 0.01 and not flight.get("on_ground"):
                        anomalies.append({
                            "flight": flight,
                            "anomaly_type": "stationary_in_air",
                            "severity": "high",
                            "description": f"Flight {callsign} appears stationary in air"
                        })
            
            # Update previous state
            self.previous_states[callsign] = flight
        
        return anomalies
    
    def generate_summary(self, flights: List[Dict], anomalies: List[Dict], region_name: str) -> str:
        """
        Generate natural language summary of the region
        """
        total_flights = len(flights)
        total_anomalies = len(anomalies)
        
        if total_flights == 0:
            return f"Region {region_name} currently has no active flights."
        
        summary = f"Region {region_name} currently has {total_flights} active flights."
        
        if total_anomalies == 0:
            summary += " All flights appear normal with no anomalies detected."
            return summary
        
        summary += f" {total_anomalies} flight(s) are flagged as anomalous."
        
        # Group anomalies by severity
        critical = [a for a in anomalies if a["severity"] == "high"]
        medium = [a for a in anomalies if a["severity"] == "medium"]
        
        if critical:
            summary += f"\n\nCRITICAL ALERTS ({len(critical)}):"
            for anomaly in critical[:3]:  # Top 3 critical
                callsign = anomaly["flight"].get("callsign") or anomaly["flight"].get("icao24")
                summary += f"\n  - {callsign}: {anomaly['description']}"
        
        if medium:
            summary += f"\n\nMedium Priority ({len(medium)}):"
            for anomaly in medium[:2]:  # Top 2 medium
                callsign = anomaly["flight"].get("callsign") or anomaly["flight"].get("icao24")
                summary += f"\n  - {callsign}: {anomaly['description']}"
        
        # Identify most critical case
        if critical:
            most_critical = critical[0]
            callsign = most_critical["flight"].get("callsign") or most_critical["flight"].get("icao24")
            lat = most_critical["flight"].get("latitude", "unknown")
            lon = most_critical["flight"].get("longitude", "unknown")
            summary += f"\n\nMOST CRITICAL: {callsign} requires immediate attention. Last position: {lat}, {lon}"
        
        return summary


if __name__ == "__main__":
    # Test anomaly detection
    detector = AnomalyDetector()
    
    test_flights = [
        {
            "callsign": "TEST123",
            "icao24": "abc123",
            "altitude": 12000,
            "velocity": 80,  # Too slow for this altitude
            "on_ground": False,
            "latitude": 37.8,
            "longitude": -122.4
        },
        {
            "callsign": "NORMAL1",
            "icao24": "def456",
            "altitude": 10000,
            "velocity": 450,  # Normal
            "on_ground": False,
            "latitude": 37.9,
            "longitude": -122.5
        },
        {
            "callsign": "FAST123",
            "icao24": "ghi789",
            "altitude": 2000,  # Low
            "velocity": 700,  # Too fast for low altitude
            "on_ground": False,
            "latitude": 38.0,
            "longitude": -122.6
        }
    ]
    
    anomalies = detector.detect_anomalies(test_flights)
    print(f"\nDetected {len(anomalies)} anomalies:")
    for a in anomalies:
        print(f"  - {a['anomaly_type']}: {a['description']}")
    
    summary = detector.generate_summary(test_flights, anomalies, "Test Region")
    print(f"\nSummary:\n{summary}")
