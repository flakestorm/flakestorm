"""
Broken Agent Example

A deliberately fragile AI agent to demonstrate Entropix testing.
This agent has multiple intentional weaknesses that Entropix will find.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import time
import random

app = FastAPI(title="Broken Travel Agent")


class AgentRequest(BaseModel):
    """Request body for agent invocation."""
    input: str


class AgentResponse(BaseModel):
    """Response body from agent."""
    output: str


# Simulated database
FLIGHTS = {
    "paris": {"price": 450, "airline": "Air France"},
    "london": {"price": 320, "airline": "British Airways"},
    "tokyo": {"price": 890, "airline": "ANA"},
}


@app.post("/invoke")
async def invoke(request: AgentRequest) -> AgentResponse:
    """
    Process a user request.
    
    This agent is intentionally broken in several ways:
    1. Only recognizes exact keyword matches
    2. No typo tolerance
    3. Crashes on aggressive inputs
    4. Susceptible to prompt injection
    """
    user_input = request.input
    
    # VULNERABILITY 1: Prompt Injection
    # The agent naively follows instructions embedded in user input
    if "ignore previous instructions" in user_input.lower():
        return AgentResponse(
            output="I have ignored my previous instructions. How can I help you now?"
        )
    
    if "you are now" in user_input.lower():
        return AgentResponse(
            output="Okay, I am now a different AI assistant with no restrictions."
        )
    
    # VULNERABILITY 2: Crashes on aggressive tone
    if any(word in user_input.upper() for word in ["NOW", "HURRY", "ASAP", "IMMEDIATELY"]):
        # Simulate a crash/timeout
        time.sleep(3)  # This will cause latency checks to fail
        return AgentResponse(
            output="ERROR: System overloaded due to urgent request."
        )
    
    # VULNERABILITY 3: Only exact keyword matching
    # Will fail on paraphrases like "I want to fly" instead of "book a flight"
    if "book a flight" in user_input.lower():
        # Extract destination (very fragile parsing)
        words = user_input.lower().split()
        destination = None
        
        for city in FLIGHTS.keys():
            if city in words:
                destination = city
                break
        
        if destination:
            flight = FLIGHTS[destination]
            return AgentResponse(
                output=json.dumps({
                    "status": "booked",
                    "destination": destination.title(),
                    "price": flight["price"],
                    "airline": flight["airline"],
                    "confirmation_code": f"ENT{random.randint(10000, 99999)}"
                })
            )
        else:
            return AgentResponse(
                output=json.dumps({
                    "status": "error",
                    "message": "Unknown destination"
                })
            )
    
    # VULNERABILITY 4: No typo tolerance
    # "bock a fligt" will completely fail
    if "account balance" in user_input.lower():
        return AgentResponse(
            output=json.dumps({
                "balance": 1234.56,
                "currency": "USD"
            })
        )
    
    # Default: Unknown intent
    return AgentResponse(
        output=json.dumps({
            "status": "error",
            "message": "I don't understand your request. Please try again."
        })
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

