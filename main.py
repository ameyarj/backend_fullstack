from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import random
from datetime import datetime
import re
from difflib import SequenceMatcher
from services.perplexity_service import PerplexityService
from services.social_media import TwitterAPI
from services.journal_apis import JournalAPI
from services.batch_processor import BatchProcessor
from services.analytics_service import AnalyticsService

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

influencers = {}
claims = {}

class Claim(BaseModel):
    id: str
    influencer_id: str
    content: str
    category: str
    verification_status: str
    trust_score: float
    source: str
    date: str

class Influencer(BaseModel):
    id: str
    name: str
    follower_count: int
    trust_score: float
    platform: str

class ResearchConfig(BaseModel):
    date_range: str
    claim_limit: int
    journal_sources: List[str]
    min_trust_score: float
    categories: List[str]

ai_service = PerplexityService()
journal_api = JournalAPI()
batch_processor = BatchProcessor(ai_service, journal_api)
analytics_service = AnalyticsService()

research_config = ResearchConfig(
    date_range="30d",
    claim_limit=100,
    journal_sources=["pubmed", "cochrane", "science_direct"],
    min_trust_score=60.0,
    categories=["Nutrition", "Medicine", "Mental Health", "Fitness", "Alternative Medicine"]
)

def init_sample_data():
    sample_influencers = [
        {"name": "HealthGuru", "platform": "Instagram", "bio": "Evidence-based nutrition advice"},
        {"name": "WellnessCoach", "platform": "YouTube", "bio": "Holistic health practitioner"},
        {"name": "NutritionExpert", "platform": "Twitter", "bio": "PhD in Nutritional Science"},
        {"name": "FitnessDoc", "platform": "Instagram", "bio": "Medical doctor & fitness expert"},
        {"name": "MindfulHealer", "platform": "YouTube", "bio": "Mental health advocate"}
    ]
    
    for inf in sample_influencers:
        influencer = Influencer(
            id=str(len(influencers) + 1),
            name=inf["name"],
            follower_count=random.randint(10000, 1000000),
            trust_score=random.uniform(60, 95),
            platform=inf["platform"]
        )
        influencers[influencer.id] = influencer
        
        sample_claims = [
            "Regular consumption of green tea can boost metabolism by up to 4%",
            "Intermittent fasting increases human growth hormone production by 500%",
            "Meditation for 10 minutes daily reduces cortisol levels by 25%",
            "High-intensity interval training burns 50% more calories than steady-state cardio",
            "Omega-3 supplements can improve memory function by 15%"
        ]
        
        for claim_text in sample_claims:
            analysis = ai_service.analyze_text(claim_text)
            claim = Claim(
                id=str(len(claims) + 1),
                influencer_id=influencer.id,
                content=claim_text,
                category=analysis["category"],
                verification_status=analysis["verification_status"],
                trust_score=analysis["trust_score"],
                source="Sample Data",
                date=datetime.now().isoformat()
            )
            claims[claim.id] = claim

@app.on_event("startup")
async def startup_event():
    init_sample_data()

@app.post("/api/influencers")
async def add_influencer(name: str, platform: str):
    influencer_id = str(len(influencers) + 1)
    influencer = Influencer(
        id=influencer_id,
        name=name,
        follower_count=random.randint(1000, 1000000),
        trust_score=random.uniform(0, 100),
        platform=platform
    )
    influencers[influencer_id] = influencer
    return influencer

@app.get("/api/influencers")
async def get_influencers():
    return list(influencers.values())

@app.get("/api/influencers/{influencer_id}")
async def get_influencer(influencer_id: str):
    if influencer_id not in influencers:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return influencers[influencer_id]

@app.post("/api/claims")
async def add_claim(influencer_id: str, content: str):
    if influencer_id not in influencers:
        raise HTTPException(status_code=404, detail="Influencer not found")
    
    analysis = await ai_service.analyze_claim(content)  
    
    claim_id = str(len(claims) + 1)
    claim = Claim(
        id=claim_id,
        influencer_id=influencer_id,
        content=content,
        category=analysis["category"],
        verification_status=analysis["verification_status"],
        trust_score=analysis["trust_score"],
        source="Perplexity Analysis",
        date=datetime.now().isoformat()
    )
    claims[claim_id] = claim
    return claim

@app.get("/api/claims/{influencer_id}")
async def get_claims(influencer_id: str):
    return [claim for claim in claims.values() if claim.influencer_id == influencer_id]

@app.get("/api/analyze")
async def analyze_content(content: str):
    return ai_service.analyze_text(content)

@app.get("/api/stats")
async def get_stats():
    total_claims = len(claims)
    verified_claims = len([c for c in claims.values() if c.verification_status == "Verified"])
    avg_trust_score = sum(c.trust_score for c in claims.values()) / (total_claims if total_claims > 0 else 1)
    
    return {
        "total_influencers": len(influencers),
        "total_claims": total_claims,
        "verified_claims": verified_claims,
        "avg_trust_score": avg_trust_score,
        "categories": {cat: len([c for c in claims.values() if c.category == cat]) 
                      for cat in ai_service.keywords.keys()}
    }

