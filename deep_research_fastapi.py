import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from firecrawl import FirecrawlApp
import logging
from contextlib import asynccontextmanager

from agno.agent import Agent
from agno.models.google import Gemini

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for agents
research_agent: Optional[Agent] = None
elaboration_agent: Optional[Agent] = None
firecrawl_app: Optional[FirecrawlApp] = None

# Pydantic models for request/response
class APIKeys(BaseModel):
    gemini_api_key: str = Field(..., description="Gemini API key for the language model")
    firecrawl_api_key: str = Field(..., description="Firecrawl API key for web research")

class ResearchRequest(BaseModel):
    topic: str = Field(..., description="Research topic to investigate", min_length=1)
    max_depth: int = Field(default=3, description="Maximum depth for research", ge=1, le=5)
    time_limit: int = Field(default=180, description="Time limit in seconds", ge=30, le=600)
    max_urls: int = Field(default=10, description="Maximum URLs to research", ge=1, le=50)
    enhance_report: bool = Field(default=True, description="Whether to enhance the report with additional information")

class ResearchResponse(BaseModel):
    success: bool
    research_id: str
    topic: str
    initial_report: Optional[str] = None
    enhanced_report: Optional[str] = None
    sources_count: Optional[int] = None
    sources: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

class ResearchStatus(BaseModel):
    research_id: str
    status: str  # "pending", "researching", "enhancing", "completed", "error"
    progress: str
    current_step: str

class DeepResearchResult(BaseModel):
    success: bool
    final_analysis: Optional[str] = None
    sources_count: Optional[int] = None
    sources: Optional[List[Dict[str, Any]]] = None
    activities: Optional[List[str]] = None
    error: Optional[str] = None

# In-memory storage for research status (in production, use Redis or database)
research_status_store: Dict[str, ResearchStatus] = {}
research_results_store: Dict[str, ResearchResponse] = {}

# Deep research function
async def deep_research(query: str, max_depth: int = 3, time_limit: int = 180, max_urls: int = 10) -> DeepResearchResult:
    """
    Perform comprehensive web research using Firecrawl's deep research endpoint.
    """
    try:
        if not firecrawl_app:
            raise Exception("Firecrawl not initialized. Please configure API keys first.")
        
        # Activity tracking for progress updates
        activities = []
        def on_activity(activity):
            activities.append(f"[{activity['type']}] {activity['message']}")
            logger.info(f"Research activity: [{activity['type']}] {activity['message']}")
        
        # Run deep research
        logger.info(f"Starting deep research for query: {query}")
        results = firecrawl_app.deep_research(
            query=query,
            max_depth= max_depth,
            time_limit = time_limit,
            max_urls = max_urls,
            on_activity=on_activity
        )
        
        return DeepResearchResult(
            success=True,
            final_analysis=results['data']['finalAnalysis'],
            sources_count=len(results['data']['sources']),
            activities=activities,
            sources=results['data']['sources']
        )
    except Exception as e:
        logger.error(f"Deep research error: {str(e)}")
        return DeepResearchResult(success=False, error=str(e))

# Create agents function
def create_agents(gemini_api_key: str):
    """Create research and elaboration agents with Gemini model."""
    global research_agent, elaboration_agent
    
    gemini_model = Gemini(id="gemini-2.0-flash", api_key=gemini_api_key)
    
    research_agent = Agent(
        name="research_agent",
        model=gemini_model,
        instructions="""You are a research assistant that can perform deep web research on any topic.

        When given a research topic or question:
        1. Call the deep_research function to gather comprehensive information
           - Use the provided parameters: max_depth, time_limit, max_urls
        2. The function will search the web, analyze multiple sources, and provide a synthesis
        3. Review the research results and organize them into a well-structured report
        4. Include proper citations for all sources
        5. Highlight key findings and insights
        6. Structure the report with clear sections: Executive Summary, Key Findings, Detailed Analysis, Conclusions
        """,
        tools=[deep_research]
    )

    elaboration_agent = Agent(
        name="elaboration_agent",
        model=gemini_model,
        instructions="""You are an expert content enhancer specializing in research elaboration.

        When given a research report:
        1. Analyze the structure and content of the report
        2. Enhance the report by:
           - Adding more detailed explanations of complex concepts
           - Including relevant examples, case studies, and real-world applications
           - Expanding on key points with additional context and nuance
           - Adding visual elements descriptions (charts, diagrams, infographics)
           - Incorporating latest trends and future predictions
           - Suggesting practical implications for different stakeholders
        3. Maintain academic rigor and factual accuracy
        4. Preserve the original structure while making it more comprehensive
        5. Ensure all additions are relevant and valuable to the topic
        6. Add actionable insights and recommendations where appropriate
        """
    )
    
    logger.info("Agents created successfully")

