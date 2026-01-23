import math

from shapely.geometry import Point
from shapely.ops import nearest_points

from aasd.agent_commons import Boundaries, CowState, Location, MovementMap


def is_inside_global_boundries(location: Location, boundaries: Boundaries) -> bool:
    return bool(boundaries.polygon.contains(Point(location.longitude, location.latitude)))


def check_infected_radius(
    cow_state: CowState, location: Location, movement_map: MovementMap
) -> tuple[Location, float] | None:
    for infected_location, avoid_radius in movement_map.infected_areas:
        if infected_location == cow_state.location:
            continue

        if location.distance_to(infected_location) < avoid_radius:
            return infected_location, avoid_radius

    return None


def check_cow_position(cow_state: CowState, movement_map: MovementMap) -> bool:
    actual_location = cow_state.location
    actual_boundaries = movement_map.boundaries

    if not is_inside_global_boundries(actual_location, actual_boundaries):
        return False

    in_infected_radius = check_infected_radius(cow_state, actual_location, movement_map)
    if in_infected_radius is not None:
        return False

    return True


def move_towards_box(location: Location, boundaries: Boundaries, step: float) -> Location:
    # destination = nearest point in box
    nearest_point, origin_point = nearest_points(boundaries.polygon, Point(location.longitude, location.latitude))
    destination_lon = nearest_point.x
    destination_lat = nearest_point.y

    delta_lat = destination_lat - location.latitude
    delta_lon = destination_lon - location.longitude
    length = math.sqrt(delta_lat * delta_lat + delta_lon * delta_lon) or 1.0

    move_lat = (delta_lat / length) * step
    move_lon = (delta_lon / length) * step

    return Location(location.latitude + move_lat, location.longitude + move_lon)


def rotate_direction_vector(x: float, y: float, degrees: float) -> tuple[float, float]:
    rad = math.radians(degrees)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)
