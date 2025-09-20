"""
Discord Music Bot
Supports YouTube and Spotify (including private playlists with OAuth)
"""
import discord
from discord.ext import commands
import asyncio
import logging
from typing import Optional

from config import Config
from spotify_handler import SpotifyHandler
from music_player import MusicManager, Track
from audio_source import AudioSource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate configuration
config_status = Config.validate()
if not config_status['discord_ready']:
    logger.error("Discord bot token not configured!")
    exit(1)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=Config.DISCORD_COMMAND_PREFIX, intents=intents)

# Initialize managers
music_manager = MusicManager(bot)
spotify_handler = SpotifyHandler()
audio_source = AudioSource()

@bot.event
async def on_ready():
    """Bot ready event"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Spotify integration: {"enabled" if spotify_handler.enabled else "disabled"}')
    logger.info('Bot is ready to play music!')

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state updates"""
    if member == bot.user:
        return
    
    # Auto-disconnect if bot is alone in voice channel
    if before.channel and bot.user in before.channel.members:
        if len([m for m in before.channel.members if not m.bot]) == 0:
            player = music_manager.players.get(before.channel.guild.id)
            if player and player.voice_client and player.voice_client.channel == before.channel:
                await asyncio.sleep(60)  # Wait 1 minute before disconnecting
                if len([m for m in before.channel.members if not m.bot]) == 0:
                    await player.disconnect()

# Helper function
async def ensure_voice_connection(ctx) -> bool:
    """Ensure bot is connected to user's voice channel"""
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to use music commands!")
        return False
    
    player = music_manager.get_player(ctx.guild.id)
    if not await player.connect_to_voice(ctx.author.voice.channel):
        await ctx.send("Failed to connect to voice channel!")
        return False
    
    return True

@bot.command(name='play', aliases=['p'])
async def play(ctx, *, query: str):
    """Play music from YouTube or Spotify"""
    if not query:
        await ctx.send("Please provide a song name or URL!")
        return
    
    if not await ensure_voice_connection(ctx):
        return
    
    thinking_msg = await ctx.send("Processing...")
    
    try:
        player = music_manager.get_player(ctx.guild.id)
        
        # Handle Spotify URLs
        if spotify_handler.is_spotify_url(query):
            await handle_spotify_content(ctx, query, thinking_msg, player)
        else:
            await handle_youtube_content(ctx, query, thinking_msg, player)
            
    except Exception as e:
        logger.error(f"Error in play command: {e}")
        await thinking_msg.edit(content="An error occurred while processing your request.")

async def handle_spotify_content(ctx, url: str, thinking_msg, player):
    """Handle Spotify URL processing - simplified without authentication"""
    content_type, content_id = spotify_handler.extract_spotify_info(url)
    
    if content_type == 'playlist':
        await handle_spotify_playlist(ctx, content_id, thinking_msg, player)
    elif content_type == 'track':
        await handle_spotify_track(ctx, content_id, thinking_msg, player)
    elif content_type == 'album':
        await handle_spotify_album(ctx, content_id, thinking_msg, player)
    else:
        await thinking_msg.edit(content="❌ Invalid Spotify URL.")

async def handle_spotify_playlist(ctx, playlist_id: str, thinking_msg, player):
    """Handle Spotify playlist with optimized loading - no auth required"""
    # Get first track for immediate playback
    first_track_info = await spotify_handler.get_first_track_from_playlist(playlist_id)
    
    if not first_track_info:
        await thinking_msg.edit(content="❌ Could not access playlist or playlist is empty.")
        return
    
    # Create and add first track
    first_track = Track.from_spotify(
        first_track_info['name'],
        first_track_info['artist']
    )
    
    try:
        player.queue.add_track(first_track)
        
        await thinking_msg.edit(content=f"🎵 **Spotify Playlist Started**\nPlaying: **{first_track}**\nProcessing remaining tracks...")
        
        # Start playing if nothing is currently playing
        if not player.is_playing():
            await player.play_next(ctx)
        
        # Process remaining tracks in background
        asyncio.create_task(process_spotify_playlist_background(ctx, playlist_id, player))
        
    except ValueError as e:
        await thinking_msg.edit(content=f"❌ {str(e)}")

