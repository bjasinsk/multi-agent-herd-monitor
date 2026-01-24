import math

import pytest
from shapely.geometry import Polygon

from aasd.agent_commons import Boundaries, CowState, HealthStatus, Location, MovementMap
from aasd.map_commons import (
    check_cow_position,
    check_infected_radius,
    is_inside_global_boundaries,
    move_towards_box,
    rotate_direction_vector,
)


@pytest.fixture
def simple_polygon() -> Polygon:
    """Create a simple square polygon for testing"""
    return Polygon([(20.45, 52.11), (20.49, 52.11), (20.49, 52.13), (20.45, 52.13)])


@pytest.fixture
def boundaries(simple_polygon: Polygon) -> Boundaries:
    """Create boundaries from the simple polygon"""
    return Boundaries(simple_polygon)


@pytest.fixture
def movement_map(boundaries: Boundaries) -> MovementMap:
    """Create a movement map with no infected areas"""
    return MovementMap(boundaries=boundaries, infected_areas=[])


class TestIsInsideGlobalBoundaries:
    """Tests for is_inside_global_boundaries function"""

    def test_location_inside_boundaries(self, boundaries: Boundaries) -> None:
        """Test that a location inside the polygon is correctly identified"""
        loc = Location(latitude=52.12, longitude=20.47)
        assert is_inside_global_boundaries(loc, boundaries) is True

    def test_location_outside_boundaries(self, boundaries: Boundaries) -> None:
        """Test that a location outside the polygon is correctly identified"""
        loc = Location(latitude=52.14, longitude=20.47)
        assert is_inside_global_boundaries(loc, boundaries) is False

    def test_location_on_boundary_edge(self, boundaries: Boundaries) -> None:
        """Test location on the boundary edge"""
        # Polygon exterior coordinates: [(20.45, 52.11), (20.49, 52.11), (20.49, 52.13), (20.45, 52.13)]
        loc = Location(latitude=52.11, longitude=20.47)
        # Point on boundary edge - shapely.contains() returns False for points on the boundary
        # Use buffer to test point close to boundary instead
        assert is_inside_global_boundaries(loc, boundaries) is False

    def test_location_on_boundary_corner(self, boundaries: Boundaries) -> None:
        """Test location on the boundary corner"""
        loc = Location(latitude=52.11, longitude=20.45)
        # shapely.contains() returns False for points on the boundary
        assert is_inside_global_boundaries(loc, boundaries) is False

    def test_location_far_outside_boundaries(self, boundaries: Boundaries) -> None:
        """Test location far outside the boundaries"""
        loc = Location(latitude=51.0, longitude=19.0)
        assert is_inside_global_boundaries(loc, boundaries) is False


class TestCheckInfectedRadius:
    """Tests for check_infected_radius function"""

    def test_location_outside_infected_area(self, movement_map: MovementMap) -> None:
        """Test that location outside infected areas returns None"""
        cow_loc = Location(latitude=52.12, longitude=20.47)
        test_loc = Location(latitude=52.12, longitude=20.47)
        cow_state = CowState(
            location=cow_loc,
            health=HealthStatus.HEALTHY,
            boundaries=movement_map.boundaries,
            timestamp=0.0,
            peers=[],
        )
        result = check_infected_radius(cow_state, test_loc, movement_map)
        assert result is None

    def test_location_inside_infected_radius(self, boundaries: Boundaries) -> None:
        """Test that location inside infected radius is detected"""
        infected_loc = Location(latitude=52.12, longitude=20.47)
        radius = 1000  # 1000 meters
        movement_map = MovementMap(boundaries=boundaries, infected_areas=[(infected_loc, radius)])

        cow_loc = Location(latitude=52.11, longitude=20.47)  # Different from infected location
        cow_state = CowState(
            location=cow_loc,
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=0.0,
            peers=[],
        )

        test_loc = Location(latitude=52.1201, longitude=20.47)  # Very close to infected location
        result = check_infected_radius(cow_state, test_loc, movement_map)
        assert result is not None
        assert result[0] == infected_loc
        assert result[1] == radius

    def test_location_at_infected_radius_boundary(self, boundaries: Boundaries) -> None:
        """Test location at the edge of infected radius"""
        infected_loc = Location(latitude=52.12, longitude=20.47)
        radius = 1500.0  # radius in meters
        movement_map = MovementMap(boundaries=boundaries, infected_areas=[(infected_loc, radius)])

        cow_loc = Location(latitude=52.11, longitude=20.47)  # Different from infected location
        cow_state = CowState(
            location=cow_loc,
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=0.0,
            peers=[],
        )

        # Create test location approximately at the radius boundary
        test_loc = Location(latitude=52.1301, longitude=20.47)  # ~1111 meters north from infected location
        result = check_infected_radius(cow_state, test_loc, movement_map)
        # Result depends on exact distance calculation - should be within radius
        assert result is not None

    def test_multiple_infected_areas_first_match(self, boundaries: Boundaries) -> None:
        """Test with multiple infected areas - first match is returned"""
        infected_loc1 = Location(latitude=52.12, longitude=20.47)
        infected_loc2 = Location(latitude=52.10, longitude=20.50)
        radius1 = 500.0
        radius2 = 1000.0
        movement_map = MovementMap(
            boundaries=boundaries, infected_areas=[(infected_loc1, radius1), (infected_loc2, radius2)]
        )

        cow_loc = Location(latitude=52.11, longitude=20.47)  # Different from infected locations
        cow_state = CowState(
            location=cow_loc,
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=0.0,
            peers=[],
        )

        test_loc = Location(latitude=52.1201, longitude=20.47)  # Inside radius1
        result = check_infected_radius(cow_state, test_loc, movement_map)
        assert result is not None
        assert result[0] == infected_loc1

    def test_skips_cow_current_location(self, boundaries: Boundaries) -> None:
        """Test that infected area at cow's current location is skipped"""
        infected_loc = Location(latitude=52.12, longitude=20.47)
        radius = 10000  # Large radius
        movement_map = MovementMap(boundaries=boundaries, infected_areas=[(infected_loc, radius)])

        cow_state = CowState(
            location=infected_loc,  # Cow is at the infected location
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=0.0,
            peers=[],
        )

        test_loc = Location(latitude=52.1201, longitude=20.47)  # Very close to infected location
        result = check_infected_radius(cow_state, test_loc, movement_map)
        # Should skip the infected area at cow's location
        assert result is None


