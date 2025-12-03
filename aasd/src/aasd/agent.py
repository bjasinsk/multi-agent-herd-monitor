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
    def __init__(
        self,
        jid: str,
        password: str,
        cow_id: str,
        boundaries: Tuple[float, float, float, float],
        *,
        mutation_probability: float = 0.02,
        send_delay_seconds: float = 0.5,
    ) -> None:
        super().__init__(jid, password)
        self.cow_id: str = cow_id
        self.known_agents: List[str] = []  # List of other agents to broadcast to
        self.boundaries: Tuple[float, float, float, float] = boundaries  # (lat_min, lat_max, lon_min, lon_max)
        self.mutation_probability: float = mutation_probability
        self.send_delay_seconds: float = send_delay_seconds
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
            "peers": self.known_agents,  # Add peer list to state
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
        property_choice = random.choices(["location", "health"], weights=[0.9, 0.1])[0]

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
            await asyncio.sleep(1)

            if self.agent.known_agents and random.random() < self.agent.mutation_probability:
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
                    f"{self.agent.cow_id:<7} UPDATED ({own_state['location'][0]:.5f}, {own_state['location'][1]:.5f}) {own_state['health']}, propagate to {', '.join([p.split('@')[0] for p in self.agent.known_agents])}"
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

                    # If state changed, propagate to other peers
                    if state_changed:
                        outbound_peers = [p for p in self.agent.known_agents if p != str(msg.sender).split("/")[0]]

                        if outbound_peers:
                            print(
                                f"{self.agent.cow_id:<7} Received update from {sender_id:<7}, propagate to {', '.join([p.split('@')[0] for p in outbound_peers])}"
                            )
                            await asyncio.sleep(self.agent.send_delay_seconds)
                            state_message = {"state": self.agent.state, "sender": self.agent.cow_id}

                            for peer_jid in outbound_peers:
                                propagate_msg = Message(to=peer_jid)
                                propagate_msg.set_metadata("performative", "inform")
                                propagate_msg.set_metadata("ontology", "cow_state")
                                propagate_msg.body = json.dumps(state_message)
                                await self.send(propagate_msg)
                        else:
                            print(f"{self.agent.cow_id:<7} Received update from {sender_id:<7}, nowhere to propagate")
                    else:
                        print(f"{self.agent.cow_id:<7} Received null-update from {sender_id}, not propagating")

                except json.JSONDecodeError:
                    print(f"Cow {self.agent.cow_id:<7} Received malformed message")

    async def setup(self) -> None:
        print(f"{self.cow_id} starting:")
        print(f"  Location: {self.location}")
        print(f"  Health: {self.health}")
        print(f"  Boundaries: {self.boundaries}")

        # Dump initial state
        self.dump_state_to_file()

        self.add_behaviour(self.BroadcastBehaviour())
        self.add_behaviour(self.ListenBehaviour())
