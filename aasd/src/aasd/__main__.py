import asyncio
import math
import random
from typing import List, Tuple

import spade
import spade.cli

from aasd.agent import Boundaries, CowAgent, HealthStatus, Location

# How many cows to spawn
NUM_AGENTS = 15
# Set to 0 to arrange cows in a minimum spanning tree (information propagation stops by itself when it reaches leaves)
# Every value >0 adds that many extra edges to create cycles (agents must stop propagation by themselves)
NUM_EXTRA_EDGES = 1
# Chance that a cow mutates its location or health at a given second. Higher values lead to more frequent changes.
MUTATION_PROBABILITY = 0.05
# Delay between sending state updates. Set this to a higher value to actually see anything.
SEND_DELAY_SECONDS = 0.5


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


def build_minimum_spanning_tree(cows: List[CowAgent]) -> List[Tuple[int, int]]:
    """
    Build a minimum spanning tree using Prim's algorithm based on initial cow locations.
    Returns a list of (cow_index_i, cow_index_j) pairs representing edges in the tree.
    """
    n = len(cows)
    if n <= 1:
        return []

    # Track which nodes are in the tree
    in_tree = [False] * n
    in_tree[0] = True  # Start with the first cow

    edges = []

    # Build MST by repeatedly finding the minimum edge connecting tree to non-tree nodes
    for _ in range(n - 1):
        min_distance = float("inf")
        min_edge = None

        for i in range(n):
            if not in_tree[i]:
                continue
            for j in range(n):
                if in_tree[j]:
                    continue

                distance = calculate_distance(cows[i].location, cows[j].location)
                if distance < min_distance:
                    min_distance = distance
                    min_edge = (i, j)

        if min_edge:
            edges.append(min_edge)
            in_tree[min_edge[1]] = True

    return edges


async def _main() -> None:
    """
    Cow herd tracking system with state synchronization
    """
    print(
        "Starting cow herd tracking system...\nI nothing happens, ensure that an XMPP server is running on localhost."
    )
    print("\n $ uv run spade run\n")
    boundaries = Boundaries(
        lat_min=52.114894130999346,
        lat_max=52.135600964392594,
        lon_min=20.455205770503397,
        lon_max=20.494292477391095,
    )

    cows = []

    for i in range(1, NUM_AGENTS + 1):
        cow = CowAgent(
            f"cow{i}@localhost",
            "password",
            f"Cow-{i}",
            boundaries,
            random_location(boundaries),
            random_health(),
            mutation_probability=MUTATION_PROBABILITY,
            send_delay_seconds=SEND_DELAY_SECONDS,
        )
        cows.append(cow)

    # Build minimum spanning tree based on initial locations
    print("Building communication tree based on initial locations...")
    mst_edges = build_minimum_spanning_tree(cows)

    edge_set = set()
    for i, j in mst_edges:
        edge_set.add((min(i, j), max(i, j)))

    for i, j in mst_edges:
        cow_i_jid = f"cow{i + 1}@localhost"
        cow_j_jid = f"cow{j + 1}@localhost"

        cows[i].add_peer(cow_j_jid)
        cows[j].add_peer(cow_i_jid)

        print(f"  Connected Cow-{i + 1} <-> Cow-{j + 1}")

    print("\nAdding one extra connection to create a cycle...")

    # Collect all candidate edges not in MST with their distances
    candidate_edges = []
    for i in range(len(cows)):
        for j in range(i + 1, len(cows)):
            edge = (i, j)
            if edge not in edge_set:
                distance = calculate_distance(cows[i].location, cows[j].location)
                candidate_edges.append((distance, edge))

    # Sort by distance and pick one from the cheaper half (but not the cheapest)
    if candidate_edges:
        candidate_edges.sort(key=lambda x: x[0])
        # Pick an edge from the first quartile (excluding the very cheapest)
        quartile_size = max(1, len(candidate_edges) // 4)
        # Choose the edge at position between 1 and quartile_size
        chosen_index = min(quartile_size // 2 + 1, len(candidate_edges) - 1)
        extra_edges = candidate_edges[chosen_index : chosen_index + NUM_EXTRA_EDGES]

        for extra_edge in extra_edges:
            i, j = extra_edge[1]
            cow_i_jid = f"cow{i + 1}@localhost"
            cow_j_jid = f"cow{j + 1}@localhost"

            cows[i].add_peer(cow_j_jid)
            cows[j].add_peer(cow_i_jid)

            print(
                f"  Extra connection: Cow-{i + 1} <-> Cow-{j + 1} (creates a cycle, rank {chosen_index + 1} of {len(candidate_edges)} candidates)"
            )

    for cow in cows:
        await cow.start()

    print(f"\nAll {NUM_AGENTS} cows started. They will update properties at random intervals.")
    print("Press Ctrl+C to stop...\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping cow tracking system...")
        for cow in cows:
            await cow.stop()


def main() -> None:
    spade.run(_main())


if __name__ == "__main__":
    main()
