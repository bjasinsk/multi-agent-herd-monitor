import asyncio
import json
import spade
from spade.agent import Agent
from spade.message import Message
from spade.behaviour import CyclicBehaviour


class MapGeneratorBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=1)
        if msg and msg.metadata.get("protocol") == "ReceiveLatestState":
            print("[Role: MapGenerator] Received latestState.")

            latest_state = json.loads(msg.body)
            generated_map = self.generate_map(latest_state)
            print("[Role: MapGenerator] Generated map:", generated_map)

            reply = Message(
                to=str(self.agent.jid),
                metadata={"protocol": "SendMap"},
                body=json.dumps(generated_map)
            )
            await self.send(reply)
            print("[Role: MapGenerator] Sent generated map.")

    def calculate_cow_action(self, healthy_cow, infected_cows):
        pass

    
    def generate_map(self, state):
        print("[Role: MapGenerator] Generating map...")

        cows = state.get("cows", [])
        infected = state.get("infected", [])

        result = {
            "avoided_cows": infected,
            "cow_movement": []
        }

        for cow in cows:
            cid = cow["id"]
            if cid in infected:
                result["cow_movement"].append({"cow": cid, "action": "stay"})
            else:
                # cow_action = calculate_cow_action(cow, cow[y])
                result["cow_movement"].append({"cow": cid, "action": "TODO: calculate action"})

        return result


class CowAgent(Agent):
    async def setup(self):
        print("[CowAgent] Setup agent.")
        self.add_behaviour(MapGeneratorBehaviour())


async def main():
    agent = CowAgent("cow@localhost", "pass")
    await agent.start(auto_register=True)

    await asyncio.sleep(2)
    test_state = {
        "cows": [
            {"id": "1", "x": 10, "y": 3},
            {"id": "2", "x": 11, "y": 7},
            {"id": "3", "x": 17, "y": 3},
            {"id": "4", "x": 15, "y": 9},
        ],
        "infected": ["2"]
    }

    msg = Message(
        to=str(agent.jid),
        metadata={"protocol": "ReceiveLatestState"},
        body=json.dumps(test_state)
    )
    agent.dispatch(msg)
    print("[TEST] Sent test latestState")

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    spade.run(main())
