import tweepy
import os
from typing import List, Dict
from datetime import datetime, timedelta

class TwitterAPI:
    def __init__(self):
        try:
            self.client = tweepy.Client(
                bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
                consumer_key=os.getenv("TWITTER_API_KEY"),
                consumer_secret=os.getenv("TWITTER_API_SECRET"),
                access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
                access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
            )
        except Exception as e:
            print(f"Twitter API init error: {str(e)}")
            self.client = None

    async def fetch_recent_posts(self, username: str, limit: int = 10) -> List[str]:
        try:
            if not self.client:
                return []
                
            user_response = self.client.get_user(username=username)
            if not user_response or not user_response.data:
                print(f"User {username} not found")
                return []
                
            user_id = user_response.data.id
            
            tweets_response = self.client.get_users_tweets(
                user_id, 
                max_results=limit,
                exclude=['retweets', 'replies']
            )
            
            if not tweets_response or not tweets_response.data:
                return []
                
            return [tweet.text for tweet in tweets_response.data]
            
        except Exception as e:
            print(f"Error fetching tweets: {str(e)}")
            return []

