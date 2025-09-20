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
        """Get YouTube video information from search query or URL with fallback mechanisms"""
        # Try multiple strategies to avoid bot detection
        strategies = [
            # Strategy 1: Standard extraction
            lambda q: self.ytdl.extract_info(q, download=False),
            # Strategy 2: Extract with different search method
            lambda q: self._extract_with_fallback(q),
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                logger.info(f"Trying YouTube extraction strategy {i} for: {query}")
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, strategy, query)
                
                if 'entries' in data:
                    # Take first search result
                    result = data['entries'][0] if data['entries'] else None
                    if result:
                        logger.info(f"Strategy {i} succeeded for: {query}")
                        return result
                elif data:
                    logger.info(f"Strategy {i} succeeded for: {query}")
                    return data
                    
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"Strategy {i} failed for '{query}': {e}")
                
                # If this is a bot detection error, try next strategy
                if "sign in to confirm" in error_msg or "not a bot" in error_msg:
                    continue
                elif i == len(strategies):  # Last strategy
                    logger.error(f"All strategies failed for '{query}': {e}")
                    return None
                
        return None
    
    def _extract_with_fallback(self, query: str):
        """Fallback extraction method with modified options"""
        # Create a new ytdl instance with different options for fallback
        fallback_options = Config.YTDL_FORMAT_OPTIONS.copy()
        fallback_options.update({
            'extract_flat': False,
            'youtube_include_dash_manifest': False,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls', 'translated_subs'],
                    'player_skip': ['configs', 'webpage', 'js']
                }
            }
        })
        
        fallback_ytdl = yt_dlp.YoutubeDL(fallback_options)
        return fallback_ytdl.extract_info(query, download=False)
    
    async def create_audio_source(self, url: str) -> Optional['YTDLSource']:
        """Create Discord audio source from URL with enhanced error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Creating audio source from {url} (attempt {attempt + 1})")
                return await YTDLSource.from_url(url, loop=asyncio.get_event_loop(), stream=True)
            except Exception as e:
                error_msg = str(e).lower()
                if "sign in to confirm" in error_msg or "not a bot" in error_msg:
                    logger.warning(f"Bot detection on attempt {attempt + 1}, retrying with delay...")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                logger.error(f"Error creating audio source from {url} (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
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
        """Create YTDLSource from URL with enhanced bot detection handling"""
        loop = loop or asyncio.get_event_loop()
        
        # Try multiple extraction approaches
        extraction_methods = [
            # Method 1: Standard options
            lambda: yt_dlp.YoutubeDL(Config.YTDL_FORMAT_OPTIONS),
            # Method 2: Minimal options for bot detection avoidance
            lambda: yt_dlp.YoutubeDL({
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extractaudio': True,
                'audioformat': 'mp3',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            })
        ]
        
        for i, method in enumerate(extraction_methods, 1):
            try:
                logger.info(f"Trying extraction method {i} for URL: {url}")
                ytdl = method()
                data = await loop.run_in_executor(
                    None, 
                    lambda: ytdl.extract_info(url, download=not stream)
                )
                
                if 'entries' in data:
                    data = data['entries'][0]
                
                filename = data['url'] if stream else ytdl.prepare_filename(data)
                
                logger.info(f"Extraction method {i} succeeded for: {url}")
                return cls(
                    discord.FFmpegPCMAudio(filename, **Config.FFMPEG_OPTIONS), 
                    data=data
                )
                
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"Extraction method {i} failed for {url}: {e}")
                
                if "sign in to confirm" in error_msg or "not a bot" in error_msg:
                    if i < len(extraction_methods):
                        logger.info(f"Bot detection detected, trying method {i + 1}")
                        continue
                
                if i == len(extraction_methods):
                    logger.error(f"All extraction methods failed for {url}: {e}")
                    raise