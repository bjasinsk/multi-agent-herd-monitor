import math

import pytest
from shapely.geometry import Polygon

from aasd.agent_commons import (
    Boundaries,
    CowState,
    HealthStatus,
    Location,
    MovementMap,
)


class TestLocation:
    """Tests for Location class"""

    def test_distance_to_itself(self) -> None:
        """Test distance from location to itself is 0"""
        loc = Location(latitude=52.12, longitude=20.46)
        assert loc.distance_to(loc) == 0

    def test_distance_to_other(self) -> None:
        """Test distance calculation between two locations"""
        loc1 = Location(latitude=52.12, longitude=20.46)
        loc2 = Location(latitude=52.13, longitude=20.47)
        dist = loc1.distance_to(loc2)
        assert dist > 0
        assert pytest.approx(dist, rel=0.01) == 1305

    def test_distance_symmetry(self) -> None:
        """Test that distance is symmetric: d(A,B) == d(B,A)"""
        loc1 = Location(latitude=52.12, longitude=20.46)
        loc2 = Location(latitude=52.15, longitude=20.50)
        dist1_to_2 = loc1.distance_to(loc2)
        dist2_to_1 = loc2.distance_to(loc1)
        assert pytest.approx(dist1_to_2, abs=1e-6) == dist2_to_1

    def test_distance_north_south(self) -> None:
        """Test distance between two points along same longitude (north-south)"""
        loc_south = Location(latitude=52.0, longitude=20.0)
        loc_north = Location(latitude=52.01, longitude=20.0)
        dist = loc_south.distance_to(loc_north)
        # Approximately 1111 meters per degree of latitude
        assert pytest.approx(dist, rel=0.01) == 1111

    def test_distance_east_west(self) -> None:
        """Test distance between two points along same latitude (east-west)"""
        loc_west = Location(latitude=52.0, longitude=20.0)
        loc_east = Location(latitude=52.0, longitude=20.01)
        dist = loc_west.distance_to(loc_east)
        # At latitude 52, approximately 660 meters per degree of longitude
        assert dist > 0

    def test_distance_very_close_points(self) -> None:
        """Test distance between very close points"""
        loc1 = Location(latitude=52.12, longitude=20.46)
        loc2 = Location(latitude=52.120001, longitude=20.460001)
        dist = loc1.distance_to(loc2)
        # Should be small, a few millimeters
        assert 0 < dist < 1

    def test_distance_far_points(self) -> None:
        """Test distance between points far apart"""
        loc1 = Location(latitude=0.0, longitude=0.0)
        loc2 = Location(latitude=90.0, longitude=0.0)
        dist = loc1.distance_to(loc2)
        # Should be close to quarter of Earth's circumference
        earth_radius = 6371000
        expected = math.pi * earth_radius / 2
        assert pytest.approx(dist, rel=0.01) == expected


class TestHealthStatus:
    """Tests for HealthStatus enum"""

    def test_healthy_value(self) -> None:
        """Test HealthStatus.HEALTHY value"""
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_unhealthy_value(self) -> None:
        """Test HealthStatus.UNHEALTHY value"""
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_enum_creation_from_value(self) -> None:
        """Test creating HealthStatus from value"""
        healthy = HealthStatus("healthy")
        unhealthy = HealthStatus("unhealthy")
        assert healthy == HealthStatus.HEALTHY
        assert unhealthy == HealthStatus.UNHEALTHY


class TestBoundaries:
    """Tests for Boundaries class"""

    def test_boundaries_with_polygon(self) -> None:
        """Test creating Boundaries with a polygon"""
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        boundaries = Boundaries(poly)
        assert boundaries.polygon == poly

    def test_boundaries_polygon_access(self) -> None:
        """Test accessing polygon from Boundaries"""
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        boundaries = Boundaries(poly)
        assert boundaries.polygon.area > 0


class TestMovementMap:
    """Tests for MovementMap class"""

    def test_movement_map_creation(self) -> None:
        """Test creating MovementMap"""
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        boundaries = Boundaries(poly)
        infected_areas: list[tuple[Location, float]] = []
        movement_map = MovementMap(boundaries=boundaries, infected_areas=infected_areas)
        assert movement_map.boundaries == boundaries
        assert movement_map.infected_areas == infected_areas

    def test_movement_map_with_infected_areas(self) -> None:
        """Test MovementMap with infected areas"""
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        boundaries = Boundaries(poly)
        loc1 = Location(latitude=0.5, longitude=0.5)
        loc2 = Location(latitude=0.7, longitude=0.7)
        infected_areas: list[tuple[Location, float]] = [(loc1, 100.0), (loc2, 200.0)]
        movement_map = MovementMap(boundaries=boundaries, infected_areas=infected_areas)
        assert len(movement_map.infected_areas) == 2
        assert movement_map.infected_areas[0] == (loc1, 100.0)
        assert movement_map.infected_areas[1] == (loc2, 200.0)


