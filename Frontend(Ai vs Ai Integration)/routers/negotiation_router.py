import time
import uuid

from fastapi import APIRouter, HTTPException

from models import (
    NegotiationRequest,
    PracticeNegotiationRequest,
    PracticeNegotiationStartResponse,
    HumanMessageRequest,
    AIResponseDetail,
    PracticeMessageResponse,
    NegotiationStateResponse,
    NegotiationHistoryResponse
)

from property_utils import (
    classify_property,
    get_scenario_key,
    extract_price,
    get_filtered_properties
)

from negotiation_runner import run_negotiation

from agents.orchestrator_agent import OrchestratorAgent
from agents.reasoning_engine import ReasoningEngine
from agents.counteroffer_evaluator import CounterofferEvaluator
from agents.practice_agent import PracticeAIAgent
from agents.practice_store import (
    PracticeNegotiationSession,
    InMemoryNegotiationStore
)


router = APIRouter()

practice_store = InMemoryNegotiationStore()
practice_agent = PracticeAIAgent()

SCENARIOS = {
    1: "Land / Plot",
    2: "Apartment / Flat",
    3: "Villa / Independent House"
}

PERSONALITIES = {
    1: "Aggressive",
    2: "Collaborative",
    3: "Risk-Averse"
}

dataset = []


def set_dataset(data):
    global dataset
    dataset = data


def _get_session(negotiation_id):
    session = practice_store.get(negotiation_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Negotiation session '{negotiation_id}' not found."
        )

    return session


def _get_property(scenario, property_index=None):
    filtered = get_filtered_properties(dataset, scenario)

    if not filtered:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No properties are available for Scenario {scenario}: "
                f"{SCENARIOS[scenario]}. "
                "The current dataset does not contain matching properties."
            )
        )

    index = 0 if property_index is None else property_index

    if index < 0 or index >= len(filtered):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid property_index {index}. "
                f"Scenario {scenario} contains "
                f"{len(filtered)} matching properties."
            )
        )

    return filtered[index]


# =====================================================
# SCENARIOS
# =====================================================

@router.get("/scenarios")
def get_scenarios():
    return {"scenarios": SCENARIOS}


# =====================================================
# PERSONALITIES
# =====================================================

@router.get("/personalities")
def get_personalities():
    return {"personalities": PERSONALITIES}


# =====================================================
# PROPERTIES
# =====================================================

@router.get("/properties")
def get_properties(
    scenario: int = None,
    start: int = 0,
    limit: int = 7000
):
    if (
        dataset is None
        or (hasattr(dataset, "empty") and dataset.empty)
        or (not hasattr(dataset, "empty") and not dataset)
    ):
        raise HTTPException(
            status_code=500,
            detail="Dataset is not loaded."
        )

    if start < 0:
        raise HTTPException(
            status_code=400,
            detail="Start cannot be negative."
        )

    if limit <= 0:
        raise HTTPException(
            status_code=400,
            detail="Limit must be greater than 0."
        )

    if limit > 7000:
        limit = 7000

    # -------------------------------------------------
    # WITH SCENARIO
    # -------------------------------------------------

    if scenario is not None:
        if scenario not in SCENARIOS:
            raise HTTPException(
                status_code=400,
                detail="Invalid scenario. Choose 1, 2 or 3."
            )

        filtered = get_filtered_properties(dataset, scenario)
        selected = filtered[start:start + limit]

        properties = [
            {
                "index": index,
                "original_dataset_index": item["original_dataset_index"],
                "property": item["property"],
                "scenario": scenario,
                "scenario_name": SCENARIOS[scenario]
            }
            for index, item in enumerate(selected, start=start)
        ]

        return {
            "total_properties": len(filtered),
            "total_dataset_properties": len(dataset),
            "start": start,
            "limit": limit,
            "returned": len(properties),
            "scenario": scenario,
            "scenario_name": SCENARIOS[scenario],
            "properties": properties
        }

    # -------------------------------------------------
    # WITHOUT SCENARIO
    # -------------------------------------------------

    if hasattr(dataset, "iloc"):
        selected_data = (
            dataset.iloc[start:start + limit]
            .to_dict(orient="records")
        )
    else:
        selected_data = dataset[start:start + limit]

    properties = [
        {
            "index": index,
            "property": property_data
        }
        for index, property_data in enumerate(
            selected_data,
            start=start
        )
    ]

    return {
        "total_properties": len(dataset),
        "start": start,
        "limit": limit,
        "returned": len(properties),
        "properties": properties
    }


