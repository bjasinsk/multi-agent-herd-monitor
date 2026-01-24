import json
import time

from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message

from aasd.agent_commons import Boundaries


class ShepherdAgent(Agent):
    def __init__(self, jid: str, password: str, boundaries: Boundaries, verbose_logging: bool = False) -> None:
        super().__init__(jid, password)
        self.boundaries = boundaries
        self.verbose_logging = verbose_logging

    class SendLatestGlobalBoundaries(OneShotBehaviour):
        async def run(self) -> None:
            lat_lon_list = [[y, x] for x, y in self.agent.boundaries.polygon.exterior.coords]

            msg = Message(
                to="cow1@localhost",
                metadata={
                    "performative": "inform",
                    "ontology": "global_boundaries",
                    "language": "json",
                },
                body=json.dumps(
                    {
                        "boundaries": lat_lon_list,
                        "timestamp": time.time(),
                        "sender": "Shepherd",
                    }
                ),
            )

            await self.send(msg)
            print("SHEPHERD: SendLatestGlobalBoundaries")
            if self.agent.verbose_logging:
                print("DEBUG: SHEPHERD: sending global boundaries ->", repr(lat_lon_list))

    async def setup(self) -> None:
        print("SHEPHERD: started")
        self.add_behaviour(self.SendLatestGlobalBoundaries())
