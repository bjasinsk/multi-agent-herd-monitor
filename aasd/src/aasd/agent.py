import asyncio
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from spade import agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message


class CowAgent(agent.Agent):
    def __init__(self, jid: str, password: str, cow_id: str, boundaries: Tuple[float, float, float, float]) -> None:
        super().__init__(jid, password)
        self.cow_id: str = cow_id
        self.known_agents: List[str] = []  # List of other agents to broadcast to
        self.boundaries: Tuple[float, float, float, float] = boundaries  # (lat_min, lat_max, lon_min, lon_max)

        # Initialize own properties
        self.location: Tuple[float, float] = self._random_location()
        self.health: str = random.choice(["healthy", "unhealthy"])
        self.timestamp: float = time.time()

        # State: knowledge about all cows (including self)
        self.state: Dict[str, Any] = {self.cow_id: self._get_own_state()}

        # Setup state directory
        self.state_dir: Path = Path("state")
        self.state_dir.mkdir(exist_ok=True)

    def _random_location(self) -> Tuple[float, float]:
        """Generate random location within boundaries"""
        lat_min, lat_max, lon_min, lon_max = self.boundaries
        lat = random.uniform(lat_min, lat_max)
        lon = random.uniform(lon_min, lon_max)
        return (lat, lon)

    def _mutate_location(self) -> Tuple[float, float]:
        """Generate random location within boundaries"""
        lat_curr, lon_curr = self.location
        lat_min, lat_max, lon_min, lon_max = self.boundaries
        lat_max_delta = (lat_max - lat_min) * 0.1
        lon_max_delta = (lon_max - lon_min) * 0.1
        lat = random.uniform(lat_curr - lat_max_delta, lat_curr + lat_max_delta)
        lon = random.uniform(lon_curr - lon_max_delta, lon_curr + lon_max_delta)
        return (lat, lon)

    def _get_own_state(self) -> Dict[str, Any]:
        """Get current state of this cow"""
        return {
            "location": self.location,
            "health": self.health,
            "boundaries": self.boundaries,
            "timestamp": self.timestamp,
        }

    def dump_state_to_file(self) -> None:
        """Dump current state to a JSON file"""
        state_file = self.state_dir / f"{self.cow_id}.json"
        with open(state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def add_peer(self, peer_jid: str) -> None:
        """Add a peer agent to broadcast to"""
        if peer_jid not in self.known_agents:
            self.known_agents.append(peer_jid)

    def mutate_property(self) -> None:
        """Randomly mutate one of cow's properties"""
        property_choice = random.choice(["location", "health"])

        if property_choice == "location":
            self.location = self._mutate_location()
        elif property_choice == "health":
            self.health = random.choice(["healthy", "unhealthy"])

        self.timestamp = time.time()
        self.state[self.cow_id] = self._get_own_state()

    def consolidate_state(self, received_state: Dict[str, Dict[str, Any]]) -> bool:
        """
        Consolidate received state with current state based on timestamps.
        Returns True if state changed.
        """
        state_changed = False

        for cow_id, cow_data in received_state.items():
            # Never update own properties
            if cow_id == self.cow_id:
                continue

            # If we don't know about this cow, add it
            if cow_id not in self.state:
                self.state[cow_id] = cow_data
                state_changed = True
            else:
                # Compare timestamps - newer wins
                if cow_data["timestamp"] > self.state[cow_id]["timestamp"]:
                    self.state[cow_id] = cow_data
                    state_changed = True

        return state_changed

    class BroadcastBehaviour(CyclicBehaviour):
        async def run(self) -> None:
            # Wait random interval between 5-10 seconds
            await asyncio.sleep(random.uniform(5, 10))

            if self.agent.known_agents:
                # Randomly mutate a property
                self.agent.mutate_property()

                # Dump state to file
                self.agent.dump_state_to_file()

                # Broadcast current state to all peers
                state_message = {"state": self.agent.state, "sender": self.agent.cow_id}

                for peer_jid in self.agent.known_agents:
                    msg = Message(to=peer_jid)
                    msg.set_metadata("performative", "inform")
                    msg.set_metadata("ontology", "cow_state")
                    msg.body = json.dumps(state_message)
                    await self.send(msg)

                own_state = self.agent.state[self.agent.cow_id]
                print(
                    f"Cow {self.agent.cow_id}: Updated property - Location: {own_state['location']}, Health: {own_state['health']}"
                )

    class ListenBehaviour(CyclicBehaviour):
        async def run(self) -> None:
            # Listen for state broadcasts from other cows
            msg = await self.receive(timeout=1)
            if msg and msg.get_metadata("ontology") == "cow_state":
                try:
                    data = json.loads(msg.body)
                    received_state = data["state"]
                    sender_id = data["sender"]

                    # Consolidate received state with current state
                    state_changed = self.agent.consolidate_state(received_state)

                    if state_changed:
                        # Dump updated state to file
                        self.agent.dump_state_to_file()

                    print(f"Cow {self.agent.cow_id}: Received state from Cow {sender_id}")

                    # If state changed, propagate to other peers
                    if state_changed and random.random() < 0.5:
                        print(f"Cow {self.agent.cow_id}: State updated, propagating to peers")

                        # Broadcast updated state to all peers
                        await asyncio.sleep(0.5)
                        state_message = {"state": self.agent.state, "sender": self.agent.cow_id}

                        for peer_jid in self.agent.known_agents:
                            # Don't send back to the sender
                            if peer_jid != str(msg.sender).split("/")[0]:
                                propagate_msg = Message(to=peer_jid)
                                propagate_msg.set_metadata("performative", "inform")
                                propagate_msg.set_metadata("ontology", "cow_state")
                                propagate_msg.body = json.dumps(state_message)
                                await self.send(propagate_msg)

                except json.JSONDecodeError:
                    print(f"Cow {self.agent.cow_id}: Received malformed message")

    async def setup(self) -> None:
        print(f"Cow {self.cow_id} starting:")
        print(f"  Location: {self.location}")
        print(f"  Health: {self.health}")
        print(f"  Boundaries: {self.boundaries}")

        # Dump initial state
        self.dump_state_to_file()

        self.add_behaviour(self.BroadcastBehaviour())
        self.add_behaviour(self.ListenBehaviour())
