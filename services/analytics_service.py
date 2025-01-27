from typing import List, Dict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class AnalyticsService:
    def __init__(self):
        self.time_periods = ["24h", "7d", "30d", "all"]

    def generate_report(self, claims: List[Dict], influencers: List[Dict]) -> Dict:
        df_claims = pd.DataFrame(claims)
        df_influencers = pd.DataFrame(influencers)
        
        return {
            "overall_stats": self._calculate_overall_stats(df_claims),
            "trends": self._analyze_trends(df_claims),
            "influencer_impact": self._analyze_influencer_impact(df_claims, df_influencers),
            "category_analysis": self._analyze_categories(df_claims),
            "trust_metrics": self._analyze_trust_metrics(df_claims, df_influencers)
        }

    def _calculate_overall_stats(self, df: pd.DataFrame) -> Dict:
        return {
            "total_claims": len(df),
            "avg_trust_score": df["trust_score"].mean(),
            "verified_percentage": (df["verification_status"] == "Verified").mean() * 100,
            "claims_per_day": self._calculate_daily_volume(df)
        }

    def _analyze_trends(self, df: pd.DataFrame) -> Dict:
        df["date"] = pd.to_datetime(df["date"])
        daily_counts = df.resample("D", on="date").size()
        
        return {
            "daily_volume": daily_counts.to_dict(),
            "moving_average": daily_counts.rolling(7).mean().to_dict(),
            "trend": self._calculate_trend(daily_counts)
        }

