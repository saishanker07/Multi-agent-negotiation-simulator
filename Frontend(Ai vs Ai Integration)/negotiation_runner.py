import re


# ============================================================
# PRICE EXTRACTION
# ============================================================

def extract_offer_amount(text):
    """Extract an offer amount from an agent response."""

    if text is None:
        return None

    if isinstance(text, (int, float)):
        return float(text)

    text = str(text)

    # Extract prices written in lakhs
    match = re.search(
        r'₹?\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lakh)\b',
        text, re.IGNORECASE
    )
    if match:
        return float(match.group(1).replace(",", "")) * 100000

    # Extract prices written using L
    match = re.search(
        r'₹?\s*([\d,]+(?:\.\d+)?)\s*[lL]\b',
        text
    )
    if match:
        return float(match.group(1).replace(",", "")) * 100000

    # Extract prices written in crores
    match = re.search(
        r'₹?\s*([\d,]+(?:\.\d+)?)\s*(?:crores?|crore)\b',
        text, re.IGNORECASE
    )
    if match:
        return float(match.group(1).replace(",", "")) * 10000000

    # Extract rupee values
    match = re.search(
        r'₹\s*([\d,]+(?:\.\d+)?)',
        text
    )
    if match:
        return float(match.group(1).replace(",", ""))

    # Extract counteroffer values without ₹
    match = re.search(
        r'(?:COUNTEROFFER|COUNTER OFFER|OFFER)\s*[:\-]?\s*'
        r'₹?\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lakh|L)?',
        text, re.IGNORECASE
    )
    if match:
        number = float(match.group(1).replace(",", ""))
        return number * 100000 if number < 10000 else number

    return None


# ============================================================
# FORMAT PRICE
# ============================================================

def format_price(amount):
    if amount is None:
        return "N/A"

    return f"₹{float(amount) / 100000:.2f} lakhs"


# ============================================================
# EXACT MATCH ONLY
# ============================================================

def offers_match_exactly(buyer_offer, seller_offer):
    if buyer_offer is None or seller_offer is None:
        return False

    return float(buyer_offer) == float(seller_offer)


# ============================================================
# DEADLOCK DETECTION
# ============================================================

def detect_deadlock(
    previous_buyer_offer,
    current_buyer_offer,
    previous_seller_offer,
    current_seller_offer,
    previous_gap=None,
    current_gap=None
):
    """
    Detect whether negotiation has become stuck.

    Conditions:
    1. Both agents repeat exactly the same offers.
    2. Negotiation gap does not decrease.

    Exact equality is checked before deadlock detection.
    """

    if None in (
        previous_buyer_offer,
        previous_seller_offer,
        current_buyer_offer,
        current_seller_offer
    ):
        return False

    previous_buyer_offer = float(previous_buyer_offer)
    current_buyer_offer = float(current_buyer_offer)
    previous_seller_offer = float(previous_seller_offer)
    current_seller_offer = float(current_seller_offer)

    # Exact agreement is never treated as deadlock
    if offers_match_exactly(current_buyer_offer, current_seller_offer):
        return False

    # Check whether both agents repeated their offers
    buyer_stuck = current_buyer_offer == previous_buyer_offer
    seller_stuck = current_seller_offer == previous_seller_offer

    if buyer_stuck and seller_stuck:
        return True

    # Check whether the negotiation gap stopped improving
    if previous_gap is not None and current_gap is not None:
        previous_gap = abs(float(previous_gap))
        current_gap = abs(float(current_gap))

        if current_gap >= previous_gap:
            return True

    return False


# ============================================================
# ORCHESTRATOR STATE
# ============================================================

def update_orchestrator_state(
    orchestrator,
    status,
    current_agent,
    last_offer
):
    try:
        state = orchestrator.get_state()
        state["status"] = status
        state["current_agent"] = current_agent
        state["last_offer"] = last_offer
    except Exception:
        pass


# ============================================================
# ADD HISTORY
# ============================================================

def add_history(history, round_number, agent, message):
    history.append({
        "round": round_number,
        "agent": agent,
        "message": message
    })


# ============================================================
# ADD ORCHESTRATOR MESSAGE
# ============================================================

def add_orchestrator_message(orchestrator, agent, message):
    try:
        orchestrator.add_message(agent, message)
    except Exception:
        pass


# ============================================================
# NEGOTIATION RUNNER
# ============================================================

