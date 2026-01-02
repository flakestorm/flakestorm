# Generate Search Queries AI Agent

## Overview

The `generateSearchQueriesPlugin` is an **AI-powered agent** that provides an API endpoint for generating customer discovery search queries. This agent autonomously analyzes product descriptions using Google's Gemini AI and generates natural, conversational search queries that help identify potential customers who are actively seeking solutions or experiencing related pain points.

### Terminology

> **Agent vs Plugin**: While this is technically implemented as a Vite development server plugin (for development integration), it functions as an **autonomous AI agent** that:
> - Makes intelligent decisions about query generation
> - Autonomously handles errors and implements fallback strategies
> - Adapts to different product types and industries
> - Provides intelligent responses based on context
>
> In production, this should be moved to a dedicated backend agent service, similar to other AI agents in the Ralix ecosystem (like the main Ralix Marketing Co-Founder agent).

## Purpose

This AI agent automates the creation of search queries for lead generation by:
- Analyzing product/service descriptions to understand the core problem being solved
- Generating 3-5 natural, conversational search queries that potential customers might use
- Focusing on pain points, solution-seeking behavior, and buying intent
- Optimizing queries for platforms like Reddit and X (Twitter)

## How It Works

1. **Endpoint Creation**: The agent creates a middleware endpoint at `/GenerateSearchQueries` in the Vite development server
2. **Request Processing**: Accepts POST requests with a product description
3. **AI Analysis**: The agent autonomously uses Google Gemini 2.5 Flash model to analyze the product and generate queries
4. **Response Parsing**: The agent intelligently extracts and validates the generated queries from the AI response
5. **Error Handling**: The agent includes robust fallback mechanisms and autonomous decision-making for malformed responses

## API Endpoint

### Endpoint
```
POST /GenerateSearchQueries
```

### Request Format

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "productDescription": "Your product or service description here"
}
```

### Response Format

**Success Response (200):**
```json
{
  "success": true,
  "queries": [
    "query 1",
    "query 2",
    "query 3",
    "query 4",
    "query 5"
  ]
}
```

**Error Responses:**

**400 Bad Request** - Missing required parameter:
```json
{
  "error": "Missing required parameters",
  "message": "productDescription is required"
}
```

**500 Internal Server Error** - API key not configured:
```json
{
  "error": "API key not configured",
  "message": "VITE_GOOGLE_AI_API_KEY environment variable is not set"
}
```

**500 Internal Server Error** - Generation failed:
```json
{
  "error": "Failed to generate search queries",
  "message": "Error details here"
}
```

## Configuration

### Environment Variables

The AI agent requires the following environment variable:

- **`VITE_GOOGLE_AI_API_KEY`**: Your Google Generative AI API key for accessing Gemini models

Set this in your `.env` file:
```
VITE_GOOGLE_AI_API_KEY=your_api_key_here
```

### Agent Registration (Technical Implementation)

The agent is implemented as a Vite plugin and automatically registered in `vite.config.ts`:

```typescript
plugins: [
  react(),
  securityHeaders(),
  generateSearchQueriesPlugin(mode),
  // ...
]
```

## Query Generation Strategy

The AI agent is instructed to autonomously generate queries that:

### ✅ Good Query Characteristics
- Natural and conversational (as someone might type on Reddit/X)
- Focused on pain points or solution-seeking
- Specific to the product's domain/industry
- Not too generic or too narrow
- Capture people asking questions, expressing frustrations, or seeking recommendations

### ❌ What to Avoid
- Brand names or specific product names
- Overly technical jargon
- Queries that are too broad (e.g., just "help" or "problem")

### Example

**Input:**
```
"AI-powered lead generation tool for SaaS founders"
```

**Good Output:**
- "finding first customers"
- "struggling to find leads"
- "looking for lead generation tools"
- "how to find customers on reddit"

**Bad Output:**
- "lead generation" (too generic)
- "ralix.ai" (brand name)
- "SaaS" (too broad)

## Error Handling & Fallbacks

The AI agent includes multiple layers of autonomous error handling:

1. **JSON Parsing**: The agent intelligently handles markdown code blocks and extracts JSON arrays
2. **Control Character Escaping**: The agent autonomously escapes control characters in string values
3. **Regex Fallback**: If JSON parsing fails, the agent uses regex to extract quoted strings
4. **Default Queries**: If all parsing fails, the agent autonomously generates basic fallback queries from the product description

### Fallback Queries

If the AI fails to generate valid queries, the agent autonomously creates three basic queries:
- `"looking for [first 50 chars of product description]"`
- `"need help with [first 50 chars of product description]"`
- `"struggling with [first 50 chars of product description]"`

## Use Cases

1. **Lead Generation Setup**: Automatically generate search queries when users set up their product/service
2. **Campaign Creation**: Pre-populate search queries for new lead generation campaigns
3. **Query Optimization**: Get AI-suggested queries that are more likely to find qualified leads
4. **Onboarding Flow**: Help new users quickly get started with lead generation

## Technical Details

### AI Model
- **Model**: `gemini-2.5-flash`
- **Provider**: Google Generative AI
- **Library**: `@google/generative-ai`

### Response Processing
1. Extracts JSON from markdown code blocks (if present)
2. Cleans whitespace and newlines
3. Escapes control characters in string values
4. Validates array structure
5. Filters and limits to maximum 5 queries

### Development vs Production

- **Development**: Agent runs as Vite middleware, accessible at `http://localhost:8080/GenerateSearchQueries`
- **Production**: This agent should be moved to a dedicated backend service/agent endpoint (e.g., Cloudflare Worker or FastAPI endpoint) as Vite plugins only work in development mode. In production, it should function as a standalone AI agent service.

