# AI-vs-AI Frontend Integration

This version adds an **AI vs AI** mode to the existing Negotiation Arena without removing the existing **Human vs AI** practice mode.

## What changed

- Added a Human vs AI / AI vs AI mode switch.
- Added separate Buyer AI and Seller AI personality selectors.
- Connected AI-vs-AI mode to `POST /api/negotiations`.
- Displays the returned multi-agent negotiation history as a chat transcript.
- Extracts and displays offer values from AI messages.
- Displays final status and agreed price.
- Added AI-vs-AI metrics for latest buyer/seller offers.
- Added a multi-agent pipeline panel explaining Orchestrator, Reasoning Engine, Counteroffer Evaluator and Deadlock Detector.
- Preserved the existing Human vs AI endpoints and interaction.

## Run

### Terminal 1 - backend

```powershell
python -m uvicorn main:app --reload
```

### Terminal 2 - frontend

```powershell
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`.

## AI-vs-AI demo flow

1. Select **AI vs AI**.
2. Select scenario and property.
3. Choose Buyer AI personality.
4. Choose Seller AI personality.
5. Set maximum rounds.
6. Click **Start AI simulation**.
7. The frontend calls `POST /api/negotiations`.
8. The backend runs the autonomous Buyer/Seller negotiation.
9. The transcript displays the returned agent messages.
10. The final status and agreed price are shown in the result/metrics area.
