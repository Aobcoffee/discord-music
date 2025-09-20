"""
Configuration management for Discord Music Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Discord Bot Configuration
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DISCORD_COMMAND_PREFIX = os.getenv('DISCORD_COMMAND_PREFIX', '/')
    
    # Spotify API Configuration
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')
    
    # Music Configuration
    MAX_PLAYLIST_SIZE = int(os.getenv('MAX_PLAYLIST_SIZE', '50'))
    MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', '100'))
    YOUTUBE_SEARCH_LIMIT = int(os.getenv('YOUTUBE_SEARCH_LIMIT', '1'))
    
    # FFmpeg Configuration
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    
    # YouTube-DL Configuration
    YTDL_FORMAT_OPTIONS = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN is required")
        
        spotify_configured = bool(cls.SPOTIFY_CLIENT_ID and cls.SPOTIFY_CLIENT_SECRET)
        return {
            'discord_ready': bool(cls.DISCORD_BOT_TOKEN),
            'spotify_ready': spotify_configured
        }

# Spotify OAuth Scopes for accessing private playlists
SPOTIFY_SCOPES = [
    'playlist-read-private',
    'playlist-read-collaborative', 
    'user-library-read',
    'user-read-private',
    'user-read-email'
]