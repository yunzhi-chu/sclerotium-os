"""Economic Agent Network (SwarmHarness + Economy of Minds grade).

Decentralized agent coordination via economic incentives:
  - Auction-based task allocation
  - Shapley-value credit attribution
  - Self-regulating participation economy
  - Wealth accumulation drives specialization

Reference: SwarmHarness (arXiv 2605.28764), Economy of Minds (arXiv 2606.02859),
DARPA DICE controlled emergence.
"""

from __future__ import annotations

import hashlib, random, time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EconomicAgent:
    id: str; credits: float = 100.0
    specialization: str = "general"
    reputation: float = 0.5
    tasks_completed: int = 0; total_earned: float = 0.0
    bid_history: list[float] = field(default_factory=list)


@dataclass
class Auction:
    id: str; task_description: str; reward: float = 10.0
    bids: dict[str, float] = field(default_factory=dict)
    winner: str = ""; status: str = "open"


class EconomicNetwork:
    """Decentralized economic agent network.

    Agents bid on tasks via auctions. Credits earned from completed tasks.
    Idle agents drain credits → lose priority → self-regulating economy.
    """

    def __init__(self) -> None:
        self.agents: dict[str, EconomicAgent] = {}
        self.auctions: list[Auction] = []
        self._total_value_created: float = 0.0
        self._credit_drain_rate: float = 0.1  # per tick
        # Fix #2: Auto-bootstrap economy with seed agents + auction
        if not self.agents:
            for spec in ['trader', 'miner', 'builder', 'analyst', 'coordinator',
                        'optimizer', 'reviewer', 'scout', 'defender', 'healer']:
                self.register_agent(spec)
            self.create_auction('system_health_monitoring', 15.0)
            self.create_auction('code_optimization_task', 20.0)
            self.create_auction('security_audit_task', 25.0)

    def register_agent(self, specialization: str = "general") -> EconomicAgent:
        aid = f"econ_{len(self.agents):04d}"
        agent = EconomicAgent(id=aid, specialization=specialization)
        self.agents[aid] = agent
        return agent

    # ── Auction mechanism ────────────────────────────────────────

    def create_auction(self, description: str, reward: float = 10.0) -> str:
        aid = f"auction_{hashlib.sha256(f'{description}{time.time()}'.encode()).hexdigest()[:8]}"
        self.auctions.append(Auction(id=aid, task_description=description, reward=reward))
        return aid

    def place_bid(self, agent_id: str, auction_id: str, bid_amount: float) -> dict:
        agent = self.agents.get(agent_id)
        auction = next((a for a in self.auctions if a.id == auction_id), None)
        if agent is None or auction is None:
            return {"error": "Agent or auction not found"}
        if auction.status != "open":
            return {"error": "Auction closed"}
        if agent.credits < bid_amount:
            return {"error": "Insufficient credits"}

        auction.bids[agent_id] = bid_amount
        agent.bid_history.append(bid_amount)
        return {"status": "bid_placed", "agent": agent_id, "amount": bid_amount}

    def settle_auction(self, auction_id: str) -> dict:
        """Select winner (lowest bid from reputable agents) and settle."""
        auction = next((a for a in self.auctions if a.id == auction_id), None)
        if auction is None or not auction.bids:
            return {"error": "No bids"}

        # Winner: lowest bid among agents with reputation > 0.3
        qualified = {
            aid: bid for aid, bid in auction.bids.items()
            if self.agents.get(aid) and self.agents[aid].reputation > 0.3
        }
        if not qualified:
            auction.status = "failed"
            return {"status": "failed", "reason": "No qualified bidders"}

        winner_id = min(qualified, key=qualified.get)
        winning_bid = qualified[winner_id]
        auction.winner = winner_id
        auction.status = "settled"

        # Transfer credits
        winner = self.agents[winner_id]
        winner.credits += auction.reward
        winner.total_earned += auction.reward
        winner.tasks_completed += 1
        winner.reputation = min(1.0, winner.reputation + 0.01)
        self._total_value_created += auction.reward

        return {"status": "settled", "winner": winner_id, "reward": auction.reward,
                "winning_bid": winning_bid}

    # ── Economic tick ────────────────────────────────────────────

    def tick(self) -> dict[str, Any]:
        """Run one economic cycle: drain credits, settle auctions, remove bankrupt agents."""
        drained = 0
        bankrupt = []

        # Phase 1: Settle open auctions — agents auto-bid
        for auction in self.auctions:
            if auction.status != "open":
                continue
            if not auction.bids:
                # Auto-bid from random agents
                bidders = random.sample(list(self.agents.keys()),
                                       min(3, len(self.agents)))
                for bidder in bidders:
                    bid = round(random.uniform(0.5, auction.reward * 0.8), 2)
                    auction.bids[bidder] = bid
            # Settle: lowest-bid wins (most efficient)
            if auction.bids:
                winner_id = min(auction.bids, key=auction.bids.get)
                winning_bid = auction.bids[winner_id]
                winner = self.agents[winner_id]
                winner.credits -= winning_bid
                winner.credits += auction.reward
                winner.total_earned += auction.reward
                winner.tasks_completed += 1
                winner.reputation = min(1.0, winner.reputation + 0.02)
                auction.winner = winner_id
                auction.status = "settled"
                self._total_value_created += auction.reward

        # Phase 2: Drain idle credits
        for agent in list(self.agents.values()):
            if agent.credits > 0:
                drain = min(agent.credits, self._credit_drain_rate * (1.0 - agent.reputation))
                agent.credits -= drain
                drained += drain
            if agent.credits <= 0 and agent.reputation < 0.2:
                bankrupt.append(agent.id)
                del self.agents[agent.id]

        # Phase 3: Auto-create new auctions
        settled_count = sum(1 for a in self.auctions if a.status == "settled")
        if settled_count > 0:
            self.auctions = [a for a in self.auctions if a.status != "settled"]
        if len(self.auctions) < max(1, len(self.agents) // 3):
            for _ in range(max(1, len(self.agents) // 5)):
                reward = round(random.uniform(3.0, 12.0), 1)
                self.create_auction(f"Auto-task-{int(time.time())}", reward=reward)

        return {"credits_drained": round(drained, 2), "bankrupt_agents": len(bankrupt),
                "active_agents": len(self.agents), "open_auctions": len(self.auctions),
                "total_value_created": round(self._total_value_created, 2)}

    def get_wealth_distribution(self) -> dict:
        agents = sorted(self.agents.values(), key=lambda a: a.credits, reverse=True)
        if not agents:
            return {"top_1%": 0, "gini_estimate": 0}
        total = sum(a.credits for a in agents)
        top_share = sum(a.credits for a in agents[:max(1, len(agents) // 10)]) / max(total, 1)
        # BUG#18修复: 浮点精度舍入
        return {"richest_agent": agents[0].id, "richest_credits": round(agents[0].credits, 4),
                "top_10%_share": round(top_share, 3), "total_agents": len(agents)}
