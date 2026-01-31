import argparse
import asyncio
import json
import math
import random
from pathlib import Path

import geopandas
import spade
import spade.cli
from shapely.geometry import Point, Polygon

from aasd.cow_agent import Boundaries, CowAgent, HealthStatus, Location
from aasd.shepherd_agent import ShepherdAgent


def calculate_distance(loc1: Location, loc2: Location) -> float:
    # FIXME use Location.distance_to instead
    """Calculate Euclidean distance between two locations"""
    return math.sqrt((loc1.latitude - loc2.latitude) ** 2 + (loc1.longitude - loc2.longitude) ** 2)


def random_location(boundaries: Boundaries) -> Location:
    """Generate a random location within boundaries"""
    geoSeries = geopandas.GeoSeries([boundaries.polygon])
    point: Point = geoSeries.sample_points(1)[0]  # type: ignore[assignment]
    return Location(point.x, point.y)


def random_health() -> HealthStatus:
    """Generate a random health status"""
    return random.choices([HealthStatus.HEALTHY, HealthStatus.UNHEALTHY], weights=[0.8, 0.2], k=1)[0]


def load_config_from_file(path: str) -> tuple[Boundaries, list, dict]:
    with open(path, "r") as f:
        data = json.load(f)
    boundaries_data = data["boundaries"]
    polygon_boundaries = [(boundary["lon"], boundary["lat"]) for boundary in boundaries_data]

    # shapely.Polygon store data as (lon, lat)
    boundaries = Boundaries(Polygon(polygon_boundaries))
    cows_config = data.get("cows", [])
    params = data.get("params", {})
    return boundaries, cows_config, params


