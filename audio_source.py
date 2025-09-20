"""
Audio source management for Discord Music Bot
"""
import discord
import yt_dlp
import asyncio
from typing import Optional, Dict, Any
from config import Config
import logging

logger = logging.getLogger(__name__)

class AudioSource:
    """Manages audio sources and YouTube-DL operations"""
    
    def __init__(self):
        self.ytdl = yt_dlp.YoutubeDL(Config.YTDL_FORMAT_OPTIONS)
    
    async def get_youtube_info(self, query: str) -> Optional[Dict[str, Any]]:
        """Get YouTube video information from search query or URL"""
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, 
                lambda: self.ytdl.extract_info(query, download=False)
            )
            
            if 'entries' in data:
                # Take first search result
                return data['entries'][0] if data['entries'] else None
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting YouTube info for '{query}': {e}")
            return None
    
    async def create_audio_source(self, url: str) -> Optional['YTDLSource']:
        """Create Discord audio source from URL"""
        try:
            return await YTDLSource.from_url(url, loop=asyncio.get_event_loop(), stream=True)
        except Exception as e:
            logger.error(f"Error creating audio source from {url}: {e}")
            return None

class YTDLSource(discord.PCMVolumeTransformer):
    """Discord audio source using YouTube-DL"""
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration', 0)
        self.uploader = data.get('uploader', 'Unknown')
    
    @classmethod
    async def from_url(cls, url: str, *, loop=None, stream=False):
        """Create YTDLSource from URL"""
        loop = loop or asyncio.get_event_loop()
        
        try:
            ytdl = yt_dlp.YoutubeDL(Config.YTDL_FORMAT_OPTIONS)
            data = await loop.run_in_executor(
                None, 
                lambda: ytdl.extract_info(url, download=not stream)
            )
            
            if 'entries' in data:
                data = data['entries'][0]
            
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            
            return cls(
                discord.FFmpegPCMAudio(filename, **Config.FFMPEG_OPTIONS), 
                data=data
            )
            
        except Exception as e:
            logger.error(f"Error creating YTDLSource from {url}: {e}")
            raise