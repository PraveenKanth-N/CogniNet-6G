"""
Factory World & Industrial Layout Representation
Defines spatial zones, waypoints, and obstacle boundaries for a 100m x 80m smart factory.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class Zone:
    name: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    zone_type: str  # "loading", "production", "inspection", "charging"

class FactoryWorld:
    def __init__(self, width: float = 100.0, height: float = 80.0):
        self.width = width
        self.height = height

        # 4 Functional Factory Zones
        self.zones: Dict[str, Zone] = {
            "loading_dock": Zone("Loading Dock", 0.0, 25.0, 0.0, 30.0, "loading"),
            "assembly_aisles": Zone("Assembly Aisles", 30.0, 70.0, 10.0, 70.0, "production"),
            "inspection_station": Zone("Inspection Station", 75.0, 100.0, 45.0, 80.0, "inspection"),
            "charging_bays": Zone("Charging Bays", 75.0, 100.0, 0.0, 25.0, "charging")
        }

        # Strategic Navigation Waypoints
        self.waypoints: Dict[str, Tuple[float, float]] = {
            "WP_LOAD_1": (12.5, 15.0),
            "WP_LOAD_2": (18.0, 25.0),
            "WP_AISLE_MAIN": (50.0, 40.0),
            "WP_AISLE_NORTH": (50.0, 65.0),
            "WP_AISLE_SOUTH": (50.0, 15.0),
            "WP_INSPECT_ENTRY": (80.0, 50.0),
            "WP_INSPECT_BAY": (90.0, 65.0),
            "WP_CHARGE_1": (85.0, 12.0),
            "WP_CHARGE_2": (92.0, 12.0)
        }

        # gNodeB Base Station Coordinates for mmWave / Sub-THz Coverage
        self.base_stations: List[Tuple[float, float, float]] = [
            (30.0, 40.0, 6.0),   # BS-1: Covers loading and western aisles (height = 6m)
            (75.0, 40.0, 6.0)    # BS-2: Covers inspection, charging, and eastern aisles
        ]

    def get_zone_for_position(self, x: float, y: float) -> str:
        for z_name, z in self.zones.items():
            if z.x_min <= x <= z.x_max and z.y_min <= y <= z.y_max:
                return z_name
        return "general_transit"
