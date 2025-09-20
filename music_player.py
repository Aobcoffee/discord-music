"""
Music queue and playback management
"""
import asyncio
import discord
from typing import Dict, List, Optional, Any
from audio_source import AudioSource, YTDLSource
from spotify_handler import SpotifyHandler
from config import Config
import logging

logger = logging.getLogger(__name__)

class Track:
    """Represents a track in the music queue"""
    
    def __init__(self, title: str, artist: str, search_query: str, 
                 url: Optional[str] = None, source: str = 'youtube', 
                 user_id: Optional[str] = None, **kwargs):
        self.title = title
        self.artist = artist
        self.search_query = search_query
        self.url = url
        self.source = source
        self.user_id = user_id
        self.needs_resolution = url is None
        self.duration = kwargs.get('duration', 0)
        self.uploader = kwargs.get('uploader', artist)
        
    def __str__(self) -> str:
        return f"{self.artist} - {self.title}"
    
    @classmethod
    def from_youtube(cls, title: str, url: str, uploader: str = 'Unknown', duration: int = 0):
        """Create track from YouTube data"""
        return cls(
            title=title,
            artist=uploader,
            search_query=title,
            url=url,
            source='youtube',
            duration=duration,
            uploader=uploader
        )
    
    @classmethod
    def from_spotify(cls, name: str, artist: str, user_id: Optional[str] = None):
        """Create track from Spotify data"""
        return cls(
            title=name,
            artist=artist,
            search_query=f"{artist} {name}",
            source='spotify->youtube',
            user_id=user_id
        )

