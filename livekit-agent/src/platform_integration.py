"""
Platform Integration - Connects Twitch/YouTube chat to LiveKit
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import os
import twitchio
from twitchio.ext import commands
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Unified chat message structure"""
    platform: str
    user: str
    text: str
    is_mod: bool = False
    is_sub: bool = False
    is_donation: bool = False
    donation_amount: float = 0.0
    timestamp: float = 0.0


class PlatformChatIntegration:
    """
    Integrates platform chats (Twitch/YouTube) with LiveKit
    """
    
    def __init__(self):
        self.twitch_bot: Optional[TwitchBot] = None
        self.youtube_monitor: Optional[YouTubeMonitor] = None
        self.message_queue = asyncio.Queue()
        self.enabled_platforms = []
        
        # Check which platforms are configured
        if os.getenv("TWITCH_CLIENT_ID") and os.getenv("TWITCH_ACCESS_TOKEN"):
            self.enabled_platforms.append("twitch")
            
        if os.getenv("YOUTUBE_API_KEY"):
            self.enabled_platforms.append("youtube")
    
    async def connect(self) -> None:
        """Connect to configured platforms"""
        
        tasks = []
        
        if "twitch" in self.enabled_platforms:
            self.twitch_bot = TwitchBot(self.message_queue)
            tasks.append(self.twitch_bot.start())
            
        if "youtube" in self.enabled_platforms:
            self.youtube_monitor = YouTubeMonitor(self.message_queue)
            tasks.append(self.youtube_monitor.start())
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def disconnect(self) -> None:
        """Disconnect from all platforms"""
        
        if self.twitch_bot:
            await self.twitch_bot.stop()
            
        if self.youtube_monitor:
            await self.youtube_monitor.stop()
    
    async def get_messages(self, timeout: float = 0.1) -> List[ChatMessage]:
        """Get pending chat messages"""
        
        messages = []
        
        try:
            while True:
                msg = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=timeout
                )
                messages.append(msg)
                
                # Limit batch size
                if len(messages) >= 10:
                    break
                    
        except asyncio.TimeoutError:
            pass
        
        return messages
    
    async def send_message(self, text: str, platform: Optional[str] = None) -> None:
        """Send message to platform chat"""
        
        if platform == "twitch" and self.twitch_bot:
            await self.twitch_bot.send_message(text)
            
        elif platform == "youtube" and self.youtube_monitor:
            await self.youtube_monitor.send_message(text)
            
        else:
            # Send to all platforms
            if self.twitch_bot:
                await self.twitch_bot.send_message(text)
            if self.youtube_monitor:
                await self.youtube_monitor.send_message(text)


class TwitchBot(commands.Bot):
    """
    Twitch chat bot integration
    """
    
    def __init__(self, message_queue: asyncio.Queue):
        self.message_queue = message_queue
        self.channel = os.getenv("TWITCH_CHANNEL", "")
        
        super().__init__(
            token=os.getenv("TWITCH_ACCESS_TOKEN"),
            client_id=os.getenv("TWITCH_CLIENT_ID"),
            nick=os.getenv("TWITCH_BOT_NAME", "VTuberBot"),
            prefix="!",
            initial_channels=[self.channel] if self.channel else []
        )
    
    async def event_ready(self):
        """Called when bot is ready"""
        logger.info(f"Twitch bot connected as {self.nick}")
    
    async def event_message(self, message: twitchio.Message):
        """Handle incoming messages"""
        
        # Ignore bot's own messages
        if message.echo:
            return
        
        # Create unified message
        chat_msg = ChatMessage(
            platform="twitch",
            user=message.author.name,
            text=message.content,
            is_mod=message.author.is_mod if message.author else False,
            is_sub=message.author.is_subscriber if message.author else False,
            timestamp=message.timestamp.timestamp() if message.timestamp else 0
        )
        
        # Add to queue
        await self.message_queue.put(chat_msg)
        
        # Process commands
        await self.handle_commands(message)
    
    async def event_cheer(self, message: twitchio.Message, bits: int):
        """Handle bit donations"""
        
        chat_msg = ChatMessage(
            platform="twitch",
            user=message.author.name,
            text=f"Cheered {bits} bits! {message.content}",
            is_donation=True,
            donation_amount=bits / 100,  # Convert to dollars
            timestamp=message.timestamp.timestamp() if message.timestamp else 0
        )
        
        await self.message_queue.put(chat_msg)
    
    async def event_subscription(self, subscription):
        """Handle subscriptions"""
        
        chat_msg = ChatMessage(
            platform="twitch",
            user=subscription.user.name,
            text=f"Just subscribed! {subscription.message or ''}",
            is_sub=True,
            timestamp=0  # No timestamp in sub events
        )
        
        await self.message_queue.put(chat_msg)
    
    async def send_message(self, text: str) -> None:
        """Send message to Twitch chat"""
        
        if self.channel:
            channel = self.get_channel(self.channel)
            if channel:
                await channel.send(text)
    
    async def start(self) -> None:
        """Start the bot"""
        await super().start()
    
    async def stop(self) -> None:
        """Stop the bot"""
        await self.close()