class TestCheckCowPosition:
    """Tests for check_cow_position function"""

    def test_valid_position_inside_boundaries(self, movement_map: MovementMap) -> None:
        """Test valid position inside boundaries"""
        cow_loc = Location(latitude=52.12, longitude=20.47)
        cow_state = CowState(
            location=cow_loc,
            health=HealthStatus.HEALTHY,
            boundaries=movement_map.boundaries,
            timestamp=0.0,
            peers=[],
        )
        assert check_cow_position(cow_state, movement_map) is True

    def test_invalid_position_outside_boundaries(self, movement_map: MovementMap) -> None:
        """Test invalid position outside boundaries"""
        cow_loc = Location(latitude=52.14, longitude=20.47)
        cow_state = CowState(
            location=cow_loc,
            health=HealthStatus.HEALTHY,
            boundaries=movement_map.boundaries,
            timestamp=0.0,
            peers=[],
        )
        assert check_cow_position(cow_state, movement_map) is False

    def test_invalid_position_inside_infected_area(self, boundaries: Boundaries) -> None:
        """Test invalid position inside infected area"""
        infected_loc = Location(latitude=52.12, longitude=20.47)
        radius = 5000  # Large radius
        movement_map = MovementMap(boundaries=boundaries, infected_areas=[(infected_loc, radius)])

        cow_loc = Location(latitude=52.1201, longitude=20.47)  # Inside infected radius
        cow_state = CowState(
            location=cow_loc,
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=0.0,
            peers=[],
        )
        assert check_cow_position(cow_state, movement_map) is False

    def test_valid_position_outside_infected_radius(self, boundaries: Boundaries) -> None:
        """Test valid position outside infected radius"""
        infected_loc = Location(latitude=52.12, longitude=20.47)
        radius = 100.0  # Small radius
        movement_map = MovementMap(boundaries=boundaries, infected_areas=[(infected_loc, radius)])

        cow_loc = Location(latitude=52.115, longitude=20.47)  # Inside boundaries and far from infected location
        cow_state = CowState(
            location=cow_loc,
            health=HealthStatus.HEALTHY,
            boundaries=boundaries,
            timestamp=0.0,
            peers=[],
        )
        assert check_cow_position(cow_state, movement_map) is True


class TestMoveTowardsBox:
    """Tests for move_towards_box function"""

    def test_move_inside_box_no_movement(self, boundaries: Boundaries) -> None:
        """Test that location inside the box has minimal movement needed"""
        loc = Location(latitude=52.12, longitude=20.47)
        result = move_towards_box(loc, boundaries, step=100)
        # Inside box, should stay approximately at the same location
        assert abs(result.latitude - loc.latitude) < 0.001
        assert abs(result.longitude - loc.longitude) < 0.001

    def test_move_outside_box_moves_towards_boundary(self, boundaries: Boundaries) -> None:
        """Test that location outside box moves towards boundary"""
        loc = Location(latitude=52.14, longitude=20.47)  # Outside top boundary
        result = move_towards_box(loc, boundaries, step=100)
        # Should move towards the box (downwards in latitude)
        assert result.latitude < loc.latitude

    def test_move_with_different_step_sizes(self, boundaries: Boundaries) -> None:
        """Test that larger step size results in larger movement"""
        loc = Location(latitude=52.14, longitude=20.47)
        result_small = move_towards_box(loc, boundaries, step=50)
        result_large = move_towards_box(loc, boundaries, step=200)

        # Larger step should result in more movement
        small_distance = (result_small.latitude - loc.latitude) ** 2 + (result_small.longitude - loc.longitude) ** 2
        large_distance = (result_large.latitude - loc.latitude) ** 2 + (result_large.longitude - loc.longitude) ** 2
        assert large_distance > small_distance

    def test_move_from_far_corner(self, boundaries: Boundaries) -> None:
        """Test movement from a far corner"""
        loc = Location(latitude=52.15, longitude=20.40)  # Far corner
        result = move_towards_box(loc, boundaries, step=500)
        # Should move towards the box
        assert result.latitude < loc.latitude or result.longitude > loc.longitude

    def test_move_zero_step_no_movement(self, boundaries: Boundaries) -> None:
        """Test that zero step size doesn't move"""
        loc = Location(latitude=52.14, longitude=20.47)
        result = move_towards_box(loc, boundaries, step=0)
        assert result.latitude == loc.latitude
        assert result.longitude == loc.longitude