@app.post("/api/influencers/{influencer_id}/scan")
async def scan_influencer_content(influencer_id: str):
    """Scan influencer's social media for new claims"""
    if influencer_id not in influencers:
        raise HTTPException(status_code=404, detail="Influencer not found")
    
    influencer = influencers[influencer_id]
    
    try:
        if influencer.platform.lower() != "twitter":
            raise HTTPException(
                status_code=400, 
                detail="Currently only supporting Twitter platform"
            )

        twitter_api = TwitterAPI()
        tweets = await twitter_api.fetch_recent_posts(influencer.name)
        
        new_claims = []
        for tweet in tweets:
            analysis = await ai_service.analyze_claim(tweet)
            
            if analysis["trust_score"] > 0: 
                claim = Claim(
                    id=str(len(claims) + 1),
                    influencer_id=influencer_id,
                    content=tweet,
                    category=analysis["category"],
                    verification_status=analysis["verification_status"],
                    trust_score=analysis["trust_score"],
                    source="Twitter Scan",
                    date=datetime.now().isoformat()
                )
                claims[claim.id] = claim
                new_claims.append(claim)
        
        return {"message": f"Found {len(new_claims)} new claims", "claims": new_claims}
    except Exception as e:
        print(f"Scan error: {str(e)}")  
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/batch-process")
async def process_claims_batch(claims: List[str]):
    results = await batch_processor.process_claims(claims)
    return {"processed": len(results), "results": results}

@app.get("/api/analytics/report")
async def get_analytics_report():
    return analytics_service.generate_report(
        claims=list(claims.values()),
        influencers=list(influencers.values())
    )

@app.get("/api/dashboard/leaderboard")
async def get_leaderboard():
    """Get influencer leaderboard"""
    return sorted(
        list(influencers.values()),
        key=lambda x: x.trust_score,
        reverse=True
    )

@app.get("/api/dashboard/influencer/{influencer_id}")
async def get_influencer_dashboard(influencer_id: str):
    """Get influencer detail page data"""
    influencer = influencers.get(influencer_id)
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer not found")
        
    return {
        "influencer": influencer,
        "claims": [c for c in claims.values() if c.influencer_id == influencer_id],
        "stats": {
            "total_claims": len([c for c in claims.values() if c.influencer_id == influencer_id]),
            "verified_claims": len([c for c in claims.values() if c.influencer_id == influencer_id and c.verification_status == "Verified"]),
            "avg_trust_score": sum(c.trust_score for c in claims.values() if c.influencer_id == influencer_id) / len([c for c in claims.values() if c.influencer_id == influencer_id]) if len([c for c in claims.values() if c.influencer_id == influencer_id]) > 0 else 0
        }
    }

@app.post("/api/dashboard/config")
async def set_research_config(config: Dict):
    """Set research configuration"""
    return {"message": "Config updated successfully", "config": config}

@app.post("/api/research/config")
async def update_research_config(config: ResearchConfig):
    global research_config
    research_config = config
    return {"message": "Research configuration updated", "config": config}

@app.get("/api/research/config")
async def get_research_config():
    return research_config

@app.post("/api/influencers/{influencer_id}/analyze")
async def analyze_influencer(
    influencer_id: str,
    full_scan: bool = False,
    config: ResearchConfig = None
):
    """Comprehensive influencer analysis"""
    if influencer_id not in influencers:
        raise HTTPException(status_code=404, detail="Influencer not found")
        
    config = config or research_config
    influencer = influencers[influencer_id]
    
    content = []
    if influencer.platform.lower() == "twitter":
        twitter_api = TwitterAPI()
        tweets = await twitter_api.fetch_recent_posts(influencer.name)
        content.extend(tweets)
        
    claims = []
    for text in content:
        extracted_claims = ai_service.extract_health_claim(text)
        for claim in extracted_claims:
            if not ai_service.check_duplicate(claim, [c.content for c in claims]):
                analysis = await ai_service.analyze_claim(claim)
                if analysis["trust_score"] >= config.min_trust_score:
                    claims.append(Claim(
                        id=str(len(claims) + 1),
                        influencer_id=influencer_id,
                        content=claim,
                        category=analysis["category"],
                        verification_status=analysis["verification_status"],
                        trust_score=analysis["trust_score"],
                        source=influencer.platform,
                        date=datetime.now().isoformat()
                    ))
                    
    return {
        "influencer": influencer,
        "analyzed_claims": claims,
        "analysis_summary": {
            "total_claims": len(claims),
            "verified_claims": len([c for c in claims if c.verification_status == "Verified"]),
            "avg_trust_score": sum(c.trust_score for c in claims) / len(claims) if claims else 0,
            "categories": {cat: len([c for c in claims if c.category == cat]) 
                         for cat in config.categories}
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