# =====================================================
# HUMAN VS AI - START
# =====================================================

@router.post(
    "/negotiations/practice",
    response_model=PracticeNegotiationStartResponse
)
def start_practice_negotiation(
    request: PracticeNegotiationRequest
):
    if request.scenario not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid scenario '{request.scenario}'. "
                "Choose 1, 2 or 3."
            )
        )

    human_role = request.human_role.strip().lower()

    if human_role not in ["buyer", "seller"]:
        raise HTTPException(
            status_code=400,
            detail="human_role must be buyer or seller."
        )

    ai_role = "seller" if human_role == "buyer" else "buyer"

    personality = (
        request.ai_personality
        .strip()
        .lower()
        .replace("-", "_")
    )

    if personality in ["1", "aggressive"]:
        personality_key = "aggressive"
    elif personality in ["2", "collaborative"]:
        personality_key = "collaborative"
    elif personality in ["3", "risk_averse", "riskaverse"]:
        personality_key = "risk_averse"
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid ai_personality. "
                "Use aggressive, collaborative or risk_averse."
            )
        )

    selected_item = _get_property(
        request.scenario,
        request.property_index
    )

    property_data = selected_item["property"]

    if classify_property(property_data) != get_scenario_key(request.scenario):
        raise HTTPException(
            status_code=500,
            detail=(
                "Property classification mismatch. "
                "Please check scenario filtering."
            )
        )

    reference_price = extract_price(property_data)

    if reference_price is None or reference_price <= 0:
        reference_price = 5000000.0

    if ai_role == "seller":
        asking_price = reference_price
        target_price = reference_price * 0.95
        minimum_price = reference_price * 0.75
        maximum_price = reference_price * 1.10
    else:
        asking_price = reference_price
        target_price = reference_price * 0.90
        minimum_price = reference_price * 0.70
        maximum_price = reference_price

    session_id = uuid.uuid4().hex[:8]

    session = PracticeNegotiationSession(
        negotiation_id=session_id,
        mode="human_vs_ai",
        status="active",
        round=1,
        max_rounds=max(1, request.max_rounds),
        human_role=human_role,
        ai_role=ai_role,
        ai_personality=personality_key,
        property_index=(
            request.property_index
            if request.property_index is not None
            else 0
        ),
        property=property_data,
        reference_price=reference_price,
        asking_price=asking_price,
        target_price=target_price,
        minimum_price=minimum_price,
        maximum_price=maximum_price,
        current_offer=(
            reference_price if ai_role == "seller" else None
        ),
        last_human_offer=None,
        last_ai_offer=(
            reference_price if ai_role == "seller" else None
        ),
        agreed_price=None,
        history=[]
    )

    ai_greeting = practice_agent.generate_initial_greeting(session)

    session.history.append({
        "round": 0,
        "sender": f"ai_{ai_role}",
        "message": ai_greeting,
        "decision": "INITIAL_GREETING",
        "offer": session.last_ai_offer,
        "timestamp": time.time()
    })

    practice_store.save(session)

    return PracticeNegotiationStartResponse(
        negotiation_id=session.negotiation_id,
        mode=session.mode,
        human_role=session.human_role,
        ai_role=session.ai_role,
        status=session.status,
        property=session.property,
        ai_message=ai_greeting
    )


# =====================================================
# HUMAN VS AI - MESSAGE
# =====================================================