# Research process function
async def run_research_process(
    research_id: str, 
    topic: str, 
    max_depth: int = 3, 
    time_limit: int = 180, 
    max_urls: int = 10,
    enhance_report: bool = True
):
    """Run the complete research process."""
    try:
        if not research_agent:
            raise Exception("Research agent not initialized. Please configure API keys first.")
        
        # Update status
        research_status_store[research_id].status = "researching"
        research_status_store[research_id].current_step = "Conducting initial research"
        
        # Step 1: Initial Research
        logger.info(f"Starting initial research for topic: {topic}")
        initial_agent_response = await research_agent.arun(
            f"Research this topic thoroughly: {topic}. Use max_depth={max_depth}, time_limit={time_limit}, max_urls={max_urls}"
        )
        initial_report = initial_agent_response.content # Extract content
        
        enhanced_report_content = initial_report
        
        if enhance_report and elaboration_agent:
            # Update status
            research_status_store[research_id].status = "enhancing"
            research_status_store[research_id].current_step = "Enhancing report with additional information"
            
            # Step 2: Enhance the report
            logger.info("Enhancing the research report")
            elaboration_input = f"""
            RESEARCH TOPIC: {topic}
            
            INITIAL RESEARCH REPORT:
            {initial_report}
            
            Please enhance this research report with additional information, examples, case studies, 
            and deeper insights while maintaining its academic rigor and factual accuracy.
            """
            
            enhanced_agent_response = await elaboration_agent.arun(elaboration_input)
            enhanced_report_content = enhanced_agent_response.content # Extract content
        
        # Store results
        research_results_store[research_id] = ResearchResponse(
            
            success=True,
            research_id=research_id,
            topic=topic,
            initial_report=initial_report,
            enhanced_report=enhanced_report_content if enhance_report else None
        )
        
        # Update status
        research_status_store[research_id].status = "completed"
        research_status_store[research_id].current_step = "Research completed successfully"
        
        logger.info(f"Research process completed for research_id: {research_id}")
        
    except Exception as e:
        logger.error(f"Research process error: {str(e)}")
        research_status_store[research_id].status = "error"
        research_status_store[research_id].current_step = f"Error: {str(e)}"
        research_results_store[research_id] = ResearchResponse(
            success=False,
            research_id=research_id,
            topic=topic,
            error=str(e)
        )

# FastAPI application with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Gemini Deep Research Agent API")
    yield
    # Shutdown
    logger.info("Shutting down Gemini Deep Research Agent API")

app = FastAPI(
    title="Gemini Deep Research Agent API",
    description="FastAPI-powered AI Agent for deep research using Gemini and Firecrawl",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Gemini Deep Research Agent API"}

# Configure API keys
@app.post("/configure")
async def configure_api_keys(api_keys: APIKeys):
    """Configure API keys for Gemini and Firecrawl services."""
    try:
        global firecrawl_app
        
        # Initialize Firecrawl
        firecrawl_app = FirecrawlApp(api_key=api_keys.firecrawl_api_key)
        
        # Create agents
        create_agents(api_keys.gemini_api_key)
        
        logger.info("API keys configured successfully")
        return {"success": True, "message": "API keys configured successfully"}
    except Exception as e:
        logger.error(f"Configuration error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Configuration error: {str(e)}")

# Start research endpoint
@app.post("/research", response_model=Dict[str, str])
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Start a new research process."""
    try:
        if not research_agent or not firecrawl_app:
            raise HTTPException(
                status_code=400, 
                detail="API keys not configured. Please call /configure endpoint first."
            )
        
        # Generate research ID
        import uuid
        research_id = str(uuid.uuid4())
        
        # Initialize status
        research_status_store[research_id] = ResearchStatus(
            research_id=research_id,
            status="pending",
            progress="Research queued",
            current_step="Initializing research process"
        )
        
        # Start research process in background
        background_tasks.add_task(
            run_research_process,
            research_id,
            request.topic,
            request.max_depth,
            request.time_limit,
            request.max_urls,
            request.enhance_report
        )
        
        logger.info(f"Research started with ID: {research_id}")
        return {
            "research_id": research_id,
            "message": "Research process started",
            "status": "pending"
        }
        
    except Exception as e:
        logger.error(f"Start research error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get research status
@app.get("/research/{research_id}/status", response_model=ResearchStatus)
async def get_research_status(research_id: str):
    """Get the status of a research process."""
    if research_id not in research_status_store:
        raise HTTPException(status_code=404, detail="Research ID not found")
    
    return research_status_store[research_id]

# Get research results
@app.get("/research/{research_id}/results", response_model=ResearchResponse)
async def get_research_results(research_id: str):
    """Get the results of a completed research process."""
    if research_id not in research_results_store:
        raise HTTPException(status_code=404, detail="Research results not found")
    
    return research_results_store[research_id]

# Get all research processes
@app.get("/research", response_model=List[ResearchStatus])
async def list_research_processes():
    """List all research processes."""
    return list(research_status_store.values())

# Synchronous research endpoint (for simple use cases)
@app.post("/research/sync", response_model=ResearchResponse)
async def sync_research(request: ResearchRequest):
    """Perform synchronous research (waits for completion)."""
    try:
        if not research_agent or not firecrawl_app:
            raise HTTPException(
                status_code=400, 
                detail="API keys not configured. Please call /configure endpoint first."
            )
        
        import uuid
        research_id = str(uuid.uuid4())
        
        # Run research process synchronously
        await run_research_process(
            research_id,
            request.topic,
            request.max_depth,
            request.time_limit,
            request.max_urls,
            request.enhance_report
        )
        
        return research_results_store[research_id]
        
    except Exception as e:
        logger.error(f"Sync research error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Download research report
@app.get("/research/{research_id}/download")
async def download_research_report(research_id: str, format: str = "markdown"):
    """Download research report in specified format."""
    if research_id not in research_results_store:
        raise HTTPException(status_code=404, detail="Research results not found")
    
    result = research_results_store[research_id]
    if not result.success:
        raise HTTPException(status_code=400, detail="Research was not successful")
    
    report_content = result.enhanced_report or result.initial_report
    if not report_content:
        raise HTTPException(status_code=404, detail="No report content available")
    
    if format.lower() == "markdown":
        from fastapi.responses import Response
        return Response(
            content=report_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={result.topic.replace(' ', '_')}_report.md"}
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Only 'markdown' is supported.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
