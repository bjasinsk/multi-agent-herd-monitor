import json
import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

import asyncio
import matplotlib.pyplot as plt

from common import Boundaries


class PlotterAgent(Agent):
    class PlotBehaviour(CyclicBehaviour):
        async def on_start(self):
            print("PLOTTER: Waiting for boundaries...")

            # Initialize live plot
            # plt.ion()
            # self.fig, self.ax = plt.subplots(figsize=(5, 5))
            # (self.line,) = self.ax.plot([], [], "-o")
            # plt.title("Live Boundaries")
            # plt.xlabel("X")
            # plt.ylabel("Y")
            # self.ax.set_xlim(-1, 2)
            # self.ax.set_ylim(-1, 2)

            print("PLOTTER: Finished setup")

        async def run(self):
            msg = await self.receive(timeout=5)
            print("PLOTTER: Run entry")
            if msg:
                print("PLOTTER: Received boundaries")

                # Deserialize JSON
                data = json.loads(msg.body)
                bounds = Boundaries.from_dict(data)
                print(bounds)

                # xs = [
                #     bounds.top_left.x,
                #     bounds.top_right.x,
                #     bounds.bottom_right.x,
                #     bounds.bottom_left.x,
                #     bounds.top_left.x,
                # ]
                # ys = [
                #     bounds.top_left.y,
                #     bounds.top_right.y,
                #     bounds.bottom_right.y,
                #     bounds.bottom_left.y,
                #     bounds.top_left.y,
                # ]

                # # Update plot
                # self.line.set_xdata(xs)
                # self.line.set_ydata(ys)
                # self.ax.relim()
                # self.ax.autoscale_view()
                # self.fig.canvas.draw()
                # self.fig.canvas.flush_events()

            await asyncio.sleep(0.1)

    async def setup(self):
        print("PLOTTER: Started")
        behav = self.PlotBehaviour()
        self.add_behaviour(behav)


async def main():
    agent = PlotterAgent("cow@localhost", "password")
    await agent.start(auto_register=True)

    await spade.wait_until_finished(agent)


if __name__ == "__main__":
    spade.run(main())
