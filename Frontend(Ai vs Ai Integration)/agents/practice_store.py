import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod


@dataclass
class PracticeNegotiationSession:
    negotiation_id: str
    mode: str  # "human_vs_ai"
    status: str  # "active", "accepted", "rejected", "completed", "cancelled", "deadlocked"
    round: int
    max_rounds: int
    human_role: str  # "buyer" or "seller"
    ai_role: str  # "seller" or "buyer"
    ai_personality: str  # "aggressive", "collaborative", "risk_averse"
    property_index: int
    property: Dict[str, Any]
    reference_price: float
    asking_price: float
    target_price: float
    minimum_price: float
    maximum_price: float

    current_offer: Optional[float] = None
    last_human_offer: Optional[float] = None
    last_ai_offer: Optional[float] = None
    agreed_price: Optional[float] = None

    history: List[Dict[str, Any]] = field(default_factory=list)

    # =====================================================
    # DEADLOCK DETECTION STATE
    # =====================================================

    # Number of consecutive rounds where the human repeats
    # essentially the same offer.
    repeated_offer_count: int = 0

    # Number of consecutive rounds where there is very little
    # movement in the negotiation.
    stagnant_round_count: int = 0

    # Threshold used for comparing offers.
    # Example: 1000 means differences below ₹1,000
    # are considered effectively the same.
    deadlock_tolerance: float = 1000.0

    # Number of repeated/stagnant rounds required
    # before declaring a deadlock.
    deadlock_threshold: int = 3

    deadlock_reason: Optional[str] = None

    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseNegotiationStore(ABC):
    """
    Abstract storage interface for negotiation sessions.
    Allows easy switching between In-Memory, SQLite,
    PostgreSQL, MongoDB, etc.
    """

    @abstractmethod
    def save(self, session: PracticeNegotiationSession) -> None:
        pass

    @abstractmethod
    def get(
        self,
        negotiation_id: str
    ) -> Optional[PracticeNegotiationSession]:
        pass

    @abstractmethod
    def list(self) -> List[PracticeNegotiationSession]:
        pass

    @abstractmethod
    def delete(self, negotiation_id: str) -> bool:
        pass


class InMemoryNegotiationStore(BaseNegotiationStore):
    """
    In-memory dictionary store for practice sessions.
    """

    def __init__(self):
        self._sessions: Dict[str, PracticeNegotiationSession] = {}

    def save(self, session: PracticeNegotiationSession) -> None:
        session.updated_at = time.time()
        self._sessions[session.negotiation_id] = session

    def get(
        self,
        negotiation_id: str
    ) -> Optional[PracticeNegotiationSession]:
        return self._sessions.get(negotiation_id)

    def list(self) -> List[PracticeNegotiationSession]:
        return list(self._sessions.values())

    def delete(self, negotiation_id: str) -> bool:
        if negotiation_id in self._sessions:
            del self._sessions[negotiation_id]
            return True

        return False