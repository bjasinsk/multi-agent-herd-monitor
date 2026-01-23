import pytest
from aasd.agent_commons import Location, Boundaries
from aasd.map_commons import check_global_boundaries

def test_distance_to_itself():
    loc = Location(latitude=52.12, longitude=20.46)
    assert loc.distance_to(loc) == 0

def test_distance_to_other():
    loc1 = Location(latitude=52.12, longitude=20.46)
    loc2 = Location(latitude=52.13, longitude=20.47)
    dist = loc1.distance_to(loc2)
    assert dist > 0
    assert pytest.approx(dist, rel=0.01) == 1305

#### BOUNDIRES CLASS WILL BE CHANGED TO POLYGON
def test_location_inside_boundaries():
    bounds = Boundaries(lat_min=52.115, lat_max=52.135, lon_min=20.455, lon_max=20.495)
    loc_inside = Location(latitude=52.12, longitude=20.46)
    assert check_global_boundaries(loc_inside, bounds) is True

def test_location_outside_boundaries_lat():
    bounds = Boundaries(lat_min=52.115, lat_max=52.135, lon_min=20.455, lon_max=20.495)
    loc_outside_lat = Location(latitude=52.14, longitude=20.46)
    assert check_global_boundaries(loc_outside_lat, bounds) is False

def test_location_outside_boundaries_lon():
    bounds = Boundaries(lat_min=52.115, lat_max=52.135, lon_min=20.455, lon_max=20.495)
    loc_outside_lon = Location(latitude=52.12, longitude=20.50)
    assert check_global_boundaries(loc_outside_lon, bounds) is False

def test_location_on_boundary_corner():
    bounds = Boundaries(lat_min=52.115, lat_max=52.135, lon_min=20.455, lon_max=20.495)
    loc_on_min_edge = Location(latitude=52.115, longitude=20.455)
    loc_on_max_edge = Location(latitude=52.135, longitude=20.495)
    assert check_global_boundaries(loc_on_min_edge, bounds) is True
    assert check_global_boundaries(loc_on_max_edge, bounds) is True
#### BOUNDIRES CLASS WILL BE CHANGED TO POLYGON
