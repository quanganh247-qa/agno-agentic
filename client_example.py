import requests
import json
import time
from typing import Dict, Any

class DeepResearchClient:
    """Client for interacting with the Deep Research FastAPI service."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def configure_api_keys(self, gemini_api_key: str, firecrawl_api_key: str) -> Dict[str, Any]:
        """Configure API keys for the service."""
        response = self.session.post(
            f"{self.base_url}/configure",
            json={
                "gemini_api_key": gemini_api_key,
                "firecrawl_api_key": firecrawl_api_key
            }
        )
        response.raise_for_status()
        return response.json()
    
    def start_research(self, topic: str, max_depth: int = 3, time_limit: int = 180, 
                      max_urls: int = 10, enhance_report: bool = True) -> str:
        """Start a research process and return the research ID."""
        response = self.session.post(
            f"{self.base_url}/research",
            json={
                "topic": topic,
                "max_depth": max_depth,
                "time_limit": time_limit,
                "max_urls": max_urls,
                "enhance_report": enhance_report
            }
        )
        response.raise_for_status()
        return response.json()["research_id"]
    
    def get_research_status(self, research_id: str) -> Dict[str, Any]:
        """Get the status of a research process."""
        response = self.session.get(f"{self.base_url}/research/{research_id}/status")
        response.raise_for_status()
        return response.json()
    
    def get_research_results(self, research_id: str) -> Dict[str, Any]:
        """Get the results of a completed research process."""
        response = self.session.get(f"{self.base_url}/research/{research_id}/results")
        response.raise_for_status()
        return response.json()
    
    def sync_research(self, topic: str, max_depth: int = 3, time_limit: int = 180,
                     max_urls: int = 10, enhance_report: bool = True) -> Dict[str, Any]:
        """Perform synchronous research (waits for completion)."""
        response = self.session.post(
            f"{self.base_url}/research/sync",
            json={
                "topic": topic,
                "max_depth": max_depth,
                "time_limit": time_limit,
                "max_urls": max_urls,
                "enhance_report": enhance_report
            }
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_research_completion(self, research_id: str, timeout: int = 600) -> Dict[str, Any]:
        """Wait for research to complete and return results."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_research_status(research_id)
            print(f"Status: {status['status']} - {status['current_step']}")
            
            if status["status"] == "completed":
                return self.get_research_results(research_id)
            elif status["status"] == "error":
                raise Exception(f"Research failed: {status['current_step']}")
            
            time.sleep(5)  # Poll every 5 seconds
        
        raise TimeoutError(f"Research did not complete within {timeout} seconds")
    
    def download_report(self, research_id: str, filename: str = None) -> str:
        """Download research report as markdown."""
        response = self.session.get(f"{self.base_url}/research/{research_id}/download")
        response.raise_for_status()
        
        content = response.text
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Report saved to {filename}")
        
        return content

def main():
    """Example usage of the Deep Research Client."""
    # Initialize client
    client = DeepResearchClient()
    
    # Configure API keys (replace with your actual keys)
    try:
        # You need to set these environment variables or replace with actual keys
        import os
        gemini_key = os.getenv("GEMINI_API_KEY", "AIzaSyCL5I8JcAq2QBkwU9ZsmI5KO8YdtFF2k7A")
        firecrawl_key = os.getenv("FIRECRAWL_API_KEY", "fc-91db174e4d974ecfa96ce205b3d0d604")
        
        print("Configuring API keys...")
        client.configure_api_keys(gemini_key, firecrawl_key)
        print("✅ API keys configured successfully")
        
        # Example 1: Asynchronous research
        print("\n🔍 Starting asynchronous research...")
        research_topic = "Latest developments in AI and machine learning"
        research_id = client.start_research(
            topic=research_topic,
            max_depth=2,
            time_limit=120,
            max_urls=5,
            enhance_report=True
        )
        print(f"Research started with ID: {research_id}")
        
        # Wait for completion
        print("Waiting for research to complete...")
        results = client.wait_for_research_completion(research_id)
        
        if results["success"]:
            print("✅ Research completed successfully!")
            print(f"Topic: {results['topic']}")
            print(f"Sources count: {results.get('sources_count', 'N/A')}")
            
            # Download report
            filename = f"{research_topic.replace(' ', '_')}_report.md"
            client.download_report(research_id, filename)
            
        else:
            print(f"❌ Research failed: {results.get('error', 'Unknown error')}")
        
        # Example 2: Synchronous research (simpler but blocks)
        print("\n🔍 Starting synchronous research...")
        sync_results = client.sync_research(
            topic="Benefits of renewable energy",
            max_depth=2,
            time_limit=60,
            max_urls=3,
            enhance_report=False
        )
        
        if sync_results["success"]:
            print("✅ Synchronous research completed!")
            print("Report preview:")
            print("=" * 50)
            print(sync_results["initial_report"][:500] + "...")
        else:
            
            print(f"❌ Synchronous research failed: {sync_results.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
