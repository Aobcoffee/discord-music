import discord
from discord.ext import commands
import asyncio
import yt_dlp
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='/', intents=intents)

# YTDL options
ytdl_format_options = {
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

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # Take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicBot:
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}
        self.queues = {}
        self.current_songs = {}

    async def add_to_queue(self, ctx, url):
        try:
            guild_id = ctx.guild.id
            
            # Initialize queue for this guild if it doesn't exist
            if guild_id not in self.queues:
                self.queues[guild_id] = []

            # Get song info
            async with ctx.typing():
                # Send thinking message
                thinking_msg = await ctx.send("Thinking...")
                
                data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(url, download=False)
                )

                if 'entries' in data:
                    # Handle playlist
                    entries = data['entries']
                    added_count = 0
                    for entry in entries[:10]:  # Limit to 10 songs from playlist
                        if entry:
                            song_info = {
                                'title': entry.get('title', 'Unknown'),
                                'url': entry.get('webpage_url', entry.get('url')),
                                'duration': entry.get('duration', 0),
                                'uploader': entry.get('uploader', 'Unknown')
                            }
                            self.queues[guild_id].append(song_info)
                            added_count += 1
                    
                    await thinking_msg.delete()
                    embed = discord.Embed(
                        title="Playlist Added to Queue",
                        description=f"📋 Added {added_count} songs to the queue!",
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)
                else:
                    # Single song
                    song_info = {
                        'title': data.get('title', 'Unknown'),
                        'url': data.get('webpage_url', data.get('url')),
                        'duration': data.get('duration', 0),
                        'uploader': data.get('uploader', 'Unknown')
                    }
                    self.queues[guild_id].append(song_info)
                    
                    await thinking_msg.delete()
                    embed = discord.Embed(
                        title="Added to Queue",
                        description=f"🎵 **{song_info['title']}**\n📍 Position in queue: {len(self.queues[guild_id])}",
                        color=discord.Color.green()
                    )
                    await ctx.send(embed=embed)

            # Start playing if nothing is currently playing
            if not self.is_playing(guild_id):
                await self.play_next(ctx)

        except Exception as e:
            if 'thinking_msg' in locals():
                await thinking_msg.delete()
            embed = discord.Embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    async def play_next(self, ctx):
        guild_id = ctx.guild.id
        
        if guild_id not in self.queues or not self.queues[guild_id]:
            return False

        voice_client = await self.get_voice_client(ctx)
        if not voice_client:
            return False

        try:
            # Get next song from queue
            song_info = self.queues[guild_id].pop(0)
            self.current_songs[guild_id] = song_info

            # Create audio source
            player = await YTDLSource.from_url(song_info['url'], loop=self.bot.loop, stream=True)
            
            # Play with callback to play next song when done
            def after_playing(error):
                if error:
                    print(f'Player error: {error}')
                else:
                    # Schedule next song
                    asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            voice_client.play(player, after=after_playing)

            # Format duration
            duration_str = ""
            if song_info['duration']:
                minutes = song_info['duration'] // 60
                seconds = song_info['duration'] % 60
                duration_str = f" [{minutes:02d}:{seconds:02d}]"

            embed = discord.Embed(
                title="Now Playing",
                description=f"🎵 **{song_info['title']}**{duration_str}\n👤 {song_info['uploader']}",
                color=discord.Color.green()
            )
            
            if len(self.queues[guild_id]) > 0:
                embed.add_field(
                    name="Up Next",
                    value=f"🎶 {self.queues[guild_id][0]['title']}\n📋 {len(self.queues[guild_id])} songs in queue",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            return True

        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Failed to play song: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return False

    def is_playing(self, guild_id):
        if guild_id in self.voice_clients:
            voice_client = self.voice_clients[guild_id]
            return voice_client.is_playing()
        return False

    async def skip_song(self, ctx):
        guild_id = ctx.guild.id
        
        if guild_id in self.voice_clients:
            voice_client = self.voice_clients[guild_id]
            if voice_client.is_playing():
                voice_client.stop()  # This will trigger the after callback to play next song
                
                embed = discord.Embed(
                    title="Song Skipped",
                    description="⏭️ Skipped to next song",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return True
        
        await ctx.send("❌ No song is currently playing!")
        return False

    async def show_queue(self, ctx):
        guild_id = ctx.guild.id
        
        if guild_id not in self.queues or not self.queues[guild_id]:
            if guild_id in self.current_songs:
                # Show currently playing song
                current = self.current_songs[guild_id]
                embed = discord.Embed(
                    title="Current Queue",
                    description=f"🎵 **Now Playing:** {current['title']}\n📋 Queue is empty",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="Queue Empty",
                    description="📭 No songs in queue. Use `/play` to add some music!",
                    color=discord.Color.orange()
                )
            await ctx.send(embed=embed)
            return

        queue_list = ""
        for i, song in enumerate(self.queues[guild_id][:10], 1):  # Show first 10 songs
            duration_str = ""
            if song['duration']:
                minutes = song['duration'] // 60
                seconds = song['duration'] % 60
                duration_str = f" [{minutes:02d}:{seconds:02d}]"
            queue_list += f"{i}. **{song['title']}**{duration_str}\n"

        embed = discord.Embed(
            title="Music Queue",
            color=discord.Color.blue()
        )

        # Add currently playing song
        if guild_id in self.current_songs:
            current = self.current_songs[guild_id]
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{current['title']}**",
                inline=False
            )

        # Add queue
        embed.add_field(
            name=f"📋 Up Next ({len(self.queues[guild_id])} songs)",
            value=queue_list if queue_list else "Queue is empty",
            inline=False
        )

        if len(self.queues[guild_id]) > 10:
            embed.add_field(
                name="",
                value=f"... and {len(self.queues[guild_id]) - 10} more songs",
                inline=False
            )

        await ctx.send(embed=embed)

    async def clear_queue(self, ctx):
        guild_id = ctx.guild.id
        
        if guild_id in self.queues:
            cleared_count = len(self.queues[guild_id])
            self.queues[guild_id].clear()
            
            embed = discord.Embed(
                title="Queue Cleared",
                description=f"🗑️ Removed {cleared_count} songs from queue",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Queue is already empty!")

    async def get_voice_client(self, ctx):
        guild_id = ctx.guild.id
        
        if guild_id in self.voice_clients:
            return self.voice_clients[guild_id]
        
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            voice_client = await channel.connect()
            self.voice_clients[guild_id] = voice_client
            return voice_client
        else:
            await ctx.send("❌ You need to be in a voice channel to use music commands!")
            return None

# Initialize music bot
music_bot = MusicBot(bot)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready to play music!')

@bot.command(name='play')
async def play(ctx, *, query):
    """Play a song from YouTube by name or URL"""
    if not query:
        await ctx.send("❌ Please provide a song name or URL!")
        return
    
    # If it's not a URL, search for it
    if not query.startswith(('http://', 'https://', 'www.')):
        query = f"ytsearch:{query}"
    
    await music_bot.add_to_queue(ctx, query)

@bot.command(name='skip')
async def skip(ctx):
    """Skip the current song"""
    thinking_msg = await ctx.send("Thinking...")
    await thinking_msg.delete()
    await music_bot.skip_song(ctx)

@bot.command(name='queue')
async def queue(ctx):
    """Show the current music queue"""
    thinking_msg = await ctx.send("Thinking...")
    await thinking_msg.delete()
    await music_bot.show_queue(ctx)

@bot.command(name='clear')
async def clear_queue(ctx):
    """Clear the music queue"""
    thinking_msg = await ctx.send("Thinking...")
    await thinking_msg.delete()
    await music_bot.clear_queue(ctx)

@bot.command(name='stop')
async def stop(ctx):
    """Stop the current song and disconnect"""
    thinking_msg = await ctx.send("Thinking...")
    
    guild_id = ctx.guild.id
    
    if guild_id in music_bot.voice_clients:
        voice_client = music_bot.voice_clients[guild_id]
        if voice_client.is_playing():
            voice_client.stop()
        await voice_client.disconnect()
        del music_bot.voice_clients[guild_id]
        
        # Clear queue and current song
        if guild_id in music_bot.queues:
            music_bot.queues[guild_id].clear()
        if guild_id in music_bot.current_songs:
            del music_bot.current_songs[guild_id]
        
        await thinking_msg.delete()
        embed = discord.Embed(
            title="Music Stopped",
            description="⏹️ Stopped playing and disconnected from voice channel",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    else:
        await thinking_msg.delete()
        await ctx.send("❌ I'm not currently playing anything!")

@bot.command(name='pause')
async def pause(ctx):
    """Pause the current song"""
    thinking_msg = await ctx.send("Thinking...")
    
    guild_id = ctx.guild.id
    
    if guild_id in music_bot.voice_clients:
        voice_client = music_bot.voice_clients[guild_id]
        if voice_client.is_playing():
            voice_client.pause()
            await thinking_msg.delete()
            embed = discord.Embed(
                title="Music Paused",
                description="⏸️ Music has been paused",
                color=discord.Color.yellow()
            )
            await ctx.send(embed=embed)
        else:
            await thinking_msg.delete()
            await ctx.send("❌ No music is currently playing!")
    else:
        await thinking_msg.delete()
        await ctx.send("❌ I'm not connected to a voice channel!")

@bot.command(name='resume')
async def resume(ctx):
    """Resume the paused song"""
    thinking_msg = await ctx.send("Thinking...")
    
    guild_id = ctx.guild.id
    
    if guild_id in music_bot.voice_clients:
        voice_client = music_bot.voice_clients[guild_id]
        if voice_client.is_paused():
            voice_client.resume()
            await thinking_msg.delete()
            embed = discord.Embed(
                title="Music Resumed",
                description="▶️ Music has been resumed",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await thinking_msg.delete()
            await ctx.send("❌ Music is not paused!")
    else:
        await thinking_msg.delete()
        await ctx.send("❌ I'm not connected to a voice channel!")

@bot.command(name='help_music')
async def help_music(ctx):
    """Show available music commands"""
    thinking_msg = await ctx.send("Thinking...")
    await thinking_msg.delete()
    
    embed = discord.Embed(
        title="🎵 Music Bot Commands",
        description="Here are the available music commands:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="/play <song name or URL>",
        value="Add a song to the queue (plays immediately if nothing is playing)",
        inline=False
    )
    embed.add_field(
        name="/skip",
        value="Skip the current song and play the next one in queue",
        inline=False
    )
    embed.add_field(
        name="/queue",
        value="Show the current music queue with song titles",
        inline=False
    )
    embed.add_field(
        name="/clear",
        value="Clear all songs from the queue",
        inline=False
    )
    embed.add_field(
        name="/pause",
        value="Pause the current song",
        inline=False
    )
    embed.add_field(
        name="/resume",
        value="Resume the paused song",
        inline=False
    )
    embed.add_field(
        name="/stop",
        value="Stop music, clear queue, and disconnect from voice channel",
        inline=False
    )
    embed.add_field(
        name="✨ New Features:",
        value="• **Queue System** - Add multiple songs that play automatically\n• **Skip Songs** - Jump to the next track\n• **Playlist Support** - Add YouTube playlists\n• **Smart Responses** - Bot shows 'thinking' while processing",
        inline=False
    )
    embed.add_field(
        name="Examples:",
        value="`/play Never Gonna Give You Up`\n`/play https://www.youtube.com/watch?v=dQw4w9WgXcQ`\n`/play https://www.youtube.com/playlist?list=...`\n`/queue` - See what's coming up\n`/skip` - Next song please!",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument! Use `/help_music` for command usage.")
    else:
        print(f'Error: {error}')
        await ctx.send(f"❌ An error occurred: {str(error)}")

if __name__ == "__main__":
    # Get token from environment variable
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token.")
        exit(1)
    
    bot.run(TOKEN)