async def process_spotify_playlist_background(ctx, playlist_id: str, player):
    """Process remaining playlist tracks in background"""
    try:
        playlist_info, tracks = await spotify_handler.get_playlist_info(playlist_id)
        
        if not tracks or len(tracks) <= 1:
            return
        
        # Skip first track (already added)
        remaining_tracks = tracks[1:]
        spotify_tracks = [
            Track.from_spotify(track['name'], track['artist'])
            for track in remaining_tracks
        ]
        
        added_count = player.queue.add_tracks(spotify_tracks)
        
        if playlist_info and isinstance(playlist_info, dict):
            playlist_name = playlist_info.get('name', 'Unknown Playlist')
            embed = discord.Embed(
                title="✅ Spotify Playlist Loaded",
                description=f"**{playlist_name}**\nAdded {added_count} more tracks to queue.",
                color=discord.Color.green()
            )
            
            if not playlist_info.get('public', True):
                embed.set_footer(text="🔒 Private Playlist")
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error processing Spotify playlist background: {e}")

async def handle_spotify_track(ctx, track_id: str, thinking_msg, player):
    """Handle single Spotify track"""
    track_info = await spotify_handler.get_track_info(track_id)
    
    if not track_info:
        await thinking_msg.edit(content="❌ Could not get track information.")
        return
    
    track = Track.from_spotify(track_info['name'], track_info['artist'])
    
    try:
        position = player.queue.add_track(track)
        
        embed = discord.Embed(
            title="🎵 Spotify Track Added",
            description=f"**{track}**\nPosition in queue: {position}",
            color=discord.Color.green()
        )
        
        await thinking_msg.edit(content="", embed=embed)
        
        if not player.is_playing():
            await player.play_next(ctx)
            
    except ValueError as e:
        await thinking_msg.edit(content=f"❌ {str(e)}")

async def handle_spotify_album(ctx, album_id: str, thinking_msg, player):
    """Handle Spotify album with optimized loading"""
    # Get first track for immediate playback
    first_track_info = await spotify_handler.get_first_track_from_album(album_id)
    
    if not first_track_info:
        await thinking_msg.edit(content="❌ Could not access album or album is empty.")
        return
    
    # Create and add first track
    first_track = Track.from_spotify(
        first_track_info['name'],
        first_track_info['artist']
    )
    
    try:
        player.queue.add_track(first_track)
        
        await thinking_msg.edit(content=f"🎵 **Spotify Album Started**\nPlaying: **{first_track}**\nProcessing remaining tracks...")
        
        # Start playing if nothing is currently playing
        if not player.is_playing():
            await player.play_next(ctx)
        
        # Process remaining tracks in background
        asyncio.create_task(process_spotify_album_background(ctx, album_id, player))
        
    except ValueError as e:
        await thinking_msg.edit(content=f"❌ {str(e)}")

