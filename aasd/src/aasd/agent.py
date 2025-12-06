from __future__ import annotations

import asyncio
import json
import random
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Self

from spade import agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message


class HealthStatus(Enum):
    """Health status of a cow"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class Boundaries(NamedTuple):
    """Geographic boundaries for cow movement"""

    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


class Location(NamedTuple):
    """Geographic location (latitude, longitude)"""

    latitude: float
    longitude: float


class CowState(NamedTuple):
    """State of a cow at a specific point in time"""

    location: Location
    health: HealthStatus
    boundaries: Boundaries
    timestamp: float
    peers: List[str]

    def to_json(self) -> Dict[str, Any]:
        """Convert a CowState object to dict for JSON serialization"""
        return {
            "location": {
                "latitude": self.location.latitude,
                "longitude": self.location.longitude,
            },
            "health": self.health.value,
            "boundaries": {
                "lat_min": self.boundaries.lat_min,
                "lat_max": self.boundaries.lat_max,
                "lon_min": self.boundaries.lon_min,
                "lon_max": self.boundaries.lon_max,
            },
            "timestamp": self.timestamp,
            "peers": self.peers,
        }

    @classmethod
    def from_json(cls, cow_data: Dict[str, Any]) -> Self:
        """Convert a dict to CowState object"""
        location_data = cow_data["location"]
        boundaries_data = cow_data["boundaries"]
        return cls(
            location=Location(location_data["latitude"], location_data["longitude"]),
            health=HealthStatus(cow_data["health"]),
            boundaries=Boundaries(
                boundaries_data["lat_min"],
                boundaries_data["lat_max"],
                boundaries_data["lon_min"],
                boundaries_data["lon_max"],
            ),
            timestamp=cow_data["timestamp"],
            peers=cow_data.get("peers", []),
        )


class CowAgent(agent.Agent):
    def __init__(
        self,
        jid: str,
        password: str,
        cow_id: str,
        boundaries: Boundaries,
        initial_location: Location,
        initial_health: HealthStatus,
        *,
        mutation_probability: float = 0.02,
        send_delay_seconds: float = 0.5,
        dump_state: bool = True,
    ) -> None:
        super().__init__(jid, password)
        self.cow_id: str = cow_id
        self.known_agents: List[str] = []
        self.boundaries: Boundaries = boundaries
        self.mutation_probability: float = mutation_probability
        self.send_delay_seconds: float = send_delay_seconds

        self.global_state: Dict[str, CowState] = {
            self.cow_id: CowState(
                location=initial_location,
                health=initial_health,
                boundaries=boundaries,
                timestamp=time.time(),
                peers=[],
            )
        }

        self.dump_state: bool = dump_state
        self.state_dump_dir: Path = Path("state")
        if dump_state:
            self.state_dump_dir.mkdir(exist_ok=True)

    @property
    def state(self) -> CowState:
        """Get current state of this cow from the state dict"""
        return self.global_state[self.cow_id]

    @property
    def location(self) -> Location:
        """Get current location of this cow"""
        return self.state.location

    def dump_state_to_file(self) -> None:
        """Dump current state to a JSON file"""
        state_file = self.state_dump_dir / f"{self.cow_id}.json"
        with open(state_file, "w") as f:
            json.dump(self.global_state_dict, f, indent=2)

    def add_peer(self, peer_jid: str) -> None:
        """Add a peer agent to broadcast to"""
        if peer_jid not in self.known_agents:
            self.known_agents.append(peer_jid)
            own_state = self.state
            self.global_state[self.cow_id] = CowState(
                location=own_state.location,
                health=own_state.health,
                boundaries=own_state.boundaries,
                timestamp=own_state.timestamp,
                peers=self.known_agents.copy(),
            )

    @property
    def global_state_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert internal CowState objects to dict for JSON serialization"""
        return {cow_id: cow_state.to_json() for cow_id, cow_state in self.global_state.items()}

    # Dummy to replace healthchecker, mapgenerator, etc - just make the state change by itself
    class MutateRole(CyclicBehaviour):
        agent: CowAgent

        async def run(self) -> None:
            await asyncio.sleep(1)

            if self.agent.known_agents and random.random() < self.agent.mutation_probability:
                self.mutate_random_property()

                if self.agent.dump_state:
                    self.agent.dump_state_to_file()

                state_message = {"state": self.agent.global_state_dict, "sender": self.agent.cow_id}

                for peer_jid in self.agent.known_agents:
                    msg = Message(to=peer_jid)
                    msg.set_metadata("performative", "inform")
                    msg.set_metadata("ontology", "cow_state")
                    msg.body = json.dumps(state_message)
                    await self.send(msg)

                own_state = self.agent.global_state[self.agent.cow_id]
                print(
                    f"{self.agent.cow_id:<7} UPDATED ({own_state.location.latitude:.5f}, {own_state.location.longitude:.5f}) {own_state.health.value}, propagate to {', '.join([p.split('@')[0] for p in self.agent.known_agents])}"
                )

        def mutate_random_property(self) -> None:
            """Randomly mutate one of cow's properties"""
            property_choice = random.choices(["location", "health"], weights=[0.9, 0.1])[0]

            own_state = self.agent.state

            if property_choice == "location":
                lat_max_delta = (self.agent.boundaries.lat_max - self.agent.boundaries.lat_min) * 0.1
                lon_max_delta = (self.agent.boundaries.lon_max - self.agent.boundaries.lon_min) * 0.1
                lat = random.uniform(
                    own_state.location.latitude - lat_max_delta, own_state.location.latitude + lat_max_delta
                )
                lon = random.uniform(
                    own_state.location.longitude - lon_max_delta, own_state.location.longitude + lon_max_delta
                )
                new_location = Location(lat, lon)
                new_health = own_state.health
            elif property_choice == "health":
                new_health = (
                    HealthStatus.HEALTHY if own_state.health == HealthStatus.UNHEALTHY else HealthStatus.UNHEALTHY
                )
                new_location = own_state.location

            self.agent.global_state[self.agent.cow_id] = CowState(
                location=new_location,
                health=new_health,
                boundaries=own_state.boundaries,
                timestamp=time.time(),
                peers=self.agent.known_agents.copy(),
            )

    class InterCowCommunicatorRole(CyclicBehaviour):
        agent: CowAgent

        async def run(self) -> None:
            msg = await self.receive(timeout=1)
            if msg and msg.get_metadata("ontology") == "cow_state":
                try:
                    data = json.loads(msg.body)
                    received_state = data["state"]
                    sender_id = data["sender"]

                    state_changed = self.consolidate_state(received_state)

                    if state_changed and self.agent.dump_state:
                        self.agent.dump_state_to_file()

                    if state_changed:
                        outbound_peers = [p for p in self.agent.known_agents if p != str(msg.sender).split("/")[0]]

                        if outbound_peers:
                            print(
                                f"{self.agent.cow_id:<7} Received update from {sender_id:<7}, propagate to {', '.join([p.split('@')[0] for p in outbound_peers])}"
                            )
                            await asyncio.sleep(self.agent.send_delay_seconds)
                            state_message = {"state": self.agent.global_state_dict, "sender": self.agent.cow_id}

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

        def consolidate_state(self, received_state: Dict[str, Dict[str, Any]]) -> bool:
            """
            Consolidate received state with current state based on timestamps.
            Returns True if state changed.
            """
            state_changed = False

            for cow_id, cow_data in received_state.items():
                if cow_id == self.agent.cow_id:
                    continue

                received_cow_state = CowState.from_json(cow_data)

                if cow_id not in self.agent.global_state:
                    self.agent.global_state[cow_id] = received_cow_state
                    state_changed = True
                else:
                    if received_cow_state.timestamp > self.agent.global_state[cow_id].timestamp:
                        self.agent.global_state[cow_id] = received_cow_state
                        state_changed = True

            return state_changed

    async def setup(self) -> None:
        own_state = self.state
        print(f"{self.cow_id} starting:")
        print(f"  Location: {own_state.location}")
        print(f"  Health: {own_state.health.value}")
        print(f"  Boundaries: {own_state.boundaries}")

        # Dump initial state
        if self.dump_state:
            self.dump_state_to_file()

        self.add_behaviour(self.MutateRole())
        self.add_behaviour(self.InterCowCommunicatorRole())