@router.post(
    "/negotiations/{negotiation_id}/message",
    response_model=PracticeMessageResponse
)
def send_practice_message(
    negotiation_id: str,
    request: HumanMessageRequest
):
    session = _get_session(negotiation_id)

    if session.status != "active":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Negotiation '{negotiation_id}' is not active. "
                f"Current status: {session.status}."
            )
        )

    human_offer = (
        request.offer
        if request.offer is not None
        else practice_agent.extract_offer_from_text(request.message)
    )

    session.history.append({
        "round": session.round,
        "sender": f"human_{session.human_role}",
        "message": request.message,
        "offer": human_offer,
        "timestamp": time.time()
    })

    if human_offer is not None:
        session.last_human_offer = human_offer
        session.current_offer = human_offer

    ai_result = practice_agent.evaluate_and_respond(
        session=session,
        human_message=request.message,
        explicit_offer=human_offer
    )

    decision = ai_result.get("decision", "REJECT")
    counter_offer = ai_result.get("counter_offer")
    ai_message = ai_result.get(
        "message",
        "Unable to generate a response."
    )
    reason = ai_result.get("reason")

    if decision == "ACCEPT":
        session.status = "accepted"
        session.agreed_price = (
            counter_offer
            if counter_offer is not None
            else human_offer
        )
        session.current_offer = session.agreed_price

    elif decision == "REJECT":
        session.status = "rejected"

    elif decision == "COUNTER":
        if counter_offer is not None:
            session.last_ai_offer = counter_offer
            session.current_offer = counter_offer

    elif decision == "DEADLOCK":
        session.status = "deadlocked"
        session.deadlock_reason = (
            reason or "Negotiation reached a deadlock."
        )
        ai_message += "\n\nNegotiation status: DEADLOCKED."

    if (
        session.status == "active"
        and session.round >= session.max_rounds
    ):
        session.status = "completed"
        ai_message += (
            "\n\n"
            f"[Negotiation ended: Maximum rounds "
            f"({session.max_rounds}) reached.]"
        )

    session.history.append({
        "round": session.round,
        "sender": f"ai_{session.ai_role}",
        "decision": decision,
        "offer": counter_offer,
        "message": ai_message,
        "reason": reason,
        "timestamp": time.time()
    })

    current_round = session.round

    if session.status == "active":
        session.round += 1

    practice_store.save(session)

    return PracticeMessageResponse(
        negotiation_id=session.negotiation_id,
        round=current_round,
        human_message=request.message,
        human_offer=human_offer,
        ai_response=AIResponseDetail(
            decision=decision,
            counter_offer=counter_offer,
            message=ai_message,
            reason=reason
        ),
        status=session.status
    )


# =====================================================
# NEGOTIATION STATE
# =====================================================

@router.get(
    "/negotiations/{negotiation_id}",
    response_model=NegotiationStateResponse
)
def get_negotiation_state(negotiation_id: str):
    session = _get_session(negotiation_id)

    return NegotiationStateResponse(
        negotiation_id=session.negotiation_id,
        mode=session.mode,
        status=session.status,
        round=session.round,
        max_rounds=session.max_rounds,
        human_role=session.human_role,
        ai_role=session.ai_role,
        ai_personality=session.ai_personality,
        property=session.property,
        reference_price=session.reference_price,
        asking_price=session.asking_price,
        target_price=session.target_price,
        minimum_price=session.minimum_price,
        maximum_price=session.maximum_price,
        current_offer=session.current_offer,
        last_human_offer=session.last_human_offer,
        last_ai_offer=session.last_ai_offer,
        agreed_price=session.agreed_price,
        repeated_offer_count=session.repeated_offer_count,
        stagnant_round_count=session.stagnant_round_count,
        deadlock_tolerance=session.deadlock_tolerance,
        deadlock_threshold=session.deadlock_threshold,
        deadlock_reason=session.deadlock_reason,
        history=session.history
    )


# =====================================================
# NEGOTIATION HISTORY
# =====================================================

@router.get(
    "/negotiations/{negotiation_id}/history",
    response_model=NegotiationHistoryResponse
)
def get_negotiation_history(negotiation_id: str):
    session = _get_session(negotiation_id)

    return NegotiationHistoryResponse(
        negotiation_id=session.negotiation_id,
        status=session.status,
        total_messages=len(session.history),
        history=session.history
    )


