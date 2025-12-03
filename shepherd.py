import json
import spade
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour, CyclicBehaviour
from spade.message import Message
from spade.template import Template

import random
import asyncio

from common import Coords, Boundaries, to_dict


BASE_BOUNDARIES = Boundaries(
    top_right=Coords(1, 1),
    bottom_right=Coords(1, 0),
    top_left=Coords(0, 1),
    bottom_left=Coords(0, 0),
)
JITTER_SCALE = 0.1
MESSAGE_INTERVAL = 3  # s


class Shepherd(Agent):
    @staticmethod
    def think_of_boundaries() -> Boundaries:
        global BASE_BOUNDARIES, JITTER_SCALE

        def jitter(coord: Coords) -> Coords:
            return Coords(
                coord.x + random.uniform(-JITTER_SCALE, JITTER_SCALE),
                coord.y + random.uniform(-JITTER_SCALE, JITTER_SCALE),
            )

        return Boundaries(
            top_right=jitter(BASE_BOUNDARIES.top_right),
            bottom_right=jitter(BASE_BOUNDARIES.bottom_right),
            top_left=jitter(BASE_BOUNDARIES.top_left),
            bottom_left=jitter(BASE_BOUNDARIES.bottom_left),
        )

    class UpdateBoundariesBehav(CyclicBehaviour):
        async def on_start(self):
            print("SHEPHERD: Started sending")

        async def run(self):
            msg = Message(to="cow@localhost")
            msg.body = json.dumps(to_dict(Shepherd.think_of_boundaries()))

            await self.send(msg)
            print("SHEPHERD: Sent boundaries")
            await asyncio.sleep(MESSAGE_INTERVAL)

    async def setup(self):
        print("SHEPHERD: Started")
        behav = self.UpdateBoundariesBehav()
        self.add_behaviour(behav)


async def main():
    agent = Shepherd("shepherd@localhost", "password")
    await agent.start(auto_register=True)

    await spade.wait_until_finished(agent)


if __name__ == "__main__":
    spade.run(main())
