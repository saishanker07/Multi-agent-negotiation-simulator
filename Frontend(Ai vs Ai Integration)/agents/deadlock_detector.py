from typing import List, Dict, Any


class DeadlockDetector:
    """
    Detects a stalled negotiation.

    IMPORTANT:
    - This class does NOT decide prices.
    - This class does NOT modify Buyer/Seller offers.
    - CounterofferEvaluator remains responsible for prices.
    - This class only observes negotiation history.

    Deadlock process:

        Negotiation continues
              ↓
        Offers stop moving
              ↓
        Stall threshold reached
              ↓
        Resolution attempt
              ↓
        Still stalled
              ↓
        Breakdown
    """

    def __init__(
        self,
        stall_rounds: int = 3,
        minimum_price_change: float = 1000.0
    ):
        self.stall_rounds = max(
            1,
            int(stall_rounds)
        )

        self.minimum_price_change = float(
            minimum_price_change
        )

        self.resolution_attempted = False

    # =========================================================
    # CHECK DEADLOCK
    # =========================================================

    def check_deadlock(
        self,
        history: List[Dict[str, Any]],
        current_round: int,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Check the current negotiation history.

        Returns:

        {
            "deadlock": True / False,
            "stalled_rounds": number,
            "threshold": configured threshold,
            "action": "CONTINUE",
            "action": "RESOLUTION_ATTEMPT",
            "action": "BREAKDOWN",
            "reason": explanation
        }
        """

        # -----------------------------------------------------
        # Already finished negotiations cannot be deadlocked.
        # -----------------------------------------------------

        if str(status).lower() != "active":

            return self._build_result(
                deadlock=False,
                stalled_rounds=0,
                action="CONTINUE",
                reason=(
                    "Negotiation is no longer active."
                )
            )

        # -----------------------------------------------------
        # No history = nothing to detect.
        # -----------------------------------------------------

        if not history:

            return self._build_result(
                deadlock=False,
                stalled_rounds=0,
                action="CONTINUE",
                reason=(
                    "No negotiation history available."
                )
            )

        # -----------------------------------------------------
        # Extract actual numeric offers.
        # -----------------------------------------------------

        offer_entries = self._extract_offer_entries(
            history
        )

        # Need at least two offers to compare movement.
        if len(offer_entries) < 2:

            return self._build_result(
                deadlock=False,
                stalled_rounds=0,
                action="CONTINUE",
                reason=(
                    "Not enough offers to detect deadlock."
                )
            )

        # -----------------------------------------------------
        # Count consecutive stalled offer movements.
        # -----------------------------------------------------

        stalled_rounds = (
            self._calculate_stalled_rounds(
                offer_entries
            )
        )

        # -----------------------------------------------------
        # Threshold not reached.
        # -----------------------------------------------------

        if stalled_rounds < self.stall_rounds:

            return self._build_result(
                deadlock=False,
                stalled_rounds=stalled_rounds,
                action="CONTINUE",
                reason=(
                    f"Negotiation is progressing. "
                    f"{stalled_rounds} stalled movement(s) "
                    f"detected."
                )
            )

        # -----------------------------------------------------
        # First deadlock detection.
        # -----------------------------------------------------

        if not self.resolution_attempted:

            self.resolution_attempted = True

            return self._build_result(
                deadlock=True,
                stalled_rounds=stalled_rounds,
                action="RESOLUTION_ATTEMPT",
                reason=(
                    f"Negotiation has stalled for "
                    f"{stalled_rounds} consecutive "
                    f"offer movements."
                )
            )

        # -----------------------------------------------------
        # Deadlock remained after resolution attempt.
        # -----------------------------------------------------

        return self._build_result(
            deadlock=True,
            stalled_rounds=stalled_rounds,
            action="BREAKDOWN",
            reason=(
                "Negotiation remained stalled after "
                "the resolution attempt."
            )
        )

    # =========================================================
    # EXTRACT OFFERS
    # =========================================================

    def _extract_offer_entries(
        self,
        history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract numeric offers from negotiation history.

        Supports the history format used by the current
        OrchestratorAgent:

            {
                "round": 1,
                "agent": "Buyer Agent",
                "message": "..."
            }

        If an offer is not explicitly stored, the detector
        attempts to extract it from the message.
        """

        entries = []

        for entry in history:

            if not isinstance(entry, dict):
                continue

            offer = entry.get("offer")

            # -------------------------------------------------
            # Current runner stores the offer inside the
            # natural-language message.
            # -------------------------------------------------

            if offer is None:

                message = entry.get(
                    "message",
                    ""
                )

                offer = self._extract_offer_from_message(
                    message
                )

            if offer is None:
                continue

            try:

                offer = float(offer)

            except (
                TypeError,
                ValueError
            ):
                continue

            entries.append(
                {
                    "round": entry.get(
                        "round"
                    ),
                    "agent": entry.get(
                        "agent"
                    ),
                    "offer": offer
                }
            )

        return entries

    # =========================================================
    # EXTRACT PRICE FROM MESSAGE
    # =========================================================

    def _extract_offer_from_message(
        self,
        message
    ):
        """
        Extract prices from messages.

        Supports examples such as:

            ₹54.00 lakhs
            ₹65.50 lakhs
            ₹5400000
            COUNTEROFFER: ₹54.00 lakhs
        """

        if message is None:
            return None

        text = str(message)

        # -----------------------------------------------------
        # Lakhs
        # -----------------------------------------------------

        import re

        match = re.search(
            r'₹?\s*([\d,]+(?:\.\d+)?)\s*'
            r'(?:lakhs?|lakh)\b',
            text,
            re.IGNORECASE
        )

        if match:

            value = (
                match.group(1)
                .replace(",", "")
            )

            try:

                return (
                    float(value) *
                    100000
                )

            except ValueError:

                return None

        # -----------------------------------------------------
        # Crores
        # -----------------------------------------------------

        match = re.search(
            r'₹?\s*([\d,]+(?:\.\d+)?)\s*'
            r'(?:crores?|crore)\b',
            text,
            re.IGNORECASE
        )

        if match:

            value = (
                match.group(1)
                .replace(",", "")
            )

            try:

                return (
                    float(value) *
                    10000000
                )

            except ValueError:

                return None

        # -----------------------------------------------------
        # Rupee amount
        # -----------------------------------------------------

        match = re.search(
            r'₹\s*([\d,]+(?:\.\d+)?)',
            text
        )

        if match:

            value = (
                match.group(1)
                .replace(",", "")
            )

            try:

                return float(value)

            except ValueError:

                return None

        return None

    # =========================================================
    # CALCULATE STALLED ROUNDS
    # =========================================================

    def _calculate_stalled_rounds(
        self,
        offer_entries: List[Dict[str, Any]]
    ) -> int:
        """
        Count consecutive offer movements where the price
        changed by less than minimum_price_change.

        The count starts from the latest offer and moves
        backwards until meaningful movement is found.
        """

        if len(offer_entries) < 2:
            return 0

        stalled = 0

        for index in range(
            len(offer_entries) - 1,
            0,
            -1
        ):

            current_offer = (
                offer_entries[index]["offer"]
            )

            previous_offer = (
                offer_entries[index - 1]["offer"]
            )

            difference = abs(
                current_offer -
                previous_offer
            )

            if difference < self.minimum_price_change:

                stalled += 1

            else:

                break

            if stalled >= self.stall_rounds:
                break

        return stalled

    # =========================================================
    # BUILD RESULT
    # =========================================================

    def _build_result(
        self,
        deadlock: bool,
        stalled_rounds: int,
        action: str,
        reason: str
    ) -> Dict[str, Any]:

        return {
            "deadlock": deadlock,
            "stalled_rounds": stalled_rounds,
            "threshold": self.stall_rounds,
            "action": action,
            "reason": reason
        }

    # =========================================================
    # SIMPLE BOOLEAN CHECK
    # =========================================================

    def is_deadlocked(
        self,
        history: List[Dict[str, Any]],
        status: str = "active"
    ) -> bool:
        """
        Simple True/False deadlock check.
        """

        result = self.check_deadlock(
            history=history,
            current_round=0,
            status=status
        )

        return result["deadlock"]