# =====================================================
# CANCEL NEGOTIATION
# =====================================================

@router.post(
    "/negotiations/{negotiation_id}/cancel"
)
def cancel_negotiation(negotiation_id: str):
    session = _get_session(negotiation_id)

    if session.status != "active":
        return {
            "negotiation_id": session.negotiation_id,
            "status": session.status,
            "message": f"Session was already {session.status}."
        }

    session.status = "cancelled"

    session.history.append({
        "round": session.round,
        "sender": "system",
        "message": "Negotiation session was cancelled by the user.",
        "timestamp": time.time()
    })

    practice_store.save(session)

    return {
        "negotiation_id": session.negotiation_id,
        "status": "cancelled",
        "message": "Negotiation cancelled successfully."
    }


# =====================================================
# AI VS AI SIMULATION
# KEEP THIS AT THE END
# =====================================================

@router.post("/negotiations")
def start_negotiation(request: NegotiationRequest):

    if request.scenario not in SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail="Invalid scenario. Choose 1, 2 or 3."
        )

    if request.buyer_personality not in PERSONALITIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid buyer personality."
        )

    if request.seller_personality not in PERSONALITIES:
        raise HTTPException(
            status_code=400,
            detail="Invalid seller personality."
        )

    selected_item = _get_property(
        request.scenario,
        request.property_index
    )

    property_data = selected_item["property"]
    reference_price = extract_price(property_data)

    if reference_price is None:
        raise HTTPException(
            status_code=400,
            detail="Could not determine property price."
        )

    buyer_personality = PERSONALITIES[
        request.buyer_personality
    ]

    seller_personality = PERSONALITIES[
        request.seller_personality
    ]

    buyer_target = reference_price * 0.90
    buyer_minimum = reference_price * 0.70
    buyer_maximum = reference_price

    seller_target = reference_price * 0.95
    seller_minimum = reference_price * 0.75
    seller_maximum = reference_price

    buyer_evaluator = CounterofferEvaluator(
        role="buyer",
        target_price=buyer_target,
        minimum_price=buyer_minimum,
        maximum_price=buyer_maximum
    )

    seller_evaluator = CounterofferEvaluator(
        role="seller",
        target_price=seller_target,
        minimum_price=seller_minimum,
        maximum_price=seller_maximum
    )

    buyer_reasoning = ReasoningEngine(
        role="Buyer Agent",
        persona=buyer_personality,
        goals=(
            "Buy the property at a reasonable price "
            "while staying within budget."
        ),
        target_price=buyer_target,
        minimum_price=buyer_minimum,
        maximum_price=buyer_maximum
    )

    seller_reasoning = ReasoningEngine(
        role="Seller Agent",
        persona=seller_personality,
        goals=(
            "Sell the property at a good price "
            "while remaining willing to negotiate."
        ),
        target_price=seller_target,
        minimum_price=seller_minimum,
        maximum_price=seller_maximum
    )

    orchestrator = OrchestratorAgent([
        "Buyer Agent",
        "Seller Agent"
    ])

    try:
        result = run_negotiation(
            orchestrator=orchestrator,
            buyer_reasoning=buyer_reasoning,
            seller_reasoning=seller_reasoning,
            buyer_evaluator=buyer_evaluator,
            seller_evaluator=seller_evaluator,
            property_data=property_data,
            reference_price=reference_price,
            max_rounds=request.max_rounds
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    return {
        "status": result.get("status"),
        "agreed_price": result.get("agreed_price"),
        "scenario": SCENARIOS[request.scenario],
        "scenario_id": request.scenario,
        "buyer_personality": buyer_personality,
        "seller_personality": seller_personality,
        "property": property_data,
        "original_dataset_index": (
            selected_item["original_dataset_index"]
        ),
        "negotiation_history": orchestrator.get_history(),
        "current_state": orchestrator.get_state()
    }