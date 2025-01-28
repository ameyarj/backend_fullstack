import asyncio
from typing import List, Dict
import httpx

class JournalSource:
    def __init__(self, name: str, base_url: str, api_key: str = None):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key

class JournalAPI:
    def __init__(self):
        self.sources = {
            "pubmed": JournalSource("PubMed", "https://api.pubmed.gov"),
            "cochrane": JournalSource("Cochrane", "https://api.cochrane.org"),
            "science_direct": JournalSource("ScienceDirect", "https://api.sciencedirect.com")
        }
        
    async def validate_claim(self, claim: str, sources: List[str] = None) -> Dict:
        """Enhanced validation across multiple journal sources"""
        if not sources:
            sources = list(self.sources.keys())

        validation_tasks = []
        for source_name in sources:
            if source_name in self.sources:
                validation_tasks.append(self.search_source(source_name, claim))

        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        evidence = []
        total_score = 0
        valid_results = 0
        
        for result in results:
            if isinstance(result, Dict) and not result.get("error"):
                evidence.extend(result["studies"])
                total_score += result["confidence_score"]
                valid_results += 1
        
        return {
            "sources": [r for r in results if isinstance(r, Dict)],
            "validation_score": total_score / valid_results if valid_results > 0 else 50,
            "supporting_evidence": evidence,
            "consensus_strength": self._calculate_consensus_strength(evidence)
        }

    def _calculate_consensus_strength(self, evidence: List[Dict]) -> str:
        if not evidence:
            return "Insufficient Evidence"
            
        supporting = sum(1 for e in evidence if e.get("supports_claim", False))
        total = len(evidence)
        
        ratio = supporting / total if total > 0 else 0
        
        if ratio >= 0.8:
            return "Strong Consensus"
        elif ratio >= 0.6:
            return "Moderate Consensus"
        elif ratio >= 0.4:
            return "Mixed Evidence"
        else:
            return "Limited Support"