async def _main() -> None:
    """
    Cow herd tracking system with state synchronization
    """
    parser = argparse.ArgumentParser(description="Cow Herd Tracking System")
    parser.add_argument(
        "--scenario", type=str, default="./scenarios/oneline.json", help="Path to the configuration file"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging", default=False)
    args = parser.parse_args()

    print(
        "Starting cow herd tracking system...\nI nothing happens, ensure that an XMPP server is running on localhost."
    )
    print("\n $ uv run spade run\n")

    boundaries, cow_configs, params = load_config_from_file(args.scenario)

    # Chance that a cow mutates its health at a given interval. Higher values lead to more frequent changes.
    HEALTH_MUTATION_PROBABILITY = params.get("health_mutation_probability", 0.01)
    # Chance that a cow mutates its location at a given interval. Higher values lead to more frequent changes.
    LOC_MUTATION_PROBABILITY = params.get("loc_mutation_probability", 0.5)
    # Range of location mutation as a fraction of total boundaries size
    LOC_MUTATION_RANGE = params.get("loc_mutation_range", 0.01)
    # Mutation interval in seconds
    MUTATION_INTERVAL_SECONDS = params.get("mutation_interval_seconds", 1)
    # Mutation interval jitter in seconds
    MUTATION_INTERVAL_JITTER_SECONDS = params.get("mutation_interval_jitter_seconds", 0.1)
    # Delay between sending state updates. Set this to a higher value to actually see anything.
    SEND_DELAY_SECONDS = params.get("send_delay_seconds", 0.5)
    # Distance between peers that allows for communication
    PEER_DISTANCE_THRESHOLD_METERS = params.get("peer_distance_threshold_meters", 1000.0)
    # Interval for generating cow guidance
    GUIDE_COW_INTERVAL_SECONDS = params.get("guide_cow_interval_seconds", 1.0)
    # Interval for subscribing to peer updates
    SUBSCRIBE_TO_PEERS_INTERVAL_SECONDS = params.get("subscribe_to_peers_interval_seconds", 10.0)
    # Infectious radius in meters
    INFECTIOUS_RADIUS_METERS = params.get("infectious_radius_meters", 300.0)
    # average latitude for simplified movement calculation, defaults to latitude for Warsaw
    AVG_LATITUDE = params.get("avg_latitude", 52.16)
    # Detection radius for peers for clustering movement
    CLUSTERING_MOVEMENT_DETECTION_RADIUS_METERS = params.get("clustering_movement_detection_radius_meters", 1000)
    # Cohesion coefficient for clustering movement (more -> moves more rapidly towards other cows)
    CLUSTERING_MOVEMENT_COHESION = params.get("clustering_movement_cohesion", 0.00005)
    # Separation coefficient for clustering movement (more -> escapes more rapidly when too close with other cow)
    CLUSTERING_MOVEMENT_SEPARATION = params.get("clustering_movements_separation", 0.0001)
    # Distance for which separation coefficient starts impacting movement
    CLUSTERING_MOVEMENT_MIN_SEP_DIST = params.get("clustering_movement_min_sep_dist", 0.001)
    # Step for movement when avoiding infection (more -> escapes more rapidly from an infected cow)
    AVOID_INFECTION_STEP = params.get("avoid_infection_step", 0.0001)

    cows: dict[str, CowAgent] = {}

    def get_peer_jids_in_range(cow_id: str) -> list[str]:
        cow_location = cows[cow_id].location
        return [
            peer.jid.jid
            for peer in cows.values()
            if cow_location.distance_to(peer.location) <= PEER_DISTANCE_THRESHOLD_METERS and peer.cow_id != cow_id
        ]

    # clear state dir
    state_dir = Path("./state")
    for file in state_dir.glob("Cow-*.json"):
        file.unlink()

    for cow_data in cow_configs:
        cow_id = f"Cow-{cow_data['id']}"
        start_pos = cow_data.get("start_position")

        if start_pos and "lat" in start_pos and "lon" in start_pos:
            initial_location = Location(start_pos["lat"], start_pos["lon"])
        else:
            initial_location = random_location(boundaries)

        health_str = cow_data.get("health")
        if health_str is not None:
            initial_health = HealthStatus.HEALTHY if health_str == "healthy" else HealthStatus.UNHEALTHY
        else:
            initial_health = random_health()

        cow = CowAgent(
            jid=f"cow{cow_data['id']}@localhost",
            password="password",
            cow_id=cow_id,
            boundaries=boundaries,
            initial_location=initial_location,
            initial_health=initial_health,
            health_mutation_probability=HEALTH_MUTATION_PROBABILITY,
            loc_mutation_probability=LOC_MUTATION_PROBABILITY,
            loc_mutation_range=LOC_MUTATION_RANGE,
            mutation_interval_seconds=MUTATION_INTERVAL_SECONDS,
            mutation_interval_jitter_seconds=MUTATION_INTERVAL_JITTER_SECONDS,
            send_delay_seconds=SEND_DELAY_SECONDS,
            get_peer_jids_in_range_fn=get_peer_jids_in_range,
            guide_cow_interval_seconds=GUIDE_COW_INTERVAL_SECONDS,
            subscribe_to_peers_interval_seconds=SUBSCRIBE_TO_PEERS_INTERVAL_SECONDS,
            infectious_radius_meters=INFECTIOUS_RADIUS_METERS,
            avg_latitude=AVG_LATITUDE,
            clustering_movement_detection_radius_meters=CLUSTERING_MOVEMENT_DETECTION_RADIUS_METERS,
            clustering_movement_cohesion=CLUSTERING_MOVEMENT_COHESION,
            clustering_movement_separation=CLUSTERING_MOVEMENT_SEPARATION,
            clustering_movement_min_sep_dist=CLUSTERING_MOVEMENT_MIN_SEP_DIST,
            avoid_infection_step=AVOID_INFECTION_STEP,
            verbose_logging=args.verbose,
        )
        cows[cow.cow_id] = cow

    for cow in cows.values():
        await cow.start()

    shepherd = ShepherdAgent("shepherd@localhost", "password", boundaries, verbose_logging=args.verbose)
    await shepherd.start()

    print("Press Ctrl+C to stop...\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping cow tracking system...")
        for cow in cows.values():
            await cow.stop()


def main() -> None:
    spade.run(_main())


if __name__ == "__main__":
    main()
