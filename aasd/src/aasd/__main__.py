import asyncio
import json
import math
import random

import geopandas
import spade
import spade.cli
from shapely.geometry import Point, Polygon

from aasd.agent import Boundaries, CowAgent, HealthStatus, Location
from aasd.shepherd import ShepherdAgent

# Chance that a cow mutates its health at a given interval. Higher values lead to more frequent changes.
HEALTH_MUTATION_PROBABILITY = 0.01
# Chance that a cow mutates its location at a given interval. Higher values lead to more frequent changes.
LOC_MUTATION_PROBABILITY = 0.5
# Range of location mutation as a fraction of total boundaries size
LOC_MUTATION_RANGE = 0.01
# Mutation interval in seconds
MUTATION_INTERVAL_SECONDS = 1
# Mutation interval jitter in seconds
MUTATION_INTERVAL_JITTER_SECONDS = 0.1
# Delay between sending state updates. Set this to a higher value to actually see anything.
SEND_DELAY_SECONDS = 0.5
# Distance between peers that allows for communication
PEER_DISTANCE_THRESHOLD_METERS = 1000.0


def calculate_distance(loc1: Location, loc2: Location) -> float:
    # FIXME this is wrong and does not work with geography, use Location.distance_to instead
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


def load_config_from_file(path: str) -> tuple[Boundaries, list]:
    with open(path, "r") as f:
        data = json.load(f)
    boundaries_data = data["boundaries"]
    polygon_boundaries = [(boundary["lon"], boundary["lat"]) for boundary in boundaries_data]

    # shapely.Polygon store data as (lon, lat)
    boundaries = Boundaries(Polygon(polygon_boundaries))
    cows_config = data.get("cows", [])
    return boundaries, cows_config


async def _main() -> None:
    """
    Cow herd tracking system with state synchronization
    """
    print(
        "Starting cow herd tracking system...\nI nothing happens, ensure that an XMPP server is running on localhost."
    )
    print("\n $ uv run spade run\n")

    boundaries, cow_configs = load_config_from_file("./src/aasd/configs/globalboundaries.json")

    cows: dict[str, CowAgent] = {}

    def get_peer_jids_in_range(cow_id: str) -> list[str]:
        cow_location = cows[cow_id].location
        return [
            peer.jid.jid
            for peer in cows.values()
            if cow_location.distance_to(peer.location) <= PEER_DISTANCE_THRESHOLD_METERS and peer.cow_id != cow_id
        ]

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
        )
        cows[cow.cow_id] = cow

    for cow in cows.values():
        await cow.start()

    shepherd = ShepherdAgent("shepherd@localhost", "password", boundaries)
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