class TestCowState:
    """Tests for CowState class"""

    def test_cow_state_creation(self) -> None:
        """Test creating a CowState"""
        loc = Location(latitude=52.12, longitude=20.46)
        poly = Polygon([(20.0, 52.0), (21.0, 52.0), (21.0, 53.0), (20.0, 53.0)])
        boundaries = Boundaries(poly)
        cow_state = CowState(
            location=loc,
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=1000.0,
            peers=["cow1", "cow2"],
        )
        assert cow_state.location == loc
        assert cow_state.health == HealthStatus.HEALTHY
        assert cow_state.timestamp == 1000.0
        assert cow_state.peers == ["cow1", "cow2"]

    def test_cow_state_to_json(self) -> None:
        """Test converting CowState to JSON"""
        loc = Location(latitude=52.12, longitude=20.46)
        poly = Polygon([(20.0, 52.0), (21.0, 52.0), (21.0, 53.0), (20.0, 53.0)])
        boundaries = Boundaries(poly)
        cow_state = CowState(
            location=loc,
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=1000.0,
            peers=["cow1", "cow2"],
        )
        json_data = cow_state.to_json()

        assert json_data["location"]["latitude"] == 52.12
        assert json_data["location"]["longitude"] == 20.46
        assert json_data["health"] == "healthy"
        assert json_data["timestamp"] == 1000.0
        assert json_data["peers"] == ["cow1", "cow2"]
        assert len(json_data["boundaries"]) > 0

    def test_cow_state_from_json(self) -> None:
        """Test creating CowState from JSON"""
        cow_data = {
            "location": {"latitude": 52.12, "longitude": 20.46},
            "health": "healthy",
            "boundaries": [[52.0, 20.0], [53.0, 20.0], [53.0, 21.0], [52.0, 21.0]],
            "timestamp": 1000.0,
            "peers": ["cow1", "cow2"],
        }
        cow_state = CowState.from_json(cow_data)

        assert cow_state.location.latitude == 52.12
        assert cow_state.location.longitude == 20.46
        assert cow_state.health == HealthStatus.HEALTHY
        assert cow_state.timestamp == 1000.0
        assert cow_state.peers == ["cow1", "cow2"]

    def test_cow_state_round_trip_json(self) -> None:
        """Test that CowState survives JSON round trip"""
        loc = Location(latitude=52.12, longitude=20.46)
        poly = Polygon([(20.0, 52.0), (21.0, 52.0), (21.0, 53.0), (20.0, 53.0)])
        boundaries = Boundaries(poly)
        original = CowState(
            location=loc,
            health=HealthStatus.UNHEALTHY,
            boundaries=boundaries,
            timestamp=5000.0,
            peers=["cow3", "cow4", "cow5"],
        )

        # Convert to JSON and back
        json_data = original.to_json()
        restored = CowState.from_json(json_data)

        # Check that values are preserved
        assert restored.location.latitude == pytest.approx(original.location.latitude, abs=1e-6)
        assert restored.location.longitude == pytest.approx(original.location.longitude, abs=1e-6)
        assert restored.health == original.health
        assert restored.timestamp == original.timestamp
        assert restored.peers == original.peers

    def test_cow_state_from_json_without_peers(self) -> None:
        """Test creating CowState from JSON without peers field"""
        cow_data = {
            "location": {"latitude": 52.12, "longitude": 20.46},
            "health": "healthy",
            "boundaries": [[52.0, 20.0], [53.0, 20.0], [53.0, 21.0], [52.0, 21.0]],
            "timestamp": 1000.0,
        }
        cow_state = CowState.from_json(cow_data)

        assert cow_state.peers == []

    def test_cow_state_with_unhealthy_status(self) -> None:
        """Test CowState with UNHEALTHY status"""
        loc = Location(latitude=52.12, longitude=20.46)
        poly = Polygon([(20.0, 52.0), (21.0, 52.0), (21.0, 53.0), (20.0, 53.0)])
        boundaries = Boundaries(poly)
        cow_state = CowState(
            location=loc,
            health=HealthStatus.UNHEALTHY,
            boundaries=boundaries,
            timestamp=1000.0,
            peers=[],
        )
        json_data = cow_state.to_json()
        assert json_data["health"] == "unhealthy"

    def test_cow_state_peers_list(self) -> None:
        """Test CowState with various peers lists"""
        loc = Location(latitude=52.12, longitude=20.46)
        poly = Polygon([(20.0, 52.0), (21.0, 52.0), (21.0, 53.0), (20.0, 53.0)])
        boundaries = Boundaries(poly)

        # Test with empty peers
        cow_state1 = CowState(
            location=loc,
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=1000.0,
            peers=[],
        )
        assert cow_state1.peers == []

        # Test with many peers
        many_peers = [f"cow{i}" for i in range(100)]
        cow_state2 = CowState(
            location=loc,
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=1000.0,
            peers=many_peers,
        )
        assert len(cow_state2.peers) == 100
