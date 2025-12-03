import asyncio

import spade
import spade.cli

from aasd.agent import CowAgent


async def _main() -> None:
    """
    Cow herd tracking system with state synchronization
    """
    print("Starting cow herd tracking system...\nEnsure that an XMPP server is running on localhost.")
    print("\n $ uv run spade run\n")
    # Define boundaries for the virtual fence (lat_min, lat_max, lon_min, lon_max)
    boundaries = (50.0, 52.0, 19.0, 21.0)  # Example area in Poland

    # Create cow agents
    num_cows = 6
    cows = []

    for i in range(1, num_cows + 1):
        cow = CowAgent(f"cow{i}@localhost", "password", f"Cow-{i}", boundaries)
        cows.append(cow)

    # Set up peer relationships (full mesh - all cows know each other)
    for i, cow in enumerate(cows):
        for j, other_cow in enumerate(cows):
            if i != j:
                cow.add_peer(f"cow{j + 1}@localhost")

    # Start all cows
    for cow in cows:
        await cow.start()

    print(f"\nAll {num_cows} cows started. They will update properties at random intervals (5-10s).")
    print("Press Ctrl+C to stop...\n")

    try:
        # Keep running and let cows exchange state
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