def run_negotiation(
    orchestrator,
    buyer_reasoning,
    seller_reasoning,
    buyer_evaluator,
    seller_evaluator,
    property_data,
    reference_price,
    max_rounds=10
):
    """
    Main AI-vs-AI negotiation loop.

    Rules:
    1. Buyer starts.
    2. Seller responds.
    3. One round = Buyer + Seller.
    4. Buyer moves upward.
    5. Seller starts at reference price.
    6. Seller moves downward.
    7. Exact equality is the only agreement condition.
    8. Close prices are not agreement.
    9. No tolerance is used.
    10. Gemini does not control prices.
    11. Evaluators control prices.
    12. Failure to agree by max_rounds = REJECTED.
    13. No progress = DEADLOCK.
    14. AGREEMENT_REACHED always has agreed_price.
    """

    # ========================================================
    # INITIALIZE SETTINGS
    # ========================================================

    if max_rounds is None:
        max_rounds = 10

    try:
        max_rounds = int(max_rounds)
    except Exception:
        max_rounds = 10

    if max_rounds <= 0:
        max_rounds = 10

    reference_price = float(reference_price)

    # ========================================================
    # NEGOTIATION STATE
    # ========================================================

    buyer_offer = None
    seller_offer = None
    last_buyer_offer = None
    last_seller_offer = None
    agreed_price = None
    history = []
    status = "REJECTED"

    # ========================================================
    # DEADLOCK STATE
    # ========================================================

    previous_round_buyer_offer = None
    previous_round_seller_offer = None
    previous_gap = None
    deadlock_detected = False

    # ========================================================
    # START NEGOTIATION
    # ========================================================

    try:
        orchestrator.start_negotiation()
    except Exception:
        pass

    update_orchestrator_state(
        orchestrator,
        "Negotiation Started",
        "Buyer Agent",
        None
    )

    print("\n===================================")
    print("       NEGOTIATION STARTED")
    print("===================================")
    print(f"Reference Price: {format_price(reference_price)}")

    # ========================================================
    # ROUND LOOP
    # ========================================================

    for round_number in range(1, max_rounds + 1):

        # Keep Orchestrator synchronized with the runner
        try:
            orchestrator.round_count = round_number
            orchestrator.current_agent_index = 0
        except Exception:
            pass

        print("\n===================================")
        print(f"ROUND {round_number}")
        print("===================================")

        # ====================================================
        # BUYER TURN
        # ====================================================

        print("CURRENT AGENT: Buyer Agent")

        buyer_evaluation = buyer_evaluator.evaluate(
            incoming_offer=seller_offer,
            previous_offer=last_buyer_offer,
            reference_price=reference_price
        )

        print("\nGenerating Buyer response...")

        try:
            buyer_response = buyer_reasoning.generate_response(
                history,
                buyer_evaluation
            )
        except Exception as error:
            print("\nReasoning engine error:")
            print(str(error))

            buyer_response = _fallback_response_from_evaluation(
                buyer_evaluation
            )

        # Price comes only from evaluator
        buyer_decision = str(
            buyer_evaluation.get("decision", "COUNTER")
        ).upper()

        if buyer_decision == "ACCEPT":
            buyer_offer = buyer_evaluation.get("accepted_price")
        else:
            buyer_offer = buyer_evaluation.get("counter_price")

        # Safety fallback
        if buyer_offer is None:
            buyer_offer = (
                last_buyer_offer
                if last_buyer_offer is not None
                else reference_price * 0.90
            )

            buyer_offer = _round_price(buyer_offer)
            buyer_response = _fallback_counter_response(buyer_offer)

        buyer_offer = _round_price(buyer_offer)

        # Buyer output
        print("\nBuyer Agent:")
        print(buyer_response)
        print(f"\nDecision: {buyer_decision}")
        print(f"Buyer Offer: {format_price(buyer_offer)}")

        add_history(
            history,
            round_number,
            "Buyer Agent",
            buyer_response
        )

        add_orchestrator_message(
            orchestrator,
            "Buyer Agent",
            buyer_response
        )

        # Check exact agreement after buyer turn
        if offers_match_exactly(buyer_offer, seller_offer):
            agreed_price = float(buyer_offer)
            status = "AGREEMENT_REACHED"

            print("\n===================================")
            print("       AGREEMENT REACHED")
            print("===================================")
            print(f"Buyer Offer: {format_price(buyer_offer)}")
            print(f"Seller Offer: {format_price(seller_offer)}")
            print(f"Agreed Price: {format_price(agreed_price)}")

            update_orchestrator_state(
                orchestrator,
                "Agreement Reached",
                "Negotiation Completed",
                format_price(agreed_price)
            )

            break

        last_buyer_offer = buyer_offer

        # ====================================================
        # SELLER TURN
        # ====================================================

        print("\nCURRENT AGENT: Seller Agent")

        seller_evaluation = seller_evaluator.evaluate(
            incoming_offer=buyer_offer,
            previous_offer=last_seller_offer,
            reference_price=reference_price
        )

        print("\nGenerating Seller response...")

        try:
            seller_response = seller_reasoning.generate_response(
                history,
                seller_evaluation
            )
        except Exception as error:
            print("\nReasoning engine error:")
            print(str(error))

            seller_response = _fallback_response_from_evaluation(
                seller_evaluation
            )

        # Price comes only from evaluator
        seller_decision = str(
            seller_evaluation.get("decision", "COUNTER")
        ).upper()

        if seller_decision == "ACCEPT":
            seller_offer = seller_evaluation.get("accepted_price")
        else:
            seller_offer = seller_evaluation.get("counter_price")

        # Safety fallback
        if seller_offer is None:
            seller_offer = (
                last_seller_offer
                if last_seller_offer is not None
                else reference_price
            )

            seller_offer = _round_price(seller_offer)
            seller_response = _fallback_counter_response(seller_offer)

        seller_offer = _round_price(seller_offer)

        # Seller output
        print("\nSeller Agent:")
        print(seller_response)
        print(f"\nDecision: {seller_decision}")
        print(f"Seller Offer: {format_price(seller_offer)}")

        add_history(
            history,
            round_number,
            "Seller Agent",
            seller_response
        )

        add_orchestrator_message(
            orchestrator,
            "Seller Agent",
            seller_response
        )

        # ====================================================
        # EXACT AGREEMENT CHECK
        # ====================================================

        if offers_match_exactly(buyer_offer, seller_offer):
            agreed_price = float(buyer_offer)
            status = "AGREEMENT_REACHED"

            print("\n===================================")
            print("       AGREEMENT REACHED")
            print("===================================")
            print(f"Buyer Offer: {format_price(buyer_offer)}")
            print(f"Seller Offer: {format_price(seller_offer)}")
            print(f"Agreed Price: {format_price(agreed_price)}")

            update_orchestrator_state(
                orchestrator,
                "Agreement Reached",
                "Negotiation Completed",
                format_price(agreed_price)
            )

            break

        # ====================================================
        # DEADLOCK DETECTION
        # ====================================================

        current_gap = float(seller_offer) - float(buyer_offer)

        deadlock_detected = detect_deadlock(
            previous_buyer_offer=previous_round_buyer_offer,
            current_buyer_offer=buyer_offer,
            previous_seller_offer=previous_round_seller_offer,
            current_seller_offer=seller_offer,
            previous_gap=previous_gap,
            current_gap=current_gap
        )

        if deadlock_detected:
            status = "DEADLOCK"

            print("\n===================================")
            print("       NEGOTIATION DEADLOCK")
            print("===================================")

            print(
                "Buyer and Seller are no longer "
                "making meaningful progress."
            )

            print(f"Buyer Offer: {format_price(buyer_offer)}")
            print(f"Seller Offer: {format_price(seller_offer)}")
            print(
                f"Remaining Gap: "
                f"{format_price(abs(current_gap))}"
            )

            update_orchestrator_state(
                orchestrator,
                "Negotiation Deadlock",
                "Negotiation Completed",
                format_price(seller_offer)
            )

            break

        # Store current round for next deadlock check
        previous_round_buyer_offer = buyer_offer
        previous_round_seller_offer = seller_offer
        previous_gap = current_gap
        last_seller_offer = seller_offer

        # Continue to next round
        update_orchestrator_state(
            orchestrator,
            "Negotiation In Progress",
            "Buyer Agent",
            format_price(seller_offer)
        )

    # ========================================================
    # MAX ROUNDS REACHED
    # ========================================================

    if agreed_price is None and status != "DEADLOCK":
        status = "REJECTED"

        last_offer = (
            seller_offer
            if seller_offer is not None
            else buyer_offer
        )

        update_orchestrator_state(
            orchestrator,
            "Negotiation Rejected",
            "Negotiation Completed",
            format_price(last_offer)
        )

        print("\n===================================")
        print("       NEGOTIATION REJECTED")
        print("===================================")

        print(
            "Buyer and Seller did not reach "
            "the exact same offer."
        )

        print(f"Maximum rounds reached: {max_rounds}")

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result = {
        "status": status,
        "agreed_price": agreed_price,
        "negotiation_history": history
    }

    # Safety invariant:
    # AGREEMENT_REACHED can never have null agreed_price.
    if (
        result["status"] == "AGREEMENT_REACHED"
        and result["agreed_price"] is None
    ):
        result["status"] = "REJECTED"

    return result


# ============================================================
# FALLBACK FROM EVALUATION
# ============================================================

def _fallback_response_from_evaluation(evaluation):
    decision = str(
        evaluation.get("decision", "COUNTER")
    ).upper()

    if decision == "ACCEPT":
        price = evaluation.get("accepted_price")

        return (
            "DECISION: ACCEPT\n\n"
            "We accept the current offer.\n\n"
            f"ACCEPTED OFFER: {format_price(price)}"
        )

    price = evaluation.get("counter_price")

    return (
        "DECISION: COUNTER\n\n"
        "We appreciate the offer and "
        "would like to continue negotiating.\n\n"
        f"COUNTEROFFER: {format_price(price)}"
    )


# ============================================================
# FALLBACK COUNTER RESPONSE
# ============================================================

def _fallback_counter_response(price):
    return (
        "DECISION: COUNTER\n\n"
        "We would like to continue the "
        "negotiation with the following offer.\n\n"
        f"COUNTEROFFER: {format_price(price)}"
    )


# ============================================================
# ROUND PRICE
# ============================================================

def _round_price(price):
    return float(round(float(price) / 1000) * 1000)