class MusicQueue:
    """Manages music queue for a guild"""
    
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.tracks: List[Track] = []
        self.current_track: Optional[Track] = None
        self.loop_mode = False
        self.shuffle_mode = False
    
    def add_track(self, track: Track) -> int:
        """Add track to queue and return position"""
        if len(self.tracks) >= Config.MAX_QUEUE_SIZE:
            raise ValueError(f"Queue is full (max {Config.MAX_QUEUE_SIZE} tracks)")
        
        self.tracks.append(track)
        return len(self.tracks)
    
    def add_tracks(self, tracks: List[Track]) -> int:
        """Add multiple tracks to queue"""
        added = 0
        for track in tracks:
            if len(self.tracks) >= Config.MAX_QUEUE_SIZE:
                break
            self.tracks.append(track)
            added += 1
        return added
    
    def get_next_track(self) -> Optional[Track]:
        """Get next track from queue"""
        if not self.tracks:
            return None
        
        if self.shuffle_mode:
            import random
            track = random.choice(self.tracks)
            self.tracks.remove(track)
        else:
            track = self.tracks.pop(0)
        
        return track
    
    def peek_next(self) -> Optional[Track]:
        """Peek at next track without removing it"""
        return self.tracks[0] if self.tracks else None
    
    def clear(self) -> int:
        """Clear queue and return number of tracks removed"""
        count = len(self.tracks)
        self.tracks.clear()
        return count
    
    def remove_track(self, index: int) -> Optional[Track]:
        """Remove track at index"""
        if 0 <= index < len(self.tracks):
            return self.tracks.pop(index)
        return None
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Get queue information"""
        return {
            'length': len(self.tracks),
            'current': str(self.current_track) if self.current_track else None,
            'next': str(self.tracks[0]) if self.tracks else None,
            'loop_mode': self.loop_mode,
            'shuffle_mode': self.shuffle_mode
        }

class MusicPlayer:
    """Handles music playback for a guild"""
    
    def __init__(self, guild_id: int, bot):
        self.guild_id = guild_id
        self.bot = bot
        self.queue = MusicQueue(guild_id)
        self.voice_client: Optional[discord.VoiceClient] = None
        self.audio_source = AudioSource()
        self.spotify_handler = SpotifyHandler()
        self.is_paused = False
        
    async def connect_to_voice(self, voice_channel: discord.VoiceChannel) -> bool:
        """Connect to voice channel"""
        try:
            if self.voice_client and self.voice_client.is_connected():
                if self.voice_client.channel.id == voice_channel.id:
                    return True
                await self.voice_client.move_to(voice_channel)
            else:
                self.voice_client = await voice_channel.connect()
            
            logger.info(f"Connected to voice channel {voice_channel.name} in guild {self.guild_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to voice channel: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from voice channel"""
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
            logger.info(f"Disconnected from voice channel in guild {self.guild_id}")
    
    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.voice_client and self.voice_client.is_playing()
    
    def is_connected(self) -> bool:
        """Check if connected to voice"""
        return self.voice_client and self.voice_client.is_connected()
    
    async def play_next(self, ctx) -> bool:
        """Play next track in queue"""
        if not self.voice_client or not self.voice_client.is_connected():
            return False
        
        track = self.queue.get_next_track()
        if not track:
            return False
        
        try:
            # Resolve URL if needed
            if track.needs_resolution:
                await self._resolve_track_url(track)
            
            if not track.url:
                logger.warning(f"Could not resolve URL for track: {track}")
                return await self.play_next(ctx)  # Try next track
            
            # Create audio source
            source = await self.audio_source.create_audio_source(track.url)
            if not source:
                logger.warning(f"Could not create audio source for track: {track}")
                return await self.play_next(ctx)  # Try next track
            
            # Start playback
            self.queue.current_track = track
            
            def after_playing(error):
                if error:
                    logger.error(f"Player error: {error}")
                else:
                    # Schedule next song
                    asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)
            
            self.voice_client.play(source, after=after_playing)
            
            # Send now playing message
            await self._send_now_playing_message(ctx, track, source)
            
            return True
            
        except Exception as e:
            logger.error(f"Error playing track {track}: {e}")
            return await self.play_next(ctx)  # Try next track
    
    async def _resolve_track_url(self, track: Track):
        """Resolve YouTube URL for track"""
        try:
            search_query = f"ytsearch:{track.search_query}"
            youtube_data = await self.audio_source.get_youtube_info(search_query)
            
            if youtube_data:
                track.url = youtube_data.get('webpage_url') or youtube_data.get('url')
                track.duration = youtube_data.get('duration', 0)
                track.uploader = youtube_data.get('uploader', track.artist)
                track.needs_resolution = False
                
        except Exception as e:
            logger.error(f"Error resolving URL for track {track}: {e}")
    
    async def _send_now_playing_message(self, ctx, track: Track, source: YTDLSource):
        """Send now playing message"""
        try:
            duration_str = ""
            if track.duration:
                minutes = track.duration // 60
                seconds = track.duration % 60
                duration_str = f" [{minutes:02d}:{seconds:02d}]"
            
            embed = discord.Embed(
                title="Now Playing",
                description=f"**{track}**{duration_str}\n{track.uploader}",
                color=discord.Color.green()
            )
            
            # Add queue info
            next_track = self.queue.peek_next()
            if next_track:
                embed.add_field(
                    name="Up Next",
                    value=f"{next_track}\n{len(self.queue.tracks)} songs in queue",
                    inline=False
                )
            
            # Add source info
            if track.source == 'spotify->youtube':
                embed.set_footer(text="🎵 From Spotify")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error sending now playing message: {e}")
    
    def pause(self) -> bool:
        """Pause playback"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            self.is_paused = True
            return True
        return False
    
    def resume(self) -> bool:
        """Resume playback"""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            self.is_paused = False
            return True
        return False
    
    def stop(self) -> bool:
        """Stop playback"""
        if self.voice_client and (self.voice_client.is_playing() or self.voice_client.is_paused()):
            self.voice_client.stop()
            self.is_paused = False
            return True
        return False
    
    def skip(self) -> bool:
        """Skip current track"""
        return self.stop()  # Stopping will trigger next track via callback

class MusicManager:
    """Manages music players for all guilds"""
    
    def __init__(self, bot):
        self.bot = bot
        self.players: Dict[int, MusicPlayer] = {}
    
    def get_player(self, guild_id: int) -> MusicPlayer:
        """Get or create player for guild"""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild_id, self.bot)
        return self.players[guild_id]
    
    async def cleanup_player(self, guild_id: int):
        """Clean up player for guild"""
        if guild_id in self.players:
            await self.players[guild_id].disconnect()
            del self.players[guild_id]
    
    async def cleanup_all(self):
        """Clean up all players"""
        for player in self.players.values():
            await player.disconnect()
        self.players.clear()