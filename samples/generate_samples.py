import os
import sys
import json
import requests
from pathlib import Path
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
import time
import subprocess
import threading
import signal
import atexit

REAL_ARTICLES = [
    {
        "title": "AI in Diagnostic Imaging",
        "url": "https://www.healthimaging.com/topics/artificial-intelligence/ai-helps-detect-lung-cancer-ct-scans"
    },
    {
        "title": "Healthcare Administrative AI",
        "url": "https://www.healthcareitnews.com/news/how-ai-taking-paperwork-out-healthcare"
    }
]

API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 60  # seconds

server_process = None

def start_api_server():
    """Start the FastAPI server in a subprocess"""
    print("Starting API server...")
    root_dir = Path(__file__).parent.parent

    process = subprocess.Popen(
        ["python", "-m", "app.main"],
        cwd=str(root_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    atexit.register(lambda: process.terminate() if process and process.poll() is None else None)

    print("Waiting for server to start...")
    time.sleep(5)
    
    return process

def wait_for_server(url, max_attempts=5):
    """Wait for the server to be ready"""
    for attempt in range(max_attempts):
        try:
            response = httpx.get(url, timeout=2)
            if response.status_code == 200:
                print(f"Server is ready at {url}")
                return True
        except Exception:
            pass
        
        print(f"Waiting for server (attempt {attempt+1}/{max_attempts})...")
        time.sleep(2)
    
    print("Server did not start successfully")
    return False

def generate_post_via_api(article_url, article_summary=None):

    try:
        payload = {
            "url": article_url
        }
        
        if article_summary:
            payload["summary"] = article_summary
            
        response = httpx.post(
            f"{API_BASE_URL}/generate",
            json=payload,
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"API error: {response.status_code}",
                "linkedin_post": f"Error: {response.text}",
                "confidence_score": 0.0
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "linkedin_post": f"Error calling API: {str(e)}",
            "confidence_score": 0.0
        }

def analyze_post_via_api(content):
    try:
        response = httpx.post(
            f"{API_BASE_URL}/analyze",
            json={"content": content},
            timeout=API_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"API error: {response.status_code}",
                "overall_alignment_score": 0.0,
                "statements_referenced": [],
                "improvement_suggestions": [f"API Error: {response.text}"]
            }
            
    except Exception as e:
        return {
            "error": str(e),
            "overall_alignment_score": 0.0,
            "statements_referenced": [],
            "improvement_suggestions": [f"Error calling API: {str(e)}"]
        }

def main():
    print("Generating sample LinkedIn posts articles...\n")
    
    server_process = start_api_server()

    if not wait_for_server(API_BASE_URL):
        print("Failed to start API server. Exiting.")
        if server_process:
            server_process.terminate()
        return

    samples_dir = Path(__file__).parent
    output_file = samples_dir / "sample_outputs.md"
    
    # Generate posts
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Sample LinkedIn Post Outputs\n\n")
        
        for i, article in enumerate(REAL_ARTICLES, 1):
            print(f"Generating sample {i}: {article['title']}...")
            
            result = generate_post_via_api(article["url"])
            
            content = result.get("linkedin_post", "No content generated")
            confidence_score = result.get("confidence_score", 0.0) or 0.0
            
            f.write(f"## Sample {i}: {article['title']}\n\n")
            f.write(f"**Source:** [{urlparse(article['url']).netloc}]({article['url']})\n\n")

            if "error" in result and result["error"]:
                f.write(f"**Error:** {result['error']}\n\n")
            
            f.write(f"**Generated LinkedIn Post:**\n\n{content}\n\n")
            f.write(f"**Confidence Score:** {confidence_score:.2f}\n\n")

            if confidence_score > 0 and len(content) > 50:
                print(f"Analyzing post alignment...")
                analysis = analyze_post_via_api(json.dumps(content))
                
                if "overall_alignment_score" in analysis:
                    f.write(f"**Analysis:**\n\n")
                    f.write(f"- Alignment Score: {analysis.get('overall_alignment_score', 0.0):.2f}\n")
                    f.write(f"- Statements Referenced: {', '.join(analysis.get('statements_referenced', []))}\n")
                    
                    if analysis.get('improvement_suggestions'):
                        f.write(f"- Improvement Suggestions: {', '.join(analysis.get('improvement_suggestions', []))}\n")
            
            f.write("\n---\n\n")
            
    print(f"\nSample outputs saved to {output_file}")

    if server_process:
        print("Terminating API server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()


if __name__ == "__main__":
    main()