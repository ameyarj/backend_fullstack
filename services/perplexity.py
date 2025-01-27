import os
import httpx
from typing import List, Dict

class PerplexityService:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
    async def analyze_claim(self, claim: str) -> Dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Analyze this health claim and provide:
        1. Category (Nutrition/Medicine/Mental Health/Fitness/Alternative Medicine)
        2. Scientific validation (search medical journals)
        3. Trust score (0-100)
        4. Verification status (Verified/Questionable/Debunked)
        
        Claim: {claim}
        
        Format response as JSON."""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json={
                    "model": "pplx-7b-online",
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            
            if response.status_code != 200:
                raise Exception("Perplexity API call failed")
                
            result = response.json()
            return self.parse_response(result["choices"][0]["message"]["content"])
            
    def parse_response(self, content: str) -> Dict:
        
        try:
       
            pass
        except:
            return {
                "category": "Unknown",
                "verification_status": "Questionable",
                "trust_score": 50,
                "analysis": {
                    "scientific_references": [],
                    "validation_notes": "Analysis failed"
                }
            }
