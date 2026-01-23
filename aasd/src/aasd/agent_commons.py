import math
from enum import Enum
from typing import Any, NamedTuple, Self


class HealthStatus(Enum):
    """Health status of a cow"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class Boundaries(NamedTuple):
    """Geographic boundaries for cow movement"""

    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


class Location(NamedTuple):
    """Geographic location (latitude, longitude)"""

    latitude: float
    longitude: float

    def distance_to(self, other: Self) -> float:
        """Calculate distance to another location in meters using Haversine formula"""
        R = 6371000
        phi1 = math.radians(self.latitude)
        phi2 = math.radians(other.latitude)
        delta_phi = math.radians(other.latitude - self.latitude)
        delta_lambda = math.radians(other.longitude - self.longitude)

        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        dist = R * c
        return dist


class MovementMap(NamedTuple):
    boundaries: Boundaries
    infected_areas: list[tuple[Location, float]]


class CowState(NamedTuple):
    """State of a cow at a specific point in time"""

    location: Location
    health: HealthStatus
    boundaries: Boundaries
    timestamp: float
    peers: list[str]

    def to_json(self) -> dict[str, Any]:
        """Convert a CowState object to dict for JSON serialization"""
        return {
            "location": {
                "latitude": self.location.latitude,
                "longitude": self.location.longitude,
            },
            "health": self.health.value,
            "boundaries": {
                "lat_min": self.boundaries.lat_min,
                "lat_max": self.boundaries.lat_max,
                "lon_min": self.boundaries.lon_min,
                "lon_max": self.boundaries.lon_max,
            },
            "timestamp": self.timestamp,
            "peers": self.peers,
        }

    @classmethod
    def from_json(cls, cow_data: dict[str, Any]) -> Self:
        """Convert a dict to CowState object"""
        location_data = cow_data["location"]
        boundaries_data = cow_data["boundaries"]
        return cls(
            location=Location(location_data["latitude"], location_data["longitude"]),
            health=HealthStatus(cow_data["health"]),
            boundaries=Boundaries(
                boundaries_data["lat_min"],
                boundaries_data["lat_max"],
                boundaries_data["lon_min"],
                boundaries_data["lon_max"],
            ),
            timestamp=cow_data["timestamp"],
            peers=cow_data.get("peers", []),
        )
