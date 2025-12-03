# AASD-25Z-WBDT - SPADE Stateful Agents

This project demonstrates SPADE agents with internal state that can broadcast their state to other agents of the same kind.

## Features

- **StatefulAgent**: A SPADE agent with internal integer state
- **State Broadcasting**: Agents periodically broadcast their state to peer agents
- **State Updates**: Internal state changes over time (simulating some process)
- **Multi-Agent Communication**: Support for networks of multiple communicating agents

## Files

- `agent.py` - Main agent implementations including StatefulAgent
- `main.py` - Simple example of running stateful agents
- `examples.py` - More comprehensive examples and usage patterns
- `requirements.txt` - Python dependencies

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the simple example:
```bash
python main.py
```

3. Run comprehensive examples:
```bash
python examples.py
```

## StatefulAgent Class

The `StatefulAgent` class provides:

- **Internal State**: An integer variable that represents the agent's state
- **State Broadcasting**: Periodic broadcasting of state to known peer agents  
- **Peer Management**: Methods to add peer agents for communication
- **State Listening**: Receives and processes state broadcasts from other agents

### Usage Example

```python
# Create agents
agent1 = StatefulAgent('agent1@localhost', 'password', 1)
agent2 = StatefulAgent('agent2@localhost', 'password', 2)

# Set up peer relationships
agent1.add_peer('agent2@localhost')
agent2.add_peer('agent1@localhost')

# Start agents
await agent1.start()
await agent2.start()
```

## How It Works

1. Each agent starts with a random integer state (1-100)
2. Every 3 seconds, agents broadcast their current state to all known peers
3. Agents also listen for broadcasts from other agents
4. The internal state changes over time (±5 random adjustment each broadcast)
5. All communication uses JSON messages with XMPP protocol via SPADE

## Architecture

- **BroadcastBehaviour**: Cyclical behavior that updates and broadcasts agent state
- **ListenBehaviour**: Cyclical behavior that receives state broadcasts from peers
- **Peer Management**: Simple list-based tracking of known agent JIDs

## Integrate with your tools

- [ ] [Set up project integrations](https://gitlab-stud.elka.pw.edu.pl/bjasinsk/aasd-25z-wbdt/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
