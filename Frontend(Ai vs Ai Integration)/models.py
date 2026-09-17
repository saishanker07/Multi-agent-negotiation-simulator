from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class NegotiationRequest(BaseModel):

    scenario: int = Field(
        ...,
        description="Scenario ID (1: Land, 2: Apartment, 3: Villa)",
        examples=[2]
    )

    buyer_personality: int = Field(
        ...,
        description="Buyer personality (1: Aggressive, 2: Collaborative, 3: Risk-Averse)",
        examples=[2]
    )

    seller_personality: int = Field(
        ...,
        description="Seller personality (1: Aggressive, 2: Collaborative, 3: Risk-Averse)",
        examples=[2]
    )

    property_index: Optional[int] = Field(
        0,
        description="Index of filtered property",
        examples=[0]
    )

    max_rounds: int = Field(
        10,
        description="Maximum negotiation rounds",
        examples=[10]
    )


class PracticeNegotiationRequest(BaseModel):

    scenario: int = Field(
        1,
        description="Scenario ID (1: Land / Plot, 2: Apartment / Flat, 3: Villa / House)",
        examples=[2]
    )

    property_index: Optional[int] = Field(
        0,
        description="Index of property in selected scenario",
        examples=[0]
    )

    human_role: str = Field(
        "buyer",
        description="Role of human participant: 'buyer' or 'seller'",
        examples=["buyer"]
    )

    ai_personality: str = Field(
        "collaborative",
        description="AI personality: 'aggressive', 'collaborative', or 'risk_averse'",
        examples=["collaborative"]
    )

    max_rounds: int = Field(
        10,
        description="Maximum number of negotiation rounds",
        examples=[10]
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "scenario": 2,
                "property_index": 0,
                "human_role": "buyer",
                "ai_personality": "collaborative",
                "max_rounds": 10
            }
        }
    }


class PracticeNegotiationStartResponse(BaseModel):

    negotiation_id: str
    mode: str
    human_role: str
    ai_role: str
    status: str
    property: Dict[str, Any]
    ai_message: str


class HumanMessageRequest(BaseModel):

    message: str = Field(
        ...,
        description="Natural language negotiation message",
        examples=["I offer ₹58.00 Lakhs for this property."]
    )

    offer: Optional[float] = Field(
        None,
        description="Optional explicit offer in INR",
        examples=[5800000]
    )


class AIResponseDetail(BaseModel):

    decision: str = Field(
        ...,
        description="Decision: ACCEPT, REJECT, COUNTER, or DEADLOCK",
        examples=["COUNTER"]
    )

    counter_offer: Optional[float] = Field(
        None,
        description="Counter-offer amount in INR"
    )

    message: str
    reason: Optional[str] = None


class PracticeMessageResponse(BaseModel):

    negotiation_id: str
    round: int
    human_message: str
    human_offer: Optional[float]
    ai_response: AIResponseDetail

    status: str = Field(
        ...,
        description="active, accepted, rejected, deadlocked, completed, or cancelled"
    )


class NegotiationStateResponse(BaseModel):

    negotiation_id: str
    mode: str
    status: str
    round: int
    max_rounds: int
    human_role: str
    ai_role: str
    ai_personality: str
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
    repeated_offer_count: int = 0
    stagnant_round_count: int = 0
    deadlock_tolerance: float = 1000.0
    deadlock_threshold: int = 3
    deadlock_reason: Optional[str] = None
    history: List[Dict[str, Any]]


class NegotiationHistoryResponse(BaseModel):

    negotiation_id: str
    status: str
    total_messages: int
    history: List[Dict[str, Any]]