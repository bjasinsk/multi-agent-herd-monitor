import json
import time

from shapely.geometry import Polygon
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message

from aasd.agent import Boundaries


class ShepherdAgent(Agent):
    def __init__(self, jid: str, password: str, boundaries: Boundaries) -> None:
        super().__init__(jid, password)
        self.boundaries = boundaries

    @staticmethod
    def think_of_boundaries() -> Boundaries:
        """
        Defines global movement boundaries for the herd.
        """
        return Boundaries(
            Polygon(
                [
                    (20.455, 52.115),
                    (20.445, 52.125),
                    (20.455, 52.135),
                    (20.495, 52.135),
                    (20.495, 52.115),
                ]
            )
        )

    class SendLatestGlobalBoundaries(OneShotBehaviour):
        async def run(self) -> None:
            # boundaries = ShepherdAgent.think_of_boundaries()
            boundaries = self.agent.boundaries
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
            print("DEBUG: SHEPHERD: sending global boundaries ->", boundaries)

    async def setup(self) -> None:
        print("SHEPHERD: started")
        self.add_behaviour(self.SendLatestGlobalBoundaries())
