"""
Generate Search Queries AI Agent

An AI-powered agent that generates customer discovery search queries using Google's Gemini AI.
This agent analyzes product descriptions and generates natural, conversational search queries
that help identify potential customers who are actively seeking solutions.

Based on the TypeScript implementation in GENERATE_SEARCH_QUERIES_PLUGIN.md
"""

import json
import os
import re
from typing import List

import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Generate Search Queries Agent")


class GenerateQueriesRequest(BaseModel):
    """Request body for query generation."""

    productDescription: str


class GenerateQueriesResponse(BaseModel):
    """Response body from query generation."""

    success: bool
    queries: List[str] | None = None
    error: str | None = None
    message: str | None = None


# Initialize Gemini API
def get_gemini_model():
    """Initialize and return Gemini model."""
    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("VITE_GOOGLE_AI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY or VITE_GOOGLE_AI_API_KEY environment variable is not set")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model="gemini-2.5-flash")


def escape_control_characters_in_strings(json_string: str) -> str:
    """
    Escape control characters ONLY within string values (not in JSON structure).
    This regex finds quoted strings and escapes control characters inside them.
    """
    def escape_match(match):
        content = match.group(1)
        escaped = ""
        i = 0
        while i < len(content):
            char = content[i]
            code = ord(char)

            # Skip if already escaped
            if i > 0 and content[i - 1] == "\\":
                escaped += char
                i += 1
                continue

            # Escape control characters
            if code < 32:
                if code == 10:  # \n
                    escaped += "\\n"
                elif code == 13:  # \r
                    escaped += "\\r"
                elif code == 9:  # \t
                    escaped += "\\t"
                elif code == 12:  # \f
                    escaped += "\\f"
                elif code == 8:  # \b
                    escaped += "\\b"
                else:
                    escaped += f"\\u{code:04x}"
            else:
                escaped += char
            i += 1

        return f'"{escaped}"'

    return re.sub(r'"((?:[^"\\]|\\.)*)"', escape_match, json_string)


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON array from response, handling markdown code blocks.
    """
    json_string = response_text.strip()

    # Try to extract from markdown code blocks first
    json_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", response_text)
    if not json_match:
        # Fallback: try to find JSON array directly
        json_match = re.search(r"\[[\s\S]*?\]", response_text)

    if json_match:
        json_string = json_match.group(1) if json_match.lastindex else json_match.group(0)

    # Clean up the JSON string
    json_string = json_string.strip()
    json_string = re.sub(r"^[\s\n]*", "", json_string)
    json_string = re.sub(r"[\s\n]*$", "", json_string)

    return json_string


def parse_queries_from_response(response_text: str) -> List[str]:
    """
    Parse queries from Gemini response with multiple fallback strategies.
    """
    try:
        # Extract JSON from response
        json_string = extract_json_from_response(response_text)

        # Fix control characters in string values
        json_string = escape_control_characters_in_strings(json_string)

        # Try to parse JSON
        try:
            parsed = json.loads(json_string)
        except json.JSONDecodeError as parse_error:
            print(f"JSON parse error. Raw response: {response_text}")
            print(f"Extracted JSON string: {json_string}")
            print(f"Parse error details: {parse_error}")

            # Fallback: try to extract queries manually using regex
            query_matches = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', json_string)
            queries = []
            for match in query_matches:
                if match:
                    # Unescape the string
                    unescaped = (
                        match.replace("\\n", "\n")
                        .replace("\\r", "\r")
                        .replace("\\t", "\t")
                        .replace('\\"', '"')
                        .replace("\\\\", "\\")
                    )
                    if unescaped.strip():
                        queries.append(unescaped.strip())

            if queries:
                print(f"Using manually extracted queries: {queries}")
                return queries
            else:
                raise parse_error

        # Validate it's an array of strings
        if not isinstance(parsed, list):
            raise ValueError("Response is not an array")

        # Filter out invalid entries and ensure all are strings
        valid_queries = [
            q.strip()
            for q in parsed
            if isinstance(q, str) and q.strip()
        ][:5]  # Limit to max 5 queries

        return valid_queries

    except Exception as e:
        print(f"Error parsing queries: {e}")
        raise


def generate_fallback_queries(product_description: str) -> List[str]:
    """Generate fallback queries if AI generation fails."""
    desc_snippet = product_description[:50]
    return [
        f"looking for {desc_snippet}",
        f"need help with {desc_snippet}",
        f"struggling with {desc_snippet}",
    ]


def create_prompt(product_description: str) -> str:
    """Create the prompt for Gemini to generate search queries."""
    return f"""Analyze the following product/service description and generate 3-5 search queries that would help find potential customers who are actively seeking this solution or experiencing related pain points.

**Product/Service Description:**
{product_description}

**Instructions:**
1. Identify the core problem this product/service solves
2. Think about how potential customers might express their pain points, frustrations, or needs
3. Generate search queries that capture:
   - People asking questions about the problem domain
   - People expressing frustration with existing solutions
   - People seeking recommendations or alternatives
   - People discussing challenges related to this domain
   - People showing buying intent or solution-seeking behavior

4. Each query should be:
   - Natural and conversational (as someone might type on Reddit/X)
   - Focused on pain points or solution-seeking
   - Specific to the product's domain/industry
   - Not too generic or too narrow

5. Avoid:
   - Brand names or specific product names
   - Overly technical jargon
   - Queries that are too broad (e.g., just "help" or "problem")

**Example:**
If product is "AI-powered lead generation tool for SaaS founders":
- Good queries: "finding first customers", "struggling to find leads", "looking for lead generation tools", "how to find customers on reddit"
- Bad queries: "lead generation" (too generic), "ralix.ai" (brand name), "SaaS" (too broad)

Return ONLY a JSON array of query strings, like this:
["query 1", "query 2", "query 3", "query 4", "query 5"]

Do not include any explanation or additional text, only the JSON array."""


@app.post("/GenerateSearchQueries", response_model=GenerateQueriesResponse)
async def generate_search_queries(request: GenerateQueriesRequest) -> GenerateQueriesResponse:
    """
    Generate search queries from a product description using Google Gemini AI.

    This endpoint:
    1. Validates the input
    2. Calls Gemini AI to generate queries
    3. Parses the response with multiple fallback strategies
    4. Returns formatted queries or fallback queries if parsing fails
    """
    # Validate required parameters
    if not request.productDescription:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Missing required parameters",
                "message": "productDescription is required",
            },
        )

    try:
        # Get Gemini model
        try:
            model = get_gemini_model()
        except ValueError as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "API key not configured",
                    "message": str(e),
                },
            )

        # Generate search queries using Gemini
        prompt = create_prompt(request.productDescription)
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        print(f"Gemini API Response for query generation: {response_text}")

        # Parse queries from response
        try:
            queries = parse_queries_from_response(response_text)
        except Exception as parse_error:
            print(f"Failed to parse queries: {parse_error}")
            # Use fallback queries
            queries = generate_fallback_queries(request.productDescription)
            print(f"Using fallback queries: {queries}")

        if not queries:
            # Final fallback if parsing returned empty list
            queries = generate_fallback_queries(request.productDescription)
            print(f"No valid queries generated, using fallback queries: {queries}")

        return GenerateQueriesResponse(success=True, queries=queries)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating search queries: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to generate search queries",
                "message": str(e),
            },
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)

