import asyncio
import tweepy
import os
from typing import List, Dict
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
            
            clean_username = username.replace('@', '').strip()
            
            try:
                # Add rate limit handling with retry
                for attempt in range(3):  # Try 3 times
                    try:
                        user_response = self.client.get_user(username=clean_username)
                        if not user_response or not user_response.data:
                            print(f"User {username} not found")
                            return []
                            
                        user_id = user_response.data.id
                        await asyncio.sleep(1)  # Wait between requests
                        
                        tweets_response = self.client.get_users_tweets(
                            user_id, 
                            max_results=min(limit, 10),  # Limit to 10 tweets max
                            exclude=['retweets', 'replies']
                        )
                        
                        if not tweets_response or not tweets_response.data:
                            return []
                            
                        return [tweet.text for tweet in tweets_response.data]
                    
                    except tweepy.TooManyRequests:
                        if attempt < 2:  # Don't sleep on last attempt
                            await asyncio.sleep(15)  # Wait 15 seconds before retry
                        continue
                    except Exception as e:
                        print(f"Twitter API error: {str(e)}")
                        return []
                        
                return []  # Return empty list if all attempts fail
                
            except Exception as e:
                print(f"Error in Twitter API call: {str(e)}")
                return []
                
        except Exception as e:
            print(f"Error fetching tweets: {str(e)}")
            return []

class YouTubeAPI:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    async def fetch_recent_posts(self, channel_name: str, limit: int = 10) -> List[str]:
        try:
            # First get channel ID
            request = self.youtube.search().list(
                part="snippet",
                q=channel_name,
                type="channel",
                maxResults=1
            )
            response = request.execute()
            
            if not response['items']:
                return []
                
            channel_id = response['items'][0]['id']['channelId']
            
            # Get recent videos
            request = self.youtube.search().list(
                part="snippet",
                channelId=channel_id,
                order="date",
                type="video",
                maxResults=limit
            )
            response = request.execute()
            
            # Get video descriptions
            return [item['snippet']['description'] for item in response.get('items', [])]
            
        except HttpError as e:
            print(f"YouTube API error: {str(e)}")
            return []
        except Exception as e:
            print(f"Error fetching YouTube content: {str(e)}")
            return []

