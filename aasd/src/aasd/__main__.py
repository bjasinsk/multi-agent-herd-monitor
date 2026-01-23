import asyncio
import math
import random

import spade
import spade.cli

from aasd.agent import Boundaries, CowAgent, HealthStatus, Location
from aasd.shepherd import ShepherdAgent

import json
from pathlib import Path

# How many cows to spawn
NUM_AGENTS = 15
# Set to 0 to arrange cows in a minimum spanning tree (information propagation stops by itself when it reaches leaves)
# Every value >0 adds that many extra edges to create cycles (agents must stop propagation by themselves)
NUM_EXTRA_EDGES = 1
# Chance that a cow mutates its location or health at a given second. Higher values lead to more frequent changes.
MUTATION_PROBABILITY = 0.05
# Delay between sending state updates. Set this to a higher value to actually see anything.
SEND_DELAY_SECONDS = 0.5
# Distance between peers that allows for communication
PEER_DISTANCE_THRESHOLD_METERS = 1000.0


def calculate_distance(loc1: Location, loc2: Location) -> float:
    """Calculate Euclidean distance between two locations"""
    return math.sqrt((loc1.latitude - loc2.latitude) ** 2 + (loc1.longitude - loc2.longitude) ** 2)


def random_location(boundaries: Boundaries) -> Location:
    """Generate a random location within boundaries"""
    lat = random.uniform(boundaries.lat_min, boundaries.lat_max)
    lon = random.uniform(boundaries.lon_min, boundaries.lon_max)
    return Location(lat, lon)


def random_health() -> HealthStatus:
    """Generate a random health status"""
    return random.choices([HealthStatus.HEALTHY, HealthStatus.UNHEALTHY], weights=[0.8, 0.2], k=1)[0]

def load_config_from_file(path: str):
    with open(path, "r") as f:
        data = json.load(f)
    boundaries_data = data["boundries"]
    boundaries = Boundaries(
        lat_min=boundaries_data["lat_min"],
        lat_max=boundaries_data["lat_max"],
        lon_min=boundaries_data["lon_min"],
        lon_max=boundaries_data["lon_max"],
    )
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

    boundaries, cow_configs = load_config_from_file("../configs/globalboundaries.json")

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
        start_pos = cow_data["start_position"]
        cow = CowAgent(
            jid=f"cow{cow_data['id']}@localhost",
            password="password",
            cow_id=cow_id,
            boundaries=boundaries,
            initial_location=Location(start_pos["lat"], start_pos["lon"]),
            initial_health=random_health(),
            mutation_probability=MUTATION_PROBABILITY,
            send_delay_seconds=SEND_DELAY_SECONDS,
            get_peer_jids_in_range_fn=get_peer_jids_in_range,
        )
        cows[cow.cow_id] = cow

    for cow in cows.values():
        await cow.start()

    shepherd = ShepherdAgent("shepherd@localhost", "password", boundaries)
    await shepherd.start()

    print(f"\nAll {NUM_AGENTS} cows started. They will update properties at random intervals.")
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
