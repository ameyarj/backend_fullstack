from difflib import SequenceMatcher
import os
import httpx
import json
from typing import Dict, List
from dotenv import load_dotenv
import re
from services.social_media import TwitterAPI
import numpy as np

load_dotenv()

class PerplexityService:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in environment variables")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.keywords = {
            "Nutrition": ["vitamin", "protein", "diet", "food", "supplement", "meal", "eating", "nutrient"],
            "Medicine": ["treatment", "cure", "medicine", "drug", "health", "disease", "symptoms", "medical"],
            "Mental Health": ["stress", "anxiety", "depression", "mental", "therapy", "mindfulness", "psychological"],
            "Fitness": ["exercise", "workout", "training", "muscle", "cardio", "strength", "fitness", "gym"],
            "Alternative Medicine": ["natural", "herbal", "holistic", "alternative", "traditional", "healing"]
        }
        self.social_apis = {
            "twitter": TwitterAPI()
        }
        # Initialize sentence transformer only if needed
        self.model = None

    def _init_sentence_transformer(self):
        """Lazy initialization of sentence transformer"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            print("Warning: SentenceTransformer not available. Falling back to basic similarity.")
            self.model = None

    def is_similar(self, claim1: str, claim2: str) -> bool:
        # Basic similarity check using SequenceMatcher
        ratio = SequenceMatcher(None, claim1.lower(), claim2.lower()).ratio()
        if ratio > 0.8:
            return True
            
        # Advanced similarity check using sentence transformer if available
        if self.model is None and ratio <= 0.8:
            try:
                self._init_sentence_transformer()
            except Exception as e:
                print(f"Warning: Could not initialize sentence transformer: {e}")
                return ratio > 0.8

        if self.model:
            try:
                embeddings1 = self.model.encode(claim1, convert_to_tensor=True)
                embeddings2 = self.model.encode(claim2, convert_to_tensor=True)
                cosine_sim = np.dot(embeddings1, embeddings2) / (np.linalg.norm(embeddings1) * np.linalg.norm(embeddings2))
                return cosine_sim > 0.85
            except Exception as e:
                print(f"Warning: Error in advanced similarity check: {e}")
                return ratio > 0.8
                
        return ratio > 0.8

    def analyze_text(self, content: str) -> Dict:
        """Legacy method for basic analysis without API call"""
        content = content.lower()
        
        category_scores = {cat: 0 for cat in self.keywords}
        for category, words in self.keywords.items():
            for word in words:
                if word in content:
                    category_scores[category] += 1
        
        category = max(category_scores.items(), key=lambda x: x[1])[0]
        trust_score = 70  
        
        return {
            "category": category,
            "verification_status": "Verified" if trust_score > 70 else "Questionable",
            "trust_score": trust_score
        }

    async def analyze_claim(self, content: str) -> Dict:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""Analyze this health claim and provide detailed analysis:
            
            Claim: {content}
            
            Please provide:
            1. Category (Nutrition/Medicine/Mental Health/Fitness/Alternative Medicine)
            2. Scientific validation based on medical literature
            3. Trust score (0-100)
            4. Verification status (Verified/Questionable/Debunked)
            5. Scientific evidence (list of relevant studies if any)
            
            Format the response as JSON with these exact keys: category, verification_status, trust_score, scientific_evidence"""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json={
                        "model": "pplx-7b-online",
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return self.analyze_text(content)  
                    
                result = response.json()
                return self.parse_response(result)
        except Exception as e:
            print(f"API Error: {str(e)}")
            return self.analyze_text(content)  

    def parse_response(self, api_response: Dict) -> Dict:
        try:
            content = api_response["choices"][0]["message"]["content"]
         
            return {
                "category": "Nutrition",  
                "verification_status": "Verified",
                "trust_score": 75.0,
                "scientific_evidence": []
            }
        except Exception as e:
            print(f"Error parsing API response: {str(e)}")
            return {
                "category": "Unknown",
                "verification_status": "Questionable",
                "trust_score": 50.0,
                "scientific_evidence": []
            }

    def check_duplicate(self, new_claim: str, existing_claims: List[str]) -> bool:
        for claim in existing_claims:
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, new_claim.lower(), claim.lower()).ratio()
            if similarity > 0.8:
                return True
        return False

    def basic_analysis(self, content: str) -> Dict:
        content = content.lower()
        
        category_scores = {cat: 0 for cat in self.keywords}
        for category, words in self.keywords.items():
            for word in words:
                if word in content:
                    category_scores[category] += 1
        
        category = max(category_scores.items(), key=lambda x: x[1])[0]
        
        trust_score = 50  
        
        return {
            "category": category,
            "verification_status": "Questionable",
            "trust_score": trust_score,
            "scientific_evidence": []
        }
    
    async def fetch_social_content(self, platform: str, handle: str) -> List[str]:
        """Fetch recent content from social media platforms"""
        if platform.lower() not in self.social_apis:
            raise ValueError(f"Unsupported platform: {platform}")
        
        content = await self.social_apis[platform.lower()].fetch_recent_posts(handle)
        return self.extract_claims(content)
    
    def extract_claims(self, content: List[str]) -> List[str]:
        """Extract health claims from content using NLP"""
        claims = []
        for text in content:
            claim_patterns = [
                r"(studies show|research indicates|according to|proven to|can|may|will) .+",
                r".+ (increases|decreases|improves|reduces|boosts|helps) .+",
                r".+ is (good|bad|beneficial|harmful) for .+"
            ]
            
            for pattern in claim_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                claims.extend(match.group(0) for match in matches)
        
        return self.remove_duplicate_claims(claims)
    
    def remove_duplicate_claims(self, claims: List[str]) -> List[str]:
        unique_claims = []
        for claim in claims:
            if not any(self.is_similar(claim, existing) for existing in unique_claims):
                unique_claims.append(claim)
        return unique_claims

    def calculate_trust_score(self, analysis: Dict) -> float:
        score = 50  
        
        for evidence in analysis.get("scientific_evidence", []):
            if evidence.get("supports_claim"):
                score += 10
                
        return min(max(score, 0), 100)
