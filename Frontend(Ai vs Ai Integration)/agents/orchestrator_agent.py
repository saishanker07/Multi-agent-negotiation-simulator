class OrchestratorAgent:
    """
    Orchestrator Agent for the Real Estate Negotiation Simulator.

    Responsibilities:
    1. Manage turn order
    2. Store negotiation history
    3. Track current negotiation state
    4. Track negotiation rounds
    """

    def __init__(self, agents):
        self.agents = agents

        # Index of the agent whose turn is currently active
        self.current_agent_index = 0

        # Current negotiation round
        self.round_count = 0

        # Stores the complete negotiation history
        self.negotiation_history = []

        # Stores the current state of the negotiation
        self.current_state = {
            "status": "Not Started",
            "current_agent": None,
            "last_offer": None
        }

    def start_negotiation(self):
        """Start the negotiation."""

        self.round_count = 1
        self.current_agent_index = 0

        current_agent = self.get_current_agent()

        self.current_state["status"] = "Negotiation Started"
        self.current_state["current_agent"] = current_agent

        print("\n===================================")
        print("     REAL ESTATE NEGOTIATION")
        print("===================================")
        print(f"Round: {self.round_count}")
        print(f"Current Agent: {current_agent}")

    def get_current_agent(self):
        """Return the agent whose turn it is."""

        return self.agents[self.current_agent_index]

    def get_next_agent(self):
        """Return the next agent in the turn order."""

        next_index = (self.current_agent_index + 1) % len(self.agents)

        return self.agents[next_index]

    def add_message(self, agent, message):
        """Add an agent's message to the negotiation history."""

        entry = {
            "round": self.round_count,
            "agent": agent,
            "message": message
        }

        self.negotiation_history.append(entry)

        # Update latest offer/message
        self.current_state["last_offer"] = message

    def next_turn(self):
        """Move the negotiation to the next agent."""

        self.current_agent_index = (
            self.current_agent_index + 1
        ) % len(self.agents)

        # Increase round when all agents have completed their turn
        if self.current_agent_index == 0:
            self.round_count += 1

        next_agent = self.get_current_agent()

        self.current_state["current_agent"] = next_agent

        print("\n-----------------------------------")
        print(f"Round: {self.round_count}")
        print(f"Next Agent: {next_agent}")
        print("-----------------------------------")

    def get_history(self):
        """Return the complete negotiation history."""

        return self.negotiation_history

    def get_state(self):
        """Return the current negotiation state."""

        return self.current_state

    def display_history(self):
        """Display the negotiation history."""

        print("\n========== NEGOTIATION HISTORY ==========")

        if not self.negotiation_history:
            print("No negotiation history available.")
            return

        for entry in self.negotiation_history:
            print(
                f"Round {entry['round']} | "
                f"{entry['agent']}: {entry['message']}"
            )

    def display_state(self):
        """Display the current negotiation state."""

        print("\n========== CURRENT STATE ==========")
        print(f"Status: {self.current_state['status']}")
        print(f"Current Agent: {self.current_state['current_agent']}")
        print(f"Last Offer: {self.current_state['last_offer']}")
        print(f"Round: {self.round_count}")