## Example Usage

### JavaScript/TypeScript

```typescript
const response = await fetch('/GenerateSearchQueries', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    productDescription: 'AI-powered lead generation tool for SaaS founders'
  })
});

const data = await response.json();

if (data.success) {
  console.log('Generated queries:', data.queries);
  // ["finding first customers", "struggling to find leads", ...]
} else {
  console.error('Error:', data.error);
}
```

### cURL

```bash
curl -X POST http://localhost:8080/GenerateSearchQueries \
  -H "Content-Type: application/json" \
  -d '{"productDescription": "AI-powered lead generation tool for SaaS founders"}'
```

## Limitations

1. **Development Only**: This agent is currently implemented as a Vite plugin and only works in development mode. For production, implement this as a dedicated backend agent service.
2. **API Key Required**: The agent requires a valid Google AI API key with access to Gemini models
3. **Rate Limits**: Subject to Google AI API rate limits
4. **Query Count**: The agent is limited to generating a maximum of 5 queries per request

## Future Improvements

- Move agent to dedicated backend service for production use
- Add intelligent caching for frequently requested product descriptions
- Support for custom query generation strategies that the agent can learn from
- Integration with actual search platforms (Reddit, X) for autonomous query validation
- Analytics on query performance to help the agent improve over time
- Agent learning capabilities to refine query generation based on successful lead conversions

## Related Documentation