class YouTubeMonitor:
    """
    YouTube Live chat monitor
    """
    
    def __init__(self, message_queue: asyncio.Queue):
        self.message_queue = message_queue
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.channel_id = os.getenv("YOUTUBE_CHANNEL_ID")
        self.live_chat_id: Optional[str] = None
        self.youtube = None
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start monitoring YouTube chat"""
        
        if not self.api_key:
            logger.warning("YouTube API key not configured")
            return
        
        # Build YouTube API client
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        
        # Get live chat ID
        await self.get_live_chat_id()
        
        if self.live_chat_id:
            self.monitoring = True
            self.monitor_task = asyncio.create_task(self.monitor_chat())
            logger.info(f"Started monitoring YouTube live chat: {self.live_chat_id}")
    
    async def stop(self) -> None:
        """Stop monitoring"""
        
        self.monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
    
    async def get_live_chat_id(self) -> None:
        """Get the live chat ID for the current stream"""
        
        try:
            # Get live broadcasts
            request = self.youtube.liveBroadcasts().list(
                part="snippet",
                broadcastStatus="active",
                maxResults=1
            )
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, request.execute
            )
            
            if response.get('items'):
                broadcast = response['items'][0]
                self.live_chat_id = broadcast['snippet']['liveChatId']
                logger.info(f"Found live chat: {self.live_chat_id}")
            else:
                logger.warning("No active YouTube live stream found")
                
        except Exception as e:
            logger.error(f"Failed to get YouTube live chat ID: {e}")
    
    async def monitor_chat(self) -> None:
        """Monitor YouTube live chat"""
        
        next_page_token = None
        
        while self.monitoring:
            try:
                # Get chat messages
                request = self.youtube.liveChatMessages().list(
                    liveChatId=self.live_chat_id,
                    part="snippet,authorDetails",
                    maxResults=200,
                    pageToken=next_page_token
                )
                
                response = await asyncio.get_event_loop().run_in_executor(
                    None, request.execute
                )
                
                # Process messages
                for item in response.get('items', []):
                    await self.process_youtube_message(item)
                
                # Get next page token
                next_page_token = response.get('nextPageToken')
                
                # Wait before next poll (YouTube rate limits)
                poll_interval = response.get('pollingIntervalMillis', 5000) / 1000
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring YouTube chat: {e}")
                await asyncio.sleep(5)
    
    async def process_youtube_message(self, item: Dict) -> None:
        """Process a YouTube chat message"""
        
        snippet = item['snippet']
        author = item['authorDetails']
        
        # Check message type
        message_type = snippet.get('type', 'textMessageEvent')
        
        if message_type == 'textMessageEvent':
            # Regular chat message
            chat_msg = ChatMessage(
                platform="youtube",
                user=author['displayName'],
                text=snippet['displayMessage'],
                is_mod=author.get('isChatModerator', False),
                is_sub=author.get('isChatSponsor', False),
                timestamp=snippet['publishedAt']
            )
            
        elif message_type == 'superChatEvent':
            # Super Chat donation
            details = snippet.get('superChatDetails', {})
            amount = details.get('amountMicros', 0) / 1000000  # Convert to dollars
            
            chat_msg = ChatMessage(
                platform="youtube",
                user=author['displayName'],
                text=f"Super Chat ${amount:.2f}: {details.get('userComment', '')}",
                is_donation=True,
                donation_amount=amount,
                timestamp=snippet['publishedAt']
            )
            
        else:
            # Other event types
            return
        
        # Add to queue
        await self.message_queue.put(chat_msg)
    
    async def send_message(self, text: str) -> None:
        """Send message to YouTube chat"""
        
        if not self.live_chat_id:
            return
        
        try:
            request = self.youtube.liveChatMessages().insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": self.live_chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {
                            "messageText": text
                        }
                    }
                }
            )
            
            await asyncio.get_event_loop().run_in_executor(
                None, request.execute
            )
            
        except Exception as e:
            logger.error(f"Failed to send YouTube message: {e}")