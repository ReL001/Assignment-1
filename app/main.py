from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any
import uvicorn

from app.content_generator import ContentGenerator

app = FastAPI(
    title="Perspective-Driven Content Generation",
    description="Generates perspective-driven LinkedIn content",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

content_generator = ContentGenerator()

class ArticleInfo(BaseModel):
    summary: Optional[str] = Field(None, min_length=10, description="Summary of the article to respond to")
    url: Optional[str] = Field(None, description="URL of the healthcare AI article")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="Controls creativity (0.0-1.0)")

class ContentRequest(BaseModel):
    content: str = Field(..., description="LinkedIn post content to analyze")

class LinkedInPost(BaseModel):
    linkedin_post: str = Field(..., description="Generated LinkedIn post content")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score for perspective alignment")
    error: Optional[str] = Field(None, description="Error message if generation failed")

# API routes
@app.post("/generate", response_model=LinkedInPost)
async def generate_post(article_info: ArticleInfo) -> Dict[str, Any]:
    result = content_generator.generate_linkedin_post(
        article_summary=article_info.summary,
        article_url=article_info.url,
        temperature=article_info.temperature
    )
    
    if "error" in result and result["error"]:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result

@app.post("/analyze", response_model=Dict[str, Any])
async def analyze_post(request: ContentRequest) -> Dict[str, Any]:
    analysis = content_generator.analyze_perspective_alignment(request.content)
    
    if "error" in analysis and analysis["error"]:
        raise HTTPException(status_code=500, detail=analysis["error"])
        
    return analysis

@app.get("/")
async def root():
    return {
        "name": "Perspective-Driven Content Generation",
        "description": "Generates perspective-driven LinkedIn content"
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)