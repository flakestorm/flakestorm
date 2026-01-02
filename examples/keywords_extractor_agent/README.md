# Generate Search Queries Agent Example

This example demonstrates a real-world AI agent that generates customer discovery search queries using Google's Gemini AI. This agent is designed to be tested with flakestorm to ensure it handles various input mutations robustly.

## Overview

The agent accepts product/service descriptions and generates 3-5 natural, conversational search queries that potential customers might use when seeking solutions. It uses Google Gemini 2.5 Flash model for intelligent query generation.

## Features

- **AI-Powered Query Generation**: Uses Google Gemini to analyze product descriptions and generate relevant search queries
- **Robust Error Handling**: Multiple fallback strategies for parsing AI responses
- **Natural Language Processing**: Generates queries that sound like real user searches on Reddit/X
- **Production-Ready**: Includes comprehensive error handling and validation

## Setup

### 1. Create Virtual Environment (Recommended)

It's recommended to use a virtual environment to avoid dependency conflicts:

```bash
cd examples/keywords_extractor_agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows (PowerShell):
# venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
# venv\Scripts\activate.bat
```

**Note:** You should see `(venv)` in your terminal prompt after activation.

### 2. Install Dependencies

```bash
# Make sure virtual environment is activated
pip install -r requirements.txt

# Or install manually:
# pip install fastapi uvicorn google-generativeai pydantic
```

### 3. Set Up Google AI API Key

You need a Google AI API key to use Gemini. Get one from [Google AI Studio](https://makersuite.google.com/app/apikey).

Set the environment variable:

```bash
# On macOS/Linux
export GOOGLE_AI_API_KEY=your_api_key_here

# On Windows (PowerShell)
$env:GOOGLE_AI_API_KEY="your_api_key_here"

# Or create a .env file (not recommended for production)
echo "GOOGLE_AI_API_KEY=your_api_key_here" > .env
```

**Note:** The agent also checks for `VITE_GOOGLE_AI_API_KEY` for compatibility with the original TypeScript implementation.

### 4. Start the Agent Server

**Make sure your virtual environment is activated** (you should see `(venv)` in your prompt):

```bash
python agent.py
```

Or using uvicorn directly:

```bash
uvicorn agent:app --port 8080
```

The agent will be available at `http://localhost:8080/GenerateSearchQueries`

**To deactivate the virtual environment when done:**
```bash
deactivate
```

## Testing the Agent

### Manual Test

```bash
curl -X POST http://localhost:8080/GenerateSearchQueries \
  -H "Content-Type: application/json" \
  -d '{"productDescription": "AI-powered lead generation tool for SaaS founders"}'
```

Expected response:
```json
{
  "success": true,
  "queries": [
    "finding first customers",
    "struggling to find leads",
    "looking for lead generation tools",
    "how to find customers on reddit"
  ]
}
```

### Run flakestorm Against It

```bash
# From the project root
flakestorm run --config examples/keywords_extractor_agent/flakestorm.yaml
```

This will:
1. Generate mutations of the golden prompts (product descriptions)
2. Test the agent's robustness against various input variations
3. Generate an HTML report showing pass/fail results

## How It Works

1. **Request Processing**: Accepts POST requests with `productDescription` in JSON body
2. **AI Analysis**: Uses Google Gemini 2.5 Flash to analyze the product and generate queries
3. **Response Parsing**: Intelligently extracts JSON array from AI response with multiple fallback strategies:
   - Extracts from markdown code blocks
   - Handles control character escaping
   - Regex fallback for malformed JSON
   - Default queries if all parsing fails
4. **Validation**: Ensures queries are valid strings and limits to 5 queries

## Error Handling

The agent includes robust error handling:

- **Missing API Key**: Returns 500 error with clear message
- **Invalid Input**: Returns 400 error for missing productDescription
- **JSON Parsing Failures**: Uses regex fallback to extract queries
- **Empty Results**: Generates fallback queries from product description
- **API Failures**: Returns 500 error with error details

## Configuration

The `flakestorm.yaml` file is configured to test this agent with:
- **Endpoint**: `http://localhost:8080/GenerateSearchQueries`
- **Request Format**: Maps golden prompts to `{"productDescription": "{prompt}"}`
- **Response Extraction**: Extracts the `queries` array from the response (flakestorm converts arrays to JSON strings for assertions)
- **Golden Prompts**: Various product/service descriptions
- **Mutations**: All 7 mutation types (paraphrase, noise, tone_shift, prompt_injection, encoding_attacks, context_manipulation, length_extremes)
- **Invariants**: 
  - Valid JSON response
  - Latency under 10 seconds (allows for Gemini API call)
  - Response contains array of queries
  - PII exclusion checks
  - Refusal checks for prompt injections

## Example Golden Prompts

The agent is tested with prompts like:
- "AI-powered lead generation tool for SaaS founders..."
- "Personal finance app that tracks expenses..."
- "Fitness app with AI personal trainer..."
- "E-commerce platform for small businesses..."

flakestorm will generate mutations of these to test robustness.

## Limitations

1. **API Key Required**: Needs valid Google AI API key
2. **Rate Limits**: Subject to Google AI API rate limits
3. **Query Count**: Limited to maximum 5 queries per request
4. **Model Dependency**: Requires internet connection for Gemini API calls

## Future Improvements

- Add caching for frequently requested product descriptions
- Support for custom query generation strategies
- Integration with actual search platforms for validation
- Analytics on query performance
- Agent learning capabilities based on successful conversions

