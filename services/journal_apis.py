import asyncio
from typing import List, Dict
import httpx

class JournalAPI:
    async def validate_claim(self, claim: str) -> Dict:
        """Validate claim across multiple journals"""
        try:
            tasks = [
                self.pubmed_api.search(claim),
                self.sciencedirect_api.search(claim),
                self.lancet_api.search(claim)
            ]
            results = await asyncio.gather(*tasks)
            
            return {
                "sources": results,
                "validation_score": self._calculate_validation_score(results)
            }
            
        except Exception as e:
            print(f"Journal validation error: {str(e)}")
            return {
                "sources": [],
                "validation_score": 50
            }

    def _calculate_validation_score(self, results: List[Dict]) -> float:
        """Calculate validation score based on supporting evidence"""
        supporting = sum(1 for r in results if r.get("supports_claim", False))
        total = len(results)
        
        if total == 0:
            return 50
            
        return (supporting / total) * 100
