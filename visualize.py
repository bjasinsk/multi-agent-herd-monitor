#!/usr/bin/env python3
"""
Real-time visualization of cow herd tracking system
"""

import asyncio
import spade
from agent import CowAgent
import time
import os


class CowVisualizer:
    """Real-time visualizer for cow herd state"""
    
    def __init__(self, cows):
        self.cows = cows
        self.start_time = time.time()
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name != 'nt' else 'cls')
        
    def format_location(self, location):
        """Format location tuple to string"""
        lat, lon = location
        return f"({lat:.4f}, {lon:.4f})"
    
    def format_health(self, health):
        """Format health with color"""
        if health == 'healthy':
            return f"\033[92m{health}\033[0m"  # Green
        else:
            return f"\033[91m{health}\033[0m"  # Red
    
    def get_border_char(self, lat, lon, boundaries):
        """Check if location is near boundary"""
        lat_min, lat_max, lon_min, lon_max = boundaries
        margin = 0.1
        
        if lat < lat_min + margin or lat > lat_max - margin:
            return "⚠️"
        if lon < lon_min + margin or lon > lon_max - margin:
            return "⚠️"
        return "✓"
    
    def display(self):
        """Display current state of all cows"""
        self.clear_screen()
        
        elapsed = time.time() - self.start_time
        
        print("="*80)
        print(f"🐄 COW HERD TRACKING SYSTEM - Real-Time Visualization")
        print(f"Runtime: {elapsed:.1f}s | Cows: {len(self.cows)}")
        print("="*80)
        print()
        
        # Display each cow's state
        for cow in self.cows:
            print(f"🐄 {cow.cow_id} {self.format_health(cow.health)} Updated:  {time.time() - cow.timestamp:.1f}s ago")
            print(f"   Location: {self.format_location(cow.location)} {self.get_border_char(cow.location[0], cow.location[1], cow.boundaries)}")
        
        print("-"*80)
        print("KNOWLEDGE MATRIX (what each cow knows about others)")
        print("-"*80)
        
        # Create knowledge matrix header
        cow_ids = [cow.cow_id for cow in self.cows]
        print(f"{'':12}", end="")
        for cow_id in cow_ids:
            print(f"{cow_id:12}", end="")
        print()
        
        # Display knowledge matrix
        for cow in self.cows:
            print(f"{cow.cow_id:12}", end="")
            for target_id in cow_ids:
                if target_id in cow.state:
                    state_data = cow.state[target_id]
                    age = time.time() - state_data['timestamp']
                    
                    if target_id == cow.cow_id:
                        print(f"{'[SELF]':12}", end="")
                    else:
                        # Find the actual cow to compare with
                        actual_cow = next((c for c in self.cows if c.cow_id == target_id), None)
                        if actual_cow:
                            # Check if the known state matches the actual current state
                            # Compare timestamp - if they match, the state is up to date
                            is_up_to_date = abs(state_data['timestamp'] - actual_cow.timestamp) < 0.0001
                            
                            if is_up_to_date:
                                print(f"\033[92m{age:.1f}s\033[0m      ", end="")  # Green - up to date
                            else:
                                print(f"\033[91m{age:.1f}s\033[0m      ", end="")  # Red - outdated
                        else:
                            print(f"{age:.1f}s      ", end="")  # No color if cow not found
                else:
                    print(f"{'UNKNOWN':12}", end="")
            print()
        
        print()
        print("-"*80)
        print("HEALTH SUMMARY")
        print("-"*80)
        
        # Count health status
        healthy_count = sum(1 for cow in self.cows if cow.health == 'healthy')
        unhealthy_count = len(self.cows) - healthy_count
        
        print(f"Healthy:   \033[92m{healthy_count}\033[0m")
        print(f"Unhealthy: \033[91m{unhealthy_count}\033[0m")
        
        print()
        print("="*80)
        print("Legend: ✓ = Within boundaries | ⚠️  = Near boundary | [SELF] = Own data")
        print("Knowledge: \033[92mGreen\033[0m = Up to date (matches current state) | \033[91mRed\033[0m = Outdated (state has changed)")
        print("Press Ctrl+C to stop...")
        print("="*80)


async def main():
    """Run visualization with cow agents"""
    print("Starting cow herd tracking system with visualization...")
    
    # Define boundaries for the virtual fence (lat_min, lat_max, lon_min, lon_max)
    boundaries = (50.0, 52.0, 19.0, 21.0)  # Example area in Poland
    
    # Create cow agents
    num_cows = 6
    cows = []
    
    for i in range(1, num_cows + 1):
        cow = CowAgent(f'cow{i}@localhost', 'password', f'Cow-{i}', boundaries)
        cows.append(cow)
    
    # Set up peer relationships (full mesh - all cows know each other)
    for i, cow in enumerate(cows):
        for j, other_cow in enumerate(cows):
            if i != j:
                cow.add_peer(f'cow{j+1}@localhost')
    
    # Start all cows
    for cow in cows:
        await cow.start()
    
    print(f"\nAll {num_cows} cows started.")
    print("Starting visualization in 2 seconds...")
    await asyncio.sleep(2)
    
    # Create visualizer
    visualizer = CowVisualizer(cows)
    
    try:
        # Update display every second
        while True:
            visualizer.display()
            await asyncio.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nStopping cow tracking system...")
        for cow in cows:
            await cow.stop()
        print("Visualization stopped.")


if __name__ == '__main__':
    spade.run(main())
