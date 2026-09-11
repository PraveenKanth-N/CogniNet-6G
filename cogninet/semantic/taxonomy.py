"""
Semantic Taxonomy & Priority Specification
Explicitly defines the 4-tier semantic classification scheme and decouples
semantic functional importance from raw network deadline urgency.
"""

import enum
from typing import Dict, Any

class SemanticClass(enum.Enum):
    CRITICAL = 0    # Emergency stop, collision avoidance, hard safety events
    HIGH = 1        # Motion commands, navigation updates, trajectory corrections
    MEDIUM = 2      # Mission synchronization, fleet coordination, localization pings
    LOW = 3         # Routine battery reporting, diagnostics, temperature telemetry

# Canonical semantic importance weights w_i in [0, 1]
SEMANTIC_BASE_WEIGHTS = {
    SemanticClass.CRITICAL: 0.95,
    SemanticClass.HIGH: 0.75,
    SemanticClass.MEDIUM: 0.50,
    SemanticClass.LOW: 0.15
}

# Task mapping to semantic classes
TASK_TO_SEMANTIC_CLASS = {
    "EMERGENCY_STOP": SemanticClass.CRITICAL,
    "COLLISION_AVOID": SemanticClass.CRITICAL,
    "NAVIGATION": SemanticClass.HIGH,
    "WAYPOINT_UPDATE": SemanticClass.HIGH,
    "MISSION_SYNC": SemanticClass.MEDIUM,
    "LOCALIZATION": SemanticClass.MEDIUM,
    "TELEMETRY": SemanticClass.LOW,
    "BATTERY_STATUS": SemanticClass.LOW,
    "INSPECTION_VIDEO": SemanticClass.MEDIUM
}
