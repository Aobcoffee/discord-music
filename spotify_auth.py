"""
Enhanced Spotify handler with OAuth authentication for private playlists
"""
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import re
import asyncio
import json
import os
from typing import Optional, List, Dict, Tuple, Union
from config import Config, SPOTIFY_SCOPES
import logging

logger = logging.getLogger(__name__)

class SpotifyAuthManager:
    """Manages Spotify authentication for users"""
    
    def __init__(self):
        self.user_tokens = {}  # Store user tokens in memory (use database in production)
        self.auth_cache_dir = "spotify_auth_cache"
        os.makedirs(self.auth_cache_dir, exist_ok=True)
    
    def get_auth_url(self, user_id: str) -> Optional[str]:
        """Generate Spotify authentication URL for user"""
        if not Config.SPOTIFY_CLIENT_ID or not Config.SPOTIFY_CLIENT_SECRET:
            return None
        
        try:
            cache_path = os.path.join(self.auth_cache_dir, f"spotify_cache_{user_id}")
            
            sp_oauth = SpotifyOAuth(
                client_id=Config.SPOTIFY_CLIENT_ID,
                client_secret=Config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=Config.SPOTIFY_REDIRECT_URI,
                scope=' '.join(SPOTIFY_SCOPES),
                cache_path=cache_path,
                show_dialog=True
            )
            
            auth_url = sp_oauth.get_authorize_url()
            return auth_url
            
        except Exception as e:
            logger.error(f"Error generating auth URL for user {user_id}: {e}")
            return None
    
    def get_spotify_client(self, user_id: str) -> Optional[spotipy.Spotify]:
        """Get authenticated Spotify client for user"""
        try:
            cache_path = os.path.join(self.auth_cache_dir, f"spotify_cache_{user_id}")
            
            if not os.path.exists(cache_path):
                return None
            
            sp_oauth = SpotifyOAuth(
                client_id=Config.SPOTIFY_CLIENT_ID,
                client_secret=Config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=Config.SPOTIFY_REDIRECT_URI,
                scope=' '.join(SPOTIFY_SCOPES),
                cache_path=cache_path
            )
            
            token_info = sp_oauth.get_cached_token()
            if not token_info:
                return None
            
            return spotipy.Spotify(auth=token_info['access_token'])
            
        except Exception as e:
            logger.error(f"Error getting Spotify client for user {user_id}: {e}")
            return None
    
    def is_user_authenticated(self, user_id: str) -> bool:
        """Check if user has valid Spotify authentication"""
        return self.get_spotify_client(user_id) is not None