- [Vite Plugin Development](https://vitejs.dev/guide/api-plugin.html)
- [Google Generative AI Documentation](https://ai.google.dev/docs)
- [Lead Generation System Architecture](../docs/ARCHITECTURE_DECISION_FASTAPI.md)

## Agent Code

```typescript
// GenerateSearchQueries API endpoint plugin
function generateSearchQueriesPlugin(mode: string): Plugin {
  return {
    name: 'generate-search-queries-api',
    configureServer(server) {
      // Load environment variables
      const env = loadEnv(mode, process.cwd(), '');
      
      server.middlewares.use('/GenerateSearchQueries', async (req, res, next) => {
        // Only handle POST requests
        if (req.method !== 'POST') {
          return next();
        }

        try {
          // Read request body
          let body = '';
          req.on('data', (chunk) => {
            body += chunk.toString();
          });

          req.on('end', async () => {
            try {
              const { productDescription } = JSON.parse(body);

              // Validate required parameters
              if (!productDescription) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                  error: 'Missing required parameters',
                  message: 'productDescription is required',
                }));
                return;
              }

              // Get Google AI API key from environment
              const apiKey = env.VITE_GOOGLE_AI_API_KEY || process.env.VITE_GOOGLE_AI_API_KEY;
              if (!apiKey) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                  error: 'API key not configured',
                  message: 'VITE_GOOGLE_AI_API_KEY environment variable is not set',
                }));
                return;
              }

              // Initialize Gemini API
              const genAI = new GoogleGenerativeAI(apiKey);
              const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });

              // Generate search queries using the same prompt as GeminiAPI.generateSearchQueries
              const prompt = `Analyze the following product/service description and generate 3-5 search queries that would help find potential customers who are actively seeking this solution or experiencing related pain points.

**Product/Service Description:**
${productDescription}

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

Do not include any explanation or additional text, only the JSON array.`;

              const result = await model.generateContent(prompt);
              const response = await result.response;
              const responseText = response.text().trim();

              console.log('Gemini API Response for query generation:', responseText);
              
              // Extract JSON array from response - handle markdown code blocks
              let jsonString = responseText;
              
              // Try to extract from markdown code blocks first
              const jsonMatch = responseText.match(/```(?:json)?\s*(\[[\s\S]*?\])\s*```/) || 
                               responseText.match(/\[[\s\S]*?\]/);
              
              if (jsonMatch) {
                jsonString = jsonMatch[1] || jsonMatch[0];
              }
              
              // Clean up the JSON string
              jsonString = jsonString.trim();
              
              // Remove any leading/trailing whitespace or newlines
              jsonString = jsonString.replace(/^[\s\n]*/, '').replace(/[\s\n]*$/, '');
              
              // Fix control characters ONLY within string values (not in JSON structure)
              // This regex finds quoted strings and escapes control characters inside them
              jsonString = jsonString.replace(/"((?:[^"\\]|\\.)*)"/g, (match, content) => {
                // Escape control characters that aren't already escaped
                let escaped = '';
                for (let i = 0; i < content.length; i++) {
                  const char = content[i];
                  const code = char.charCodeAt(0);
                  
                  // Skip if already escaped
                  if (i > 0 && content[i - 1] === '\\') {
                    escaped += char;
                    continue;
                  }
                  
                  // Escape control characters
                  if (code < 32) {
                    if (code === 10) escaped += '\\n';      // \n
                    else if (code === 13) escaped += '\\r'; // \r
                    else if (code === 9) escaped += '\\t';  // \t
                    else if (code === 12) escaped += '\\f'; // \f
                    else if (code === 8) escaped += '\\b';  // \b
                    else escaped += '\\u' + code.toString(16).padStart(4, '0');
                  } else {
                    escaped += char;
                  }
                }
                return `"${escaped}"`;
              });
              
              let parsed;
              try {
                parsed = JSON.parse(jsonString);
              } catch (parseError) {
                console.error('JSON parse error. Raw response:', responseText);
                console.error('Extracted JSON string:', jsonString);
                console.error('Parse error details:', parseError);
                
                // Fallback: try to extract queries manually using regex
                // This is more lenient and handles malformed JSON
                try {
                  const queryMatches = Array.from(jsonString.matchAll(/"([^"\\]*(?:\\.[^"\\]*)*)"/g));
                  const queries: string[] = [];
                  for (const match of queryMatches) {
                    if (match[1]) {
                      // Unescape the string
                      const unescaped = match[1]
                        .replace(/\\n/g, '\n')
                        .replace(/\\r/g, '\r')
                        .replace(/\\t/g, '\t')
                        .replace(/\\"/g, '"')
                        .replace(/\\\\/g, '\\');
                      if (unescaped.trim()) {
                        queries.push(unescaped.trim());
                      }
                    }
                  }
                  
                  if (queries.length > 0) {
                    console.log('Using manually extracted queries:', queries);
                    parsed = queries;
                  } else {
                    throw parseError;
                  }
                } catch (fallbackError) {
                  throw new Error(`Invalid JSON response from Gemini: ${parseError instanceof Error ? parseError.message : 'Unknown error'}`);
                }
              }
              
              // Validate it's an array of strings
              if (!Array.isArray(parsed)) {
                throw new Error('Response is not an array');
              }
              
              // Filter out invalid entries and ensure all are strings
              const validQueries = parsed
                .filter((q) => typeof q === 'string' && q.trim().length > 0)
                .map((q) => q.trim())
                .slice(0, 5); // Limit to max 5 queries
              
              if (validQueries.length === 0) {
                console.warn('No valid queries generated, using fallback queries');
                // Fallback: generate basic queries from product description
                const fallbackQueries = [
                  `looking for ${productDescription.substring(0, 50)}`,
                  `need help with ${productDescription.substring(0, 50)}`,
                  `struggling with ${productDescription.substring(0, 50)}`
                ];
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                  success: true,
                  queries: fallbackQueries,
                }));
                return;
              }

              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({
                success: true,
                queries: validQueries,
              }));
            } catch (error) {
              console.error('Error generating search queries:', error);
              res.writeHead(500, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({
                error: 'Failed to generate search queries',
                message: error instanceof Error ? error.message : 'Unknown error',
              }));
            }
          });
        } catch (error) {
          console.error('Error handling request:', error);
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            error: 'Failed to process request',
            message: error instanceof Error ? error.message : 'Unknown error',
          }));
        }
      });
    }
  };
}
```