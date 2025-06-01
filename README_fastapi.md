# Gemini Deep Research Agent - FastAPI Version

A powerful FastAPI-based AI agent that performs comprehensive web research using Google's Gemini and Firecrawl technologies.

## Features

- **RESTful API**: Clean REST endpoints for research operations
- **Asynchronous Processing**: Non-blocking research with status tracking
- **Dual Research Modes**: Both synchronous and asynchronous research
- **Enhanced Reports**: Optional report enhancement with additional insights
- **Progress Tracking**: Real-time status updates for long-running research
- **Report Download**: Export research reports in Markdown format
- **Configurable Parameters**: Customizable research depth, time limits, and URL counts

## Installation

1. Install dependencies:
```bash
pip install -r requirements_fastapi.txt
```

2. Set up your API keys:
   - Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Get a Firecrawl API key from [Firecrawl](https://firecrawl.dev)

## Usage

### Starting the API Server

```bash
python deep_research_fastapi.py
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Using the Client

```python
from client_example import DeepResearchClient
import os

# Initialize client
client = DeepResearchClient("http://localhost:8000")

# Configure API keys
client.configure_api_keys(
    gemini_api_key=os.getenv("GEMINI_API_KEY"),
    firecrawl_api_key=os.getenv("FIRECRAWL_API_KEY")
)

# Start asynchronous research
research_id = client.start_research(
    topic="Latest developments in AI",
    max_depth=3,
    time_limit=180,
    max_urls=10,
    enhance_report=True
)

# Wait for completion and get results
results = client.wait_for_research_completion(research_id)
print(results["enhanced_report"])
```

## API Endpoints

### Configuration
- `POST /configure` - Configure API keys

### Research Operations
- `POST /research` - Start asynchronous research
- `POST /research/sync` - Perform synchronous research
- `GET /research/{research_id}/status` - Get research status
- `GET /research/{research_id}/results` - Get research results
- `GET /research/{research_id}/download` - Download research report
- `GET /research` - List all research processes

### Health Check
- `GET /health` - Service health check

## Request/Response Models

### Research Request
```json
{
  "topic": "string",
  "max_depth": 3,
  "time_limit": 180,
  "max_urls": 10,
  "enhance_report": true
}
```

### Research Response
```json
{
  "success": true,
  "research_id": "uuid",
  "topic": "string",
  "initial_report": "string",
  "enhanced_report": "string",
  "sources_count": 10,
  "sources": [...],
  "error": null
}
```

## Environment Variables

Set these environment variables for easier configuration:

```bash
export GEMINI_API_KEY="your-gemini-api-key"
export FIRECRAWL_API_KEY="your-firecrawl-api-key"
```

## Production Deployment

For production deployment, consider:

1. **Security**: Implement proper authentication and rate limiting
2. **Storage**: Replace in-memory storage with Redis or database
3. **Scaling**: Use multiple workers with a load balancer
4. **Monitoring**: Add logging, metrics, and health checks
5. **Configuration**: Use environment-based configuration

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements_fastapi.txt .
RUN pip install -r requirements_fastapi.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "deep_research_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t deep-research-api .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your-key \
  -e FIRECRAWL_API_KEY=your-key \
  deep-research-api
```

## Comparison with Streamlit Version

| Feature | Streamlit Version | FastAPI Version |
|---------|------------------|-----------------|
| Interface | Web UI | REST API |
| Integration | Standalone app | Service/microservice |
| Scalability | Single user | Multiple concurrent users |
| Deployment | Simple | Production-ready |
| Real-time updates | Live UI updates | Polling/webhooks |
| Client support | Web browser only | Any HTTP client |

## Error Handling

The API includes comprehensive error handling:

- **400 Bad Request**: Invalid parameters or missing configuration
- **404 Not Found**: Research ID not found
- **500 Internal Server Error**: Unexpected errors during processing

## Rate Limiting Considerations

Be mindful of API rate limits:
- **Gemini API**: Check Google's current rate limits
- **Firecrawl API**: Depends on your plan

## Troubleshooting

1. **Agent not initialized**: Make sure to call `/configure` endpoint first
2. **Research timeouts**: Increase `time_limit` parameter
3. **Memory usage**: In production, implement proper storage backends
4. **API key errors**: Verify your API keys are valid and have sufficient credits

## Contributing

Feel free to submit issues and enhancement requests!
