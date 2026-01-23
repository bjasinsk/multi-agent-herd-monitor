from __future__ import annotations

import asyncio
import json
import math
import random
import time
from functools import partial
from pathlib import Path
from typing import Any, Callable

from spade import agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message
from spade.template import Template

from aasd.agent_commons import Boundaries, CowState, HealthStatus, Location, MovementMap
from aasd.map_commons import (
    check_cow_position,
    check_global_boundaries,
    check_infected_radius,
    move_towards_box,
    rotate_direction_vector,
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
        get_peer_jids_in_range_fn: Callable[[str], list[str]],
        *,
        mutation_probability: float = 0.02,
        send_delay_seconds: float = 0.5,
        dump_state: bool = True,
    ) -> None:
        super().__init__(jid, password)
        self.cow_id: str = cow_id
        self.known_agents: list[str] = []
        self.boundaries: Boundaries = boundaries
        self.mutation_probability: float = mutation_probability
        self.send_delay_seconds: float = send_delay_seconds

        self.global_state: dict[str, CowState] = {
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

        self.get_peer_jids_in_range = partial(get_peer_jids_in_range_fn, self.cow_id)

        self.state_needs_broadcast_event = asyncio.Event()

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

    def add_peer(self, peer_jid: str) -> bool:
        if peer_jid in self.known_agents:
            return False

        self.known_agents.append(peer_jid)
        own_state = self.state
        self.global_state[self.cow_id] = CowState(
            location=own_state.location,
            health=own_state.health,
            boundaries=own_state.boundaries,
            timestamp=own_state.timestamp,
            peers=self.known_agents.copy(),
        )
        return True

    def remove_peer(self, peer_jid: str) -> bool:
        if peer_jid not in self.known_agents:
            return False

        self.known_agents.remove(peer_jid)
        own_state = self.state
        self.global_state[self.cow_id] = CowState(
            location=own_state.location,
            health=own_state.health,
            boundaries=own_state.boundaries,
            timestamp=own_state.timestamp,
            peers=self.known_agents.copy(),
        )
        return True

    @property
    def global_state_dict(self) -> dict[str, dict[str, Any]]:
        """Convert internal CowState objects to dict for JSON serialization"""
        return {cow_id: cow_state.to_json() for cow_id, cow_state in self.global_state.items()}

    def generate_map(self) -> MovementMap:
        infected_areas: list[tuple[Location, float]] = []

        for cow_id, cow in self.global_state.items():
            if cow.health == HealthStatus.UNHEALTHY:
                infected_areas.append((cow.location, 300.0))

        return MovementMap(
            boundaries=self.state.boundaries,
            infected_areas=infected_areas,
        )

    class ReceiveGlobalBoundariesBehaviour(CyclicBehaviour):
        agent: CowAgent

        async def run(self) -> None:
            msg = await self.receive(timeout=1)
            if not msg:
                return

            print(f"DEBUG: [{self.agent.cow_id}] RECEIVED GLOBAL BOUNDARIES MESSAGE", msg.body)

            try:
                data = json.loads(msg.body)
            except json.JSONDecodeError:
                return

            boundaries_data = data.get("boundaries")
            timestamp = data.get("timestamp")

            if not boundaries_data:
                return

            new_boundaries = Boundaries(
                lat_min=boundaries_data["lat_min"],
                lat_max=boundaries_data["lat_max"],
                lon_min=boundaries_data["lon_min"],
                lon_max=boundaries_data["lon_max"],
            )

            own_state = self.agent.state

            if timestamp > own_state.timestamp:
                self.agent.boundaries = new_boundaries
                print(f"DEBUG: [{self.agent.cow_id}] UPDATED boundaries:", new_boundaries)
                self.agent.global_state[self.agent.cow_id] = CowState(
                    location=own_state.location,
                    health=own_state.health,
                    boundaries=new_boundaries,
                    timestamp=timestamp,
                    peers=self.agent.known_agents.copy(),
                )

                print(f"{self.agent.cow_id} UPDATED GLOBAL BOUNDARIES FROM SHEPHERD")
                self.agent.state_needs_broadcast_event.set()

    class CowPositionLocalizerBehaviour(PeriodicBehaviour):
        agent: CowAgent

        async def run(self) -> None:
            movement_map = self.agent.generate_map()

            if not check_cow_position(self.agent.state, movement_map):
                self.agent.guide_cow(movement_map)

        def guide_cow(self, movement_map: MovementMap, step: float = 0.0001) -> None:
            actual_location = self.agent.state.location
            actual_boundaries = movement_map.boundaries

            # Check boundaries
            if not check_global_boundaries(actual_location, actual_boundaries):
                new_location = move_towards_box(actual_location, actual_boundaries, step)

                self.agent.global_state[self.agent.cow_id] = CowState(
                    location=new_location,
                    health=self.agent.state.health,
                    boundaries=actual_boundaries,
                    timestamp=time.time(),
                    peers=self.agent.known_agents.copy(),
                )
                return

            # Avoid infected radius (also applies to infected cows, but not from "itself")
            in_infected_radius = check_infected_radius(self.agent.state, actual_location, movement_map)
            if in_infected_radius is not None:
                infected_location, avoid_radius = in_infected_radius

                new_location = self.avoid_infection(
                    actual_location,
                    infected_location,
                    actual_boundaries,
                )

                self.agent.global_state[self.agent.cow_id] = CowState(
                    location=new_location,
                    health=self.agent.state.health,
                    boundaries=actual_boundaries,
                    timestamp=time.time(),
                    peers=self.agent.known_agents.copy(),
                )
                return

        def avoid_infection(
            self,
            location: Location,
            infected_location: Location,
            boundaries: Boundaries,
            *,
            step_degrees: float = 0.0001,
            rotation_step: float = 30.0,
            max_retries: int = 12,
        ) -> Location:
            # vector from infected -> cow (in degrees)
            vector_lat = location.latitude - infected_location.latitude
            vector_lon = location.longitude - infected_location.longitude

            length = math.sqrt(vector_lat * vector_lat + vector_lon * vector_lon)
            if length == 0.0:
                vector_lat, vector_lon = 1.0, 0.0
                length = 1.0

            direction_lat = vector_lat / length
            direction_lon = vector_lon / length

            for i in range(max_retries):
                angle = i * rotation_step
                new_dir_lat, new_dir_lon = rotate_direction_vector(direction_lat, direction_lon, angle)

                new_location = Location(
                    location.latitude + new_dir_lat * step_degrees,
                    location.longitude + new_dir_lon * step_degrees,
                )

                if check_global_boundaries(new_location, boundaries):
                    return new_location

            return move_towards_box(location, boundaries, step=step_degrees)

    # Dummy to replace healthchecker, mapgenerator, etc - just make the state change by itself
    class CowHealthChecker(PeriodicBehaviour):
        agent: CowAgent

        async def run(self) -> None:
            if not self.agent.known_agents or random.random() > self.agent.mutation_probability:
                return

            self.mutate_random_property()

            own_state = self.agent.global_state[self.agent.cow_id]
            print(
                f"{self.agent.cow_id:<7} UPDATED ({own_state.location.latitude:.5f}, {own_state.location.longitude:.5f}) {own_state.health.value}"
            )

            self.agent.state_needs_broadcast_event.set()

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

    class ReceiveStateUpdateBehaviour(CyclicBehaviour):
        agent: CowAgent

        async def run(self) -> None:
            msg = await self.receive(timeout=1)

            if not msg:
                return

            try:
                data = json.loads(msg.body)
            except json.JSONDecodeError:
                print(f"Cow {self.agent.cow_id:<7} Received malformed message")

            received_state = data["state"]
            sender_id = data["sender"]

            state_changed = self.consolidate_state(received_state)

            if not state_changed:
                print(f"{self.agent.cow_id:<7} Received null-update from {sender_id}, not propagating")
                return

            print(f"{self.agent.cow_id:<7} Received update from {sender_id:<7}")

            self.agent.state_needs_broadcast_event.set()

        def consolidate_state(self, received_state: dict[str, dict[str, Any]]) -> bool:
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

    class BroadcastStateBehaviour(CyclicBehaviour):
        agent: CowAgent

        async def run(self) -> None:
            await self.agent.state_needs_broadcast_event.wait()

            print(
                f"{self.agent.cow_id:<7} Propagate state change to {', '.join([p.split('@')[0] for p in self.agent.known_agents])}"
            )

            if self.agent.dump_state:
                self.agent.dump_state_to_file()

            await asyncio.sleep(self.agent.send_delay_seconds)

            self.agent.state_needs_broadcast_event.clear()

            msg_metadata = {"performative": "inform", "ontology": "cow_state", "language": "json"}

            msg_body = json.dumps(
                {
                    "state": self.agent.global_state_dict,
                    "sender": self.agent.cow_id,
                }
            )

            # MOCK: remove subscribers that are out of range
            for subscriber in set(self.agent.known_agents) - set(self.agent.get_peer_jids_in_range()):
                self.agent.remove_peer(subscriber)
                print(f"{self.agent.cow_id:<7} Removed subscriber {subscriber}")

            for peer_jid in self.agent.known_agents:
                print(f"DEBUG: [{self.agent.cow_id}] PROPAGATING STATE to peer:", peer_jid)
                msg = Message(to=peer_jid, sender=self.agent.jid, metadata=msg_metadata, body=msg_body)
                asyncio.create_task(self.send(msg))

    class SubscribeToPeerUpdatesBehaviour(PeriodicBehaviour):
        agent: CowAgent

        async def run(self) -> None:
            msg_metadata = {"performative": "subscribe", "ontology": "cow_state", "language": "json"}
            msg_body = json.dumps(
                {
                    "sender": self.agent.cow_id,
                }
            )

            # MOCK: subscribe to all peers in range
            for peer_jid in self.agent.get_peer_jids_in_range():
                msg = Message(to=peer_jid, sender=self.agent.jid, metadata=msg_metadata, body=msg_body)
                asyncio.create_task(self.send(msg))

    class HandleSubscriptionsBehaviour(CyclicBehaviour):
        agent: CowAgent

        async def run(self) -> None:
            msg = await self.receive(timeout=1)

            if not msg:
                return

            print(f"[{self.agent.cow_id}] RECEIVED STATE FROM PEER:", msg.sender)

            subscriber_jid = msg.sender

            if not self.agent.add_peer(str(subscriber_jid)):
                return

            print(f"{self.agent.cow_id:<7} Added subscriber {str(subscriber_jid)}")

    async def setup(self) -> None:
        own_state = self.state
        print(f"{self.cow_id} starting:")
        print(f"  Location: {own_state.location}")
        print(f"  Health: {own_state.health.value}")
        print(f"  Boundaries: {own_state.boundaries}")

        # Dump initial state
        if self.dump_state:
            self.dump_state_to_file()

        self.add_behaviour(self.CowHealthChecker(period=1.0))

        self.add_behaviour(self.BroadcastStateBehaviour())

        state_broadcast_template = Template()
        state_broadcast_template.set_metadata("ontology", "cow_state")
        state_broadcast_template.set_metadata("performative", "inform")
        self.add_behaviour(self.ReceiveStateUpdateBehaviour(), template=state_broadcast_template)

        self.add_behaviour(self.SubscribeToPeerUpdatesBehaviour(period=10.0))

        subscription_template = Template()
        subscription_template.set_metadata("ontology", "cow_state")
        subscription_template.set_metadata("performative", "subscribe")
        self.add_behaviour(self.HandleSubscriptionsBehaviour(), template=subscription_template)

        boundary_template = Template()
        boundary_template.set_metadata("ontology", "global_boundaries")
        boundary_template.set_metadata("performative", "inform")
        self.add_behaviour(self.ReceiveGlobalBoundariesBehaviour(), template=boundary_template)
        self.add_behaviour(self.CowPositionLocalizerBehaviour(period=1.0))
