import json
import os
from typing import Dict, Any, Optional
import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, GenerationConfig

from app.config import (
    GOOGLE_PROJECT_ID,
    GOOGLE_LOCATION,
    VERTEX_MODEL,
    PERSPECTIVE_STATEMENTS,
    MIN_WORD_COUNT,
    MAX_WORD_COUNT,
    DEFAULT_TEMPERATURE
)

class ContentGenerator:

    def __init__(self):
        aiplatform.init(project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION)
        self.model = GenerativeModel(VERTEX_MODEL)
        self.perspective_statements = PERSPECTIVE_STATEMENTS

    def fetch_article_content(self, url: str) -> Dict[str, Any]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = httpx.get(url, headers=headers, timeout=10.0, follow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            title = soup.title.string if soup.title else "Healthcare AI Article"

            article_tag = soup.find('article')
            if article_tag:
                paragraphs = article_tag.find_all('p')
            else:
                main_content = soup.find('main') or soup.find(id='content') or soup
                paragraphs = main_content.find_all('p')

            article_text = " ".join([p.get_text().strip() for p in paragraphs])

            summary = article_text[:1000] + ("..." if len(article_text) > 1000 else "")

            if len(summary) < 100:
                summary = f"This is an article from {urlparse(url).netloc}. Please visit the URL to read the full content."
            
            return {
                "title": title.strip(),
                "summary": summary.strip(),
                "url": url
            }
            
        except Exception as e:
            domain = urlparse(url).netloc if url else "unknown"
            return {
                "title": f"Article from {domain}",
                "summary": f"Error fetching content: {str(e)}",
                "url": url
            }

    def _construct_prompt(self, article_summary: str, article_url: Optional[str] = None) -> str:
        perspective_points = "\n".join([f"- {point}" for point in self.perspective_statements])
        
        # Prompt
        prompt = f"""
        You are an AI assistant crafting LinkedIn content for a physician healthcare AI executive. 
        
        Please generate a LinkedIn post (200-250 words) that reflects on the following article 
        information while maintaining the client's authentic perspective and voice.
        
        ARTICLE INFORMATION:
        {article_summary}
        
        CLIENT'S CORE PERSPECTIVE ON HEALTHCARE AI:
        {perspective_points}
        
        INSTRUCTIONS:
        1. Write in first person as if you are the healthcare AI executive
        2. Incorporate at least 2-3 of the client's perspective statements naturally
        3. Maintain a thoughtful, authoritative yet approachable tone
        4. Include a brief, engaging hook at the beginning
        5. End with a thought-provoking question or call to action
        6. Stay between {MIN_WORD_COUNT}-{MAX_WORD_COUNT} words
        7. Do not directly state "As a physician" or "As a healthcare executive" - embody the role naturally
        8. Reference the article content but focus on providing unique insights, not just summarizing
        
        """
        
        if article_url:
            prompt += f"\n\nArticle URL for reference (do not include the full URL in the post): {article_url}"
            
        return prompt

    def generate_linkedin_post(self, article_summary: Optional[str] = None, article_url: Optional[str] = None, 
                              temperature: float = DEFAULT_TEMPERATURE) -> Dict[str, Any]:
        if article_url and not article_summary:
            article_data = self.fetch_article_content(article_url)
            article_summary = article_data["summary"]

        if not article_summary:
            return {
                "error": "Either 'article_summary' or 'article_url' parameter must be provided",
                "linkedin_post": None,
                "confidence_score": 0.0
            }
            
        prompt = self._construct_prompt(article_summary, article_url)
        
        try:
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=1024,
                top_p=0.95,
            )
            
            response = self.model.generate_content(
                contents=prompt,
                generation_config=generation_config
            )

            content = ""
            if hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content') and response.candidates[0].content:
                    if hasattr(response.candidates[0].content, 'parts'):
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'text'):
                                content += part.text

            if not content and hasattr(response, 'text'):
                content = response.text
                
            if not content:
                content = str(response)

            confidence_match = re.search(r'\[CONFIDENCE:\s*(\d+\.\d+)\]', content)
            confidence_score = float(confidence_match.group(1)) if confidence_match else 0.85  # Default confidence if not provided
            
            if confidence_match:
                content = content.replace(confidence_match.group(0), '').strip()

            result = {
                "linkedin_post": content,
                "confidence_score": confidence_score,
                "word_count": len(content.split())
            }
            
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "linkedin_post": None,
                "confidence_score": 0.0
            }
    
    def analyze_perspective_alignment(self, content: str) -> Dict[str, Any]:
        analysis_prompt = f"""
        Analyze how well the following LinkedIn post aligns with these healthcare AI perspective statements:
        
        PERSPECTIVE STATEMENTS:
        {self.perspective_statements}
        
        LINKEDIN POST:
        {content}
        
        Provide a JSON response with:
        1. overall_alignment_score: float between 0-1
        2. statements_referenced: list of perspective statements directly or indirectly referenced
        3. improvement_suggestions: list of brief suggestions if alignment could be improved
        """
        
        try:
            generation_config = GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
            )
            
            response = self.model.generate_content(
                contents=analysis_prompt,
                generation_config=generation_config
            )
            
            response_text = ""
            if hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content') and response.candidates[0].content:
                    if hasattr(response.candidates[0].content, 'parts'):
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'text'):
                                response_text += part.text
            
            if not response_text and hasattr(response, 'text'):
                response_text = response.text
                
            if not response_text:
                response_text = str(response)

            try:
                analysis_result = json.loads(response_text)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis_result = json.loads(json_match.group(0))
                else:
                    raise ValueError("Could not extract valid JSON from response")
                
            return analysis_result
            
        except Exception as e:
            return {
                "error": str(e),
                "overall_alignment_score": 0.0,
                "statements_referenced": [],
                "improvement_suggestions": ["Analysis failed due to an error."]
            }