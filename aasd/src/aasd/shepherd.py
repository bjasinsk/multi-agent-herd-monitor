import json
import time

from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message

from aasd.agent import Boundaries


class ShepherdAgent(Agent):
    @staticmethod
    def think_of_boundaries() -> Boundaries:
        """
        Defines global movement boundaries for the herd.
        """
        return Boundaries(
            lat_min=52.115,
            lat_max=52.135,
            lon_min=20.455,
            lon_max=20.495,
        )

    class SendLatestGlobalBoundaries(OneShotBehaviour):
        async def run(self) -> None:
            boundaries = ShepherdAgent.think_of_boundaries()

            msg = Message(
                to="cow1@localhost",
                metadata={
                    "performative": "inform",
                    "ontology": "global_boundaries",
                    "language": "json",
                },
                body=json.dumps(
                    {
                        "boundaries": {
                            "lat_min": boundaries.lat_min,
                            "lat_max": boundaries.lat_max,
                            "lon_min": boundaries.lon_min,
                            "lon_max": boundaries.lon_max,
                        },
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