async def process_spotify_album_background(ctx, album_id: str, player):
    """Process remaining album tracks in background"""
    try:
        album_info, tracks = await spotify_handler.get_album_info(album_id)
        
        if not tracks or len(tracks) <= 1:
            return
        
        # Skip first track (already added)
        remaining_tracks = tracks[1:]
        spotify_tracks = [
            Track.from_spotify(track['name'], track['artist'])
            for track in remaining_tracks
        ]
        
        added_count = player.queue.add_tracks(spotify_tracks)
        
        if album_info and isinstance(album_info, dict):
            album_name = album_info.get('name', 'Unknown Album')
            embed = discord.Embed(
                title="✅ Spotify Album Loaded",
                description=f"**{album_name}**\nAdded {added_count} more tracks to queue.",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error processing Spotify album background: {e}")

async def handle_youtube_content(ctx, query: str, thinking_msg, player):
    """Handle YouTube search or URL"""
    # Add ytsearch prefix if not a URL
    if not query.startswith(('http://', 'https://', 'www.')):
        query = f"ytsearch:{query}"
    
    youtube_data = await audio_source.get_youtube_info(query)
    
    if not youtube_data:
        await thinking_msg.edit(content="Could not find the requested content.")
        return
    
    track = Track.from_youtube(
        title=youtube_data.get('title', 'Unknown'),
        url=youtube_data.get('webpage_url') or youtube_data.get('url'),
        uploader=youtube_data.get('uploader', 'Unknown'),
        duration=youtube_data.get('duration', 0)
    )
    
    try:
        position = player.queue.add_track(track)
        
        embed = discord.Embed(
            title="🎵 YouTube Track Added",
            description=f"**{track}**\nPosition in queue: {position}",
            color=discord.Color.red()
        )
        
        await thinking_msg.edit(content="", embed=embed)
        
        if not player.is_playing():
            await player.play_next(ctx)
            
    except ValueError as e:
        await thinking_msg.edit(content=f"{str(e)}")

@bot.command(name='skip', aliases=['s'])
async def skip(ctx):
    """Skip current track"""
    player = music_manager.get_player(ctx.guild.id)
    
    if not player.is_connected():
        await ctx.send("Not connected to a voice channel!")
        return
    
    if player.skip():
        await ctx.send("⏭️ Skipped to next track")
    else:
        await ctx.send("Nothing to skip!")

@bot.command(name='pause')
async def pause(ctx):
    """Pause playback"""
    player = music_manager.get_player(ctx.guild.id)
    
    if player.pause():
        await ctx.send("⏸️ Playback paused")
    else:
        await ctx.send("Nothing is playing!")

@bot.command(name='resume')
async def resume(ctx):
    """Resume playback"""
    player = music_manager.get_player(ctx.guild.id)
    
    if player.resume():
        await ctx.send("▶️ Playback resumed")
    else:
        await ctx.send("Nothing is paused!")

@bot.command(name='stop')
async def stop(ctx):
    """Stop playback and clear queue"""
    player = music_manager.get_player(ctx.guild.id)
    
    if player.is_connected():
        player.stop()
        cleared = player.queue.clear()
        await player.disconnect()
        
        embed = discord.Embed(
            title="⏹️ Playback Stopped",
            description=f"Cleared {cleared} tracks from queue and disconnected.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("Not connected to a voice channel!")

@bot.command(name='queue', aliases=['q'])
async def show_queue(ctx):
    """Show current queue"""
    player = music_manager.get_player(ctx.guild.id)
    queue_info = player.queue.get_queue_info()
    
    if not queue_info['current'] and not queue_info['length']:
        await ctx.send("📭 Queue is empty!")
        return
    
    embed = discord.Embed(title="🎵 Music Queue", color=discord.Color.blue())
    
    if queue_info['current']:
        embed.add_field(
            name="Now Playing",
            value=queue_info['current'],
            inline=False
        )
    
    if queue_info['length'] > 0:
        queue_list = ""
        for i, track in enumerate(player.queue.tracks[:10], 1):
            queue_list += f"{i}. **{track}**\n"
        
        embed.add_field(
            name=f"Up Next ({queue_info['length']} tracks)",
            value=queue_list or "Queue is empty",
            inline=False
        )
        
        if queue_info['length'] > 10:
            embed.add_field(
                name="",
                value=f"... and {queue_info['length'] - 10} more tracks",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.command(name='clear')
async def clear_queue(ctx):
    """Clear the queue"""
    player = music_manager.get_player(ctx.guild.id)
    cleared = player.queue.clear()
    
    if cleared > 0:
        await ctx.send(f"🗑️ Cleared {cleared} tracks from queue")
    else:
        await ctx.send("Queue is already empty!")

@bot.command(name='help_music')
async def help_music(ctx):
    """Show music bot help"""
    embed = discord.Embed(
        title="🎵 Music Bot Commands",
        description="Here are all available music commands:",
        color=discord.Color.blue()
    )
    
    commands_list = [
        ("**/play <song/URL>**", "Play music from YouTube or Spotify"),
        ("**/skip**", "Skip current track"),
        ("**/pause**", "Pause playback"),
        ("**/resume**", "Resume playback"),
        ("**/stop**", "Stop and disconnect"),
        ("**/queue**", "Show current queue"),
        ("**/clear**", "Clear queue")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.add_field(
        name="🎵 Supported Sources",
        value="• **YouTube** - URLs and search\n• **Spotify** - Tracks, playlists, albums, radio playlists\n• **Auto-search** - Just type song names!",
        inline=False
    )
    
    embed.add_field(
        name="🎵 Spotify Support",
        value="Works with public Spotify content without authentication:\n• Individual tracks\n• Public playlists\n• Albums\n• Radio playlists",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Command not found! Use `/help_music` to see available commands.")
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing required argument! Use `/help_music` for command usage.")
    else:
        logger.error(f'Command error: {error}')
        await ctx.send(f"An error occurred: {str(error)}")

@bot.event
async def on_disconnect():
    """Clean up on disconnect"""
    await music_manager.cleanup_all()

if __name__ == "__main__":
    if not Config.DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN not found in environment variables!")
        exit(1)
    
    try:
        bot.run(Config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        asyncio.run(music_manager.cleanup_all())