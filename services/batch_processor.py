from typing import List, Dict
import asyncio
from datetime import datetime

class BatchProcessor:
    def __init__(self, perplexity_service, journal_api):
        self.perplexity = perplexity_service
        self.journal_api = journal_api
        self.batch_size = 10
        self.delay_between_batches = 1 

    async def process_claims(self, claims: List[str]) -> List[Dict]:
        results = []
        for i in range(0, len(claims), self.batch_size):
            batch = claims[i:i + self.batch_size]
            batch_results = await asyncio.gather(*[
                self._process_single_claim(claim) for claim in batch
            ])
            results.extend(batch_results)
            await asyncio.sleep(self.delay_between_batches)
        return results

    async def _process_single_claim(self, claim: str) -> Dict:
        perplexity_analysis = await self.perplexity.analyze_claim(claim)
        journal_validation = await self.journal_api.validate_claim(claim)
        
        return {
            **perplexity_analysis,
            "journal_validation": journal_validation,
            "processed_at": datetime.now().isoformat()
        }
