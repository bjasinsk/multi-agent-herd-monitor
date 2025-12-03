import spade
import sys
import asyncio
from agent import CowAgent


async def main():
    """
    Cow herd tracking system with state synchronization
    """
    print("Starting cow herd tracking system...")
    
    # Define boundaries for the virtual fence (lat_min, lat_max, lon_min, lon_max)
    boundaries = (50.0, 52.0, 19.0, 21.0)  # Example area in Poland
    
    # Create cow agents
    cow1 = CowAgent('cow1@localhost', 'password', 'Cow-1', boundaries)
    cow2 = CowAgent('cow2@localhost', 'password', 'Cow-2', boundaries)
    cow3 = CowAgent('cow3@localhost', 'password', 'Cow-3', boundaries)
    
    # Set up peer relationships (full mesh - all cows know each other)
    cow1.add_peer('cow2@localhost')
    cow1.add_peer('cow3@localhost')
    
    cow2.add_peer('cow1@localhost')
    cow2.add_peer('cow3@localhost')
    
    cow3.add_peer('cow1@localhost')
    cow3.add_peer('cow2@localhost')
    
    # Start all cows
    await cow1.start()
    await cow2.start()
    await cow3.start()
    
    print("\nAll cows started. They will update properties at random intervals (5-10s).")
    print("Press Ctrl+C to stop...\n")
    
    try:
        # Keep running and let cows exchange state
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping cow tracking system...")
        await cow1.stop()
        await cow2.stop()
        await cow3.stop()

if __name__ == '__main__':
    spade.run(main())