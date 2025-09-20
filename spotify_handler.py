import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SpotifyHandler:
    def __init__(self):
        """Initialize Spotify client with credentials from environment variables"""
        self.spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if self.spotify_client_id and self.spotify_client_secret:
            try:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=self.spotify_client_id,
                    client_secret=self.spotify_client_secret
                )
                self.spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
                self.enabled = True
            except Exception as e:
                print(f"Error initializing Spotify client: {e}")
                self.spotify = None
                self.enabled = False
        else:
            print("Spotify credentials not found. Spotify features will be disabled.")
            print("Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to your .env file to enable Spotify support.")
            self.spotify = None
            self.enabled = False

    def is_spotify_url(self, url):
        """Check if the provided URL is a Spotify URL"""
        spotify_patterns = [
            r'spotify\.com/(track|playlist|album)/',
            r'spotify:/(track|playlist|album):',
            r'open\.spotify\.com/(track|playlist|album)/'
        ]
        return any(re.search(pattern, url) for pattern in spotify_patterns)

    def extract_spotify_info(self, url):
        """Extract Spotify track/playlist/album ID and type from URL"""
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

    async def get_track_info(self, track_id):
        """Get track information from Spotify API"""
        if not self.enabled:
            return None
        
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            track = await loop.run_in_executor(None, self.spotify.track, track_id)
            
            # Validate essential track data
            if not track or not track.get('name') or not track.get('artists'):
                print(f"Spotify track missing essential data: {track_id}")
                return None
            
            artists = track.get('artists', [])
            if not artists or not isinstance(artists, list) or len(artists) == 0:
                print(f"Spotify track has no valid artists: {track_id}")
                return None
            
            # Safely extract artist names
            artist_names = [artist.get('name', 'Unknown') for artist in artists if artist and isinstance(artist, dict)]
            if not artist_names:
                print(f"Could not extract artist names for track: {track_id}")
                return None
            
            # Safely extract album info
            album_info = track.get('album', {})
            album_name = album_info.get('name', 'Unknown') if album_info else 'Unknown'
            
            # Safely extract duration
            duration_ms = track.get('duration_ms', 0)
            duration = duration_ms // 1000 if duration_ms and isinstance(duration_ms, int) else 0
            
            # Extract track information
            track_info = {
                'name': track.get('name', 'Unknown'),
                'artists': artist_names,
                'duration': duration,
                'album': album_name,
                'release_date': album_info.get('release_date', 'Unknown') if album_info else 'Unknown',
                'popularity': track.get('popularity', 0),
                'external_urls': track.get('external_urls', {}),
                'search_query': f"{artist_names[0]} {track.get('name', 'Unknown')}"
            }
            
            return track_info
            
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg:
                print(f"Spotify track not found: {track_id}")
                return "not_found"
            elif "403" in error_msg or "forbidden" in error_msg:
                print(f"Spotify track access denied: {track_id}")
                return "access_denied"
            else:
                print(f"Error getting Spotify track {track_id}: {e}")
                return None

    async def get_playlist_info(self, playlist_id):
        """Get playlist information and tracks from Spotify API"""
        if not self.enabled:
            return None, []
        
        try:
            loop = asyncio.get_event_loop()
            
            # Get playlist details
            playlist = await loop.run_in_executor(None, self.spotify.playlist, playlist_id)
            
            playlist_info = {
                'name': playlist.get('name', 'Unknown Playlist'),
                'description': playlist.get('description', ''),
                'owner': playlist.get('owner', {}).get('display_name', 'Unknown'),
                'total_tracks': playlist.get('tracks', {}).get('total', 0),
                'external_urls': playlist.get('external_urls', {})
            }
            
            # Get playlist tracks (limit to 50 for performance)
            tracks_data = await loop.run_in_executor(
                None, 
                lambda: self.spotify.playlist_tracks(playlist_id, limit=50, offset=0)
            )
            
            tracks = []
            for item in tracks_data.get('items', []):
                # Skip if item or track is None
                if not item or not item.get('track'):
                    continue
                    
                track = item['track']
                
                # Skip if track is None or missing essential data
                if not track or not track.get('name') or not track.get('artists'):
                    continue
                
                # Safely extract artist names
                artists = track.get('artists', [])
                if not artists or not isinstance(artists, list) or len(artists) == 0:
                    continue
                
                try:
                    artist_names = [artist.get('name', 'Unknown') for artist in artists if artist and isinstance(artist, dict)]
                    if not artist_names:
                        continue
                    
                    # Only keep essential data for playback
                    track_info = {
                        'name': track.get('name', 'Unknown'),
                        'artist': artist_names[0],
                        'search_query': f"{artist_names[0]} {track.get('name', 'Unknown')}"
                    }
                    tracks.append(track_info)
                    
                except Exception as track_error:
                    print(f"Error processing track '{track.get('name', 'Unknown')}': {track_error}")
                    continue
            
            return playlist_info, tracks
            
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg:
                print(f"Spotify playlist not found or private: {playlist_id}")
                return "not_found", []
            elif "403" in error_msg or "forbidden" in error_msg:
                print(f"Spotify playlist access denied: {playlist_id}")
                return "access_denied", []
            else:
                print(f"Error getting Spotify playlist {playlist_id}: {e}")
                return None, []

    async def get_first_track_from_playlist(self, playlist_id):
        """Get only the first track from a playlist for immediate playback"""
        if not self.enabled:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            
            # Get only first track from playlist
            tracks_data = await loop.run_in_executor(
                None, 
                lambda: self.spotify.playlist_tracks(playlist_id, limit=1, offset=0)
            )
            
            items = tracks_data.get('items', [])
            if not items:
                return None
                
            item = items[0]
            if not item or not item.get('track'):
                return None
                
            track = item['track']
            if not track or not track.get('name') or not track.get('artists'):
                return None
            
            # Safely extract artist names
            artists = track.get('artists', [])
            if not artists or not isinstance(artists, list) or len(artists) == 0:
                return None
            
            artist_names = [artist.get('name', 'Unknown') for artist in artists if artist and isinstance(artist, dict)]
            if not artist_names:
                return None
            
            return {
                'name': track.get('name', 'Unknown'),
                'artist': artist_names[0],
                'search_query': f"{artist_names[0]} {track.get('name', 'Unknown')}"
            }
            
        except Exception as e:
            print(f"Error getting first track from playlist {playlist_id}: {e}")
            return None

    async def get_album_info(self, album_id):
        """Get album information and tracks from Spotify API"""
        if not self.enabled:
            return None, []
        
        try:
            loop = asyncio.get_event_loop()
            
            # Get album details
            album = await loop.run_in_executor(None, self.spotify.album, album_id)
            
            # Safely extract album info
            album_artists = album.get('artists', [])
            album_artist_names = [artist.get('name', 'Unknown') for artist in album_artists if artist and isinstance(artist, dict)]
            
            album_info = {
                'name': album.get('name', 'Unknown Album'),
                'artists': album_artist_names,
                'release_date': album.get('release_date', 'Unknown'),
                'total_tracks': album.get('total_tracks', 0),
                'external_urls': album.get('external_urls', {})
            }
            
            tracks = []
            album_tracks = album.get('tracks', {}).get('items', [])
            
            for track in album_tracks:
                # Skip if track is None or missing essential data
                if not track or not track.get('name') or not track.get('artists'):
                    continue
                
                # Safely extract artist names
                artists = track.get('artists', [])
                if not artists or not isinstance(artists, list) or len(artists) == 0:
                    continue
                
                try:
                    artist_names = [artist.get('name', 'Unknown') for artist in artists if artist and isinstance(artist, dict)]
                    if not artist_names:
                        continue
                    
                    # Safely extract duration
                    duration_ms = track.get('duration_ms', 0)
                    duration = duration_ms // 1000 if duration_ms and isinstance(duration_ms, int) else 0
                    
                    track_info = {
                        'name': track.get('name', 'Unknown'),
                        'artists': artist_names,
                        'duration': duration,
                        'album': album.get('name', 'Unknown Album'),
                        'search_query': f"{artist_names[0]} {track.get('name', 'Unknown')}"
                    }
                    tracks.append(track_info)
                    
                except Exception as track_error:
                    print(f"Error processing album track '{track.get('name', 'Unknown')}': {track_error}")
                    continue
            
            return album_info, tracks
            
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg:
                print(f"Spotify album not found: {album_id}")
                return "not_found", []
            elif "403" in error_msg or "forbidden" in error_msg:
                print(f"Spotify album access denied: {album_id}")
                return "access_denied", []
            else:
                print(f"Error getting Spotify album {album_id}: {e}")
                return None, []

    async def search_track(self, query, limit=1):
        """Search for tracks on Spotify"""
        if not self.enabled:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, 
                lambda: self.spotify.search(q=query, type='track', limit=limit)
            )
            
            tracks = []
            search_tracks = results.get('tracks', {}).get('items', [])
            
            for track in search_tracks:
                # Skip if track is None or missing essential data
                if not track or not track.get('name') or not track.get('artists'):
                    continue
                
                # Safely extract artist names
                artists = track.get('artists', [])
                if not artists or not isinstance(artists, list) or len(artists) == 0:
                    continue
                
                try:
                    artist_names = [artist.get('name', 'Unknown') for artist in artists if artist and isinstance(artist, dict)]
                    if not artist_names:
                        continue
                    
                    # Safely extract album info
                    album_info = track.get('album', {})
                    album_name = album_info.get('name', 'Unknown') if album_info else 'Unknown'
                    
                    # Safely extract duration
                    duration_ms = track.get('duration_ms', 0)
                    duration = duration_ms // 1000 if duration_ms and isinstance(duration_ms, int) else 0
                    
                    track_info = {
                        'name': track.get('name', 'Unknown'),
                        'artists': artist_names,
                        'duration': duration,
                        'album': album_name,
                        'popularity': track.get('popularity', 0),
                        'external_urls': track.get('external_urls', {}),
                        'search_query': f"{artist_names[0]} {track.get('name', 'Unknown')}"
                    }
                    tracks.append(track_info)
                    
                except Exception as track_error:
                    print(f"Error processing search result '{track.get('name', 'Unknown')}': {track_error}")
                    continue
            
            return tracks
            
        except Exception as e:
            print(f"Error searching Spotify for '{query}': {e}")
            return []

    async def process_spotify_url(self, url):
        """Process any Spotify URL and return formatted track information"""
        if not self.is_spotify_url(url):
            return None, []
        
        content_type, content_id = self.extract_spotify_info(url)
        
        if not content_type or not content_id:
            return None, []
        
        if content_type == 'track':
            track_info = await self.get_track_info(content_id)
            if track_info:
                return 'track', [track_info]
            
        elif content_type == 'playlist':
            playlist_info, tracks = await self.get_playlist_info(content_id)
            if playlist_info and tracks:
                return 'playlist', tracks
            
        elif content_type == 'album':
            album_info, tracks = await self.get_album_info(content_id)
            if album_info and tracks:
                return 'album', tracks
        
        return None, []

    def format_duration(self, seconds):
        """Format duration from seconds to MM:SS"""
        if not seconds:
            return "Unknown"
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def get_status(self):
        """Get current status of Spotify integration"""
        return {
            'enabled': self.enabled,
            'client_id_configured': bool(self.spotify_client_id),
            'client_secret_configured': bool(self.spotify_client_secret)
        }

# Example usage and testing
if __name__ == "__main__":
    async def test_spotify():
        """Test function for Spotify integration"""
        handler = SpotifyHandler()
        
        if not handler.enabled:
            print("Spotify not enabled. Please check your credentials.")
            return
        
        # Test track
        print("Testing Spotify track...")
        track_url = "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"  # Never Gonna Give You Up
        content_type, tracks = await handler.process_spotify_url(track_url)
        if tracks:
            print(f"Found {content_type}: {tracks[0]['search_query']}")
        
        # Test search
        print("\nTesting Spotify search...")
        search_results = await handler.search_track("Never Gonna Give You Up Rick Astley")
        if search_results:
            print(f"Search result: {search_results[0]['search_query']}")
    
    # Run test if this file is executed directly
    asyncio.run(test_spotify())