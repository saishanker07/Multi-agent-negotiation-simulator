# AI Driven Multi-Agent Negotiation Training & Simulation Platform

## About

This project is a real-estate negotiation training and simulation platform where multiple AI agents participate in a negotiation.

The system uses Buyer and Seller agents that make decisions based on their roles, personalities, goals, property details, price constraints, and previous negotiation history.

The backend is implemented using FastAPI and provides interactive API testing through Swagger UI.

## What I Implemented

### Orchestrator Agent

The Orchestrator Agent manages the complete negotiation flow.

It:

- Controls the turn order between Buyer and Seller.
- Passes negotiation history between agents.
- Maintains the current negotiation state.
- Keeps track of negotiation rounds.
- Coordinates the Buyer and Seller agents.

### Agent Reasoning Engine

An LLM-powered reasoning engine was implemented for the Buyer and Seller agents.

Each agent receives:

- Agent role
- Personality
- Goals
- Property information
- Target price
- Minimum price
- Maximum price
- Previous negotiation history

The reasoning engine uses this information to generate context-aware negotiation responses and offers.

### Counteroffer Evaluation

A Counteroffer Evaluation module was implemented to evaluate offers received from the other agent.

Based on the agent's goals and price constraints, the agent can:

- Accept an offer
- Reject an offer
- Generate a counteroffer

### AI-to-AI Negotiation

The complete AI-to-AI negotiation loop was implemented.

The Buyer and Seller agents negotiate with each other through multiple rounds.

The negotiation continues until:

- The agents reach an agreement, or
- The maximum number of rounds is reached.

The negotiation history and current state are returned by the backend.

## Real Estate Scenarios

The system currently supports three real-estate scenarios:

- Land / Plot
- Apartment / Flat
- Villa / Independent House

## Agent Personalities

The Buyer and Seller agents can be configured with different personalities.

### Aggressive

The agent takes a firm negotiation approach and tries to achieve a favorable price.

### Collaborative

The agent is more flexible and tries to reach a mutually acceptable agreement.

### Risk-Averse

The agent carefully evaluates offers and avoids unnecessary negotiation risks.

## Dataset

A real-estate dataset containing **14,528 properties** is used in the project.

The dataset file is:

```text
dataset_real.csv