class SpotifyHandler:
    """Enhanced Spotify handler with OAuth support"""
    
    def __init__(self):
        self.enabled = self._initialize_spotify()
        self.auth_manager = SpotifyAuthManager()
        self.public_client = self._create_public_client()
    
    def _initialize_spotify(self) -> bool:
        """Initialize Spotify integration"""
        if not Config.SPOTIFY_CLIENT_ID or not Config.SPOTIFY_CLIENT_SECRET:
            logger.warning("Spotify credentials not found. Spotify features will be disabled.")
            return False
        
        logger.info("Spotify integration enabled!")
        return True
    
    def _create_public_client(self) -> Optional[spotipy.Spotify]:
        """Create public Spotify client for non-authenticated requests"""
        if not self.enabled:
            return None
        
        try:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=Config.SPOTIFY_CLIENT_ID,
                client_secret=Config.SPOTIFY_CLIENT_SECRET
            )
            return spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        except Exception as e:
            logger.error(f"Error creating public Spotify client: {e}")
            return None
    
    def is_spotify_url(self, url: str) -> bool:
        """Check if URL is a Spotify URL"""
        spotify_patterns = [
            r'spotify\.com/(track|playlist|album)/',
            r'spotify:(track|playlist|album):',
            r'open\.spotify\.com/(track|playlist|album)/'
        ]
        return any(re.search(pattern, url) for pattern in spotify_patterns)
    
    def extract_spotify_info(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract Spotify content type and ID from URL"""
        patterns = {
            'track': [
                r'spotify\.com/track/([a-zA-Z0-9]+)',
                r'spotify:track:([a-zA-Z0-9]+)',
                r'open\.spotify\.com/track/([a-zA-Z0-9]+)'
            ],
            'playlist': [
                r'spotify\.com/playlist/([a-zA-Z0-9]+)',
                r'spotify:playlist:([a-zA-Z0-9]+)',
                r'open\.spotify\.com/playlist/([a-zA-Z0-9]+)'
            ],
            'album': [
                r'spotify\.com/album/([a-zA-Z0-9]+)',
                r'spotify:album:([a-zA-Z0-9]+)',
                r'open\.spotify\.com/album/([a-zA-Z0-9]+)'
            ]
        }
        
        for content_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, url)
                if match:
                    return content_type, match.group(1)
        
        return None, None
    
    async def get_track_info(self, track_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Get track information from Spotify"""
        if not self.enabled:
            return None
        
        # Try user's authenticated client first, then fallback to public
        client = self.auth_manager.get_spotify_client(user_id) if user_id else None
        if not client:
            client = self.public_client
        
        if not client:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            track = await loop.run_in_executor(None, client.track, track_id)
            
            return self._format_track_info(track)
            
        except Exception as e:
            logger.error(f"Error getting track {track_id}: {e}")
            return None
    
    async def get_playlist_info(self, playlist_id: str, user_id: Optional[str] = None) -> Tuple[Optional[Dict], List[Dict]]:
        """Get playlist information and tracks"""
        if not self.enabled:
            return None, []
        
        # Try user's authenticated client first for private playlists
        client = self.auth_manager.get_spotify_client(user_id) if user_id else None
        if not client:
            client = self.public_client
        
        if not client:
            return None, []
        
        try:
            loop = asyncio.get_event_loop()
            
            # Get playlist details
            playlist = await loop.run_in_executor(None, client.playlist, playlist_id)
            
            playlist_info = {
                'name': playlist.get('name', 'Unknown Playlist'),
                'description': playlist.get('description', ''),
                'owner': playlist.get('owner', {}).get('display_name', 'Unknown'),
                'total_tracks': playlist.get('tracks', {}).get('total', 0),
                'public': playlist.get('public', False),
                'collaborative': playlist.get('collaborative', False)
            }
            
            # Get tracks
            tracks_data = await loop.run_in_executor(
                None, 
                lambda: client.playlist_tracks(playlist_id, limit=Config.MAX_PLAYLIST_SIZE, offset=0)
            )
            
            tracks = []
            for item in tracks_data.get('items', []):
                if not item or not item.get('track'):
                    continue
                
                track_info = self._format_track_info(item['track'])
                if track_info:
                    tracks.append(track_info)
            
            return playlist_info, tracks
            
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 404:
                logger.warning(f"Playlist not found or private: {playlist_id}")
                return "not_found", []
            elif e.http_status == 403:
                logger.warning(f"Playlist access denied: {playlist_id}")
                return "access_denied", []
            else:
                logger.error(f"Spotify API error for playlist {playlist_id}: {e}")
                return None, []
        except Exception as e:
            logger.error(f"Error getting playlist {playlist_id}: {e}")
            return None, []
    
    async def get_first_track_from_playlist(self, playlist_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Get first track from playlist for immediate playback"""
        if not self.enabled:
            return None
        
        client = self.auth_manager.get_spotify_client(user_id) if user_id else None
        if not client:
            client = self.public_client
        
        if not client:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            tracks_data = await loop.run_in_executor(
                None, 
                lambda: client.playlist_tracks(playlist_id, limit=1, offset=0)
            )
            
            items = tracks_data.get('items', [])
            if not items or not items[0].get('track'):
                return None
            
            return self._format_track_info(items[0]['track'])
            
        except Exception as e:
            logger.error(f"Error getting first track from playlist {playlist_id}: {e}")
            return None
    
    async def get_user_playlists(self, user_id: str) -> List[Dict]:
        """Get user's playlists (including private ones)"""
        client = self.auth_manager.get_spotify_client(user_id)
        if not client:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            playlists = await loop.run_in_executor(None, client.current_user_playlists, 50)
            
            playlist_list = []
            for playlist in playlists.get('items', []):
                playlist_info = {
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'tracks_total': playlist['tracks']['total'],
                    'public': playlist.get('public', False),
                    'collaborative': playlist.get('collaborative', False),
                    'owner': playlist['owner']['display_name']
                }
                playlist_list.append(playlist_info)
            
            return playlist_list
            
        except Exception as e:
            logger.error(f"Error getting user playlists for {user_id}: {e}")
            return []
    
    def _format_track_info(self, track: Dict) -> Optional[Dict]:
        """Format track information consistently"""
        if not track or not track.get('name') or not track.get('artists'):
            return None
        
        artists = track.get('artists', [])
        if not artists or not isinstance(artists, list):
            return None
        
        try:
            artist_names = [
                artist.get('name', 'Unknown') 
                for artist in artists 
                if artist and isinstance(artist, dict)
            ]
            
            if not artist_names:
                return None
            
            return {
                'name': track.get('name', 'Unknown'),
                'artist': artist_names[0],
                'all_artists': artist_names,
                'search_query': f"{artist_names[0]} {track.get('name', 'Unknown')}",
                'duration_ms': track.get('duration_ms', 0),
                'preview_url': track.get('preview_url'),
                'explicit': track.get('explicit', False)
            }
            
        except Exception as e:
            logger.error(f"Error formatting track info: {e}")
            return None
    
    def get_auth_url_for_user(self, user_id: str) -> Optional[str]:
        """Get Spotify authentication URL for user"""
        return self.auth_manager.get_auth_url(user_id)
    
    def is_user_authenticated(self, user_id: str) -> bool:
        """Check if user has authenticated with Spotify"""
        return self.auth_manager.is_user_authenticated(user_id)
    
    def get_status(self) -> Dict:
        """Get handler status"""
        return {
            'enabled': self.enabled,
            'client_id_configured': bool(Config.SPOTIFY_CLIENT_ID),
            'client_secret_configured': bool(Config.SPOTIFY_CLIENT_SECRET),
            'public_client_ready': self.public_client is not None
        }