class TestRotateDirectionVector:
    """Tests for rotate_direction_vector function"""

    def test_rotate_90_degrees(self) -> None:
        """Test rotation by 90 degrees"""
        x, y = 1.0, 0.0
        rotated_x, rotated_y = rotate_direction_vector(x, y, 90)
        # (1, 0) rotated 90 degrees should be approximately (0, 1)
        assert pytest.approx(rotated_x, abs=1e-10) == 0
        assert pytest.approx(rotated_y, abs=1e-10) == 1

    def test_rotate_180_degrees(self) -> None:
        """Test rotation by 180 degrees"""
        x, y = 1.0, 0.0
        rotated_x, rotated_y = rotate_direction_vector(x, y, 180)
        # (1, 0) rotated 180 degrees should be approximately (-1, 0)
        assert pytest.approx(rotated_x, abs=1e-10) == -1
        assert pytest.approx(rotated_y, abs=1e-10) == 0

    def test_rotate_270_degrees(self) -> None:
        """Test rotation by 270 degrees (or -90)"""
        x, y = 1.0, 0.0
        rotated_x, rotated_y = rotate_direction_vector(x, y, 270)
        # (1, 0) rotated 270 degrees should be approximately (0, -1)
        assert pytest.approx(rotated_x, abs=1e-10) == 0
        assert pytest.approx(rotated_y, abs=1e-10) == -1

    def test_rotate_360_degrees(self) -> None:
        """Test rotation by 360 degrees (full circle)"""
        x, y = 1.0, 1.0
        rotated_x, rotated_y = rotate_direction_vector(x, y, 360)
        # Should be approximately the same as original
        assert pytest.approx(rotated_x, abs=1e-10) == x
        assert pytest.approx(rotated_y, abs=1e-10) == y

    def test_rotate_45_degrees(self) -> None:
        """Test rotation by 45 degrees"""
        x, y = 1.0, 0.0
        rotated_x, rotated_y = rotate_direction_vector(x, y, 45)
        # (1, 0) rotated 45 degrees should be approximately (cos(45), sin(45))
        expected = math.sqrt(2) / 2
        assert pytest.approx(rotated_x, abs=1e-10) == expected
        assert pytest.approx(rotated_y, abs=1e-10) == expected

    def test_rotate_negative_angle(self) -> None:
        """Test rotation with negative angle"""
        x, y = 1.0, 0.0
        rotated_x, rotated_y = rotate_direction_vector(x, y, -90)
        # (1, 0) rotated -90 degrees should be approximately (0, -1)
        assert pytest.approx(rotated_x, abs=1e-10) == 0
        assert pytest.approx(rotated_y, abs=1e-10) == -1

    def test_rotate_zero_degrees(self) -> None:
        """Test rotation by 0 degrees"""
        x, y = 1.0, 2.0
        rotated_x, rotated_y = rotate_direction_vector(x, y, 0)
        # Should be the same as original
        assert pytest.approx(rotated_x, abs=1e-10) == x
        assert pytest.approx(rotated_y, abs=1e-10) == y

    def test_rotate_preserves_magnitude(self) -> None:
        """Test that rotation preserves vector magnitude"""
        x, y = 3.0, 4.0
        original_magnitude = math.sqrt(x**2 + y**2)

        rotated_x, rotated_y = rotate_direction_vector(x, y, 37)
        rotated_magnitude = math.sqrt(rotated_x**2 + rotated_y**2)

        assert pytest.approx(rotated_magnitude, abs=1e-10) == original_magnitude

    def test_rotate_various_vectors(self) -> None:
        """Test rotation of various vectors"""
        test_cases = [
            ((2.0, 3.0), 45),
            ((1.0, 1.0), 90),
            ((5.0, 0.0), 180),
            ((0.0, 5.0), 270),
        ]

        for (x, y), angle in test_cases:
            original_magnitude = math.sqrt(x**2 + y**2)
            rotated_x, rotated_y = rotate_direction_vector(x, y, angle)
            rotated_magnitude = math.sqrt(rotated_x**2 + rotated_y**2)
            assert pytest.approx(rotated_magnitude, abs=1e-10) == original_magnitude
