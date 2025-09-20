# Discord Music Bot 🎵

A simple Discord bot that can play music in voice channels using YouTube as the source.

## Features

- 🎵 Play music from YouTube by song name or direct URL
- ⏸️ Pause and resume playback
- ⏹️ Stop playback and disconnect from voice channel
- 🔍 Automatic search when providing song names
- 🎯 Simple `/` prefix commands
- 📋 Support for YouTube URLs and playlists

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/play <song>` | Play a song by name or URL | `/play Never Gonna Give You Up` |
| `/play <url>` | Play from YouTube URL | `/play https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| `/pause` | Pause the current song | `/pause` |
| `/resume` | Resume the paused song | `/resume` |
| `/stop` | Stop playing and disconnect | `/stop` |
| `/help_music` | Show all available commands | `/help_music` |

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- FFmpeg (required for audio processing)

#### Installing FFmpeg on Windows:
1. Download FFmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your system PATH environment variable
4. Restart your command prompt/terminal

### 2. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot"
5. Copy the bot token (you'll need this later)
6. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent (optional)

### 3. Bot Permissions

When inviting the bot to your server, make sure it has these permissions:
- Connect
- Speak
- Use Voice Activity
- Read Messages
- Send Messages
- Embed Links
- Use Slash Commands

**Invite URL Template:**
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=3148800&scope=bot
```
Replace `YOUR_BOT_CLIENT_ID` with your actual bot's client ID.

### 4. Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 5. Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
2. Edit `.env` and add your Discord bot token:
   ```
   DISCORD_BOT_TOKEN=your_actual_bot_token_here
   ```

### 6. Running the Bot

```bash
python bot.py
```

You should see:
```
YourBotName#1234 has connected to Discord!
Bot is ready to play music!
```

## Usage

1. Join a voice channel in your Discord server
2. Use `/play <song name>` to search and play a song
3. Use `/play <YouTube URL>` to play from a direct link
4. Use `/pause`, `/resume`, and `/stop` to control playback

## Example Usage

```
/play Rick Astley Never Gonna Give You Up
/play https://www.youtube.com/watch?v=dQw4w9WgXcQ
/pause
/resume
/stop
```

## Troubleshooting

### Common Issues

1. **"FFmpeg not found" error:**
   - Make sure FFmpeg is installed and added to your system PATH
   - Restart your terminal/command prompt after adding to PATH

2. **"Bot doesn't respond to commands:"**
   - Make sure the bot has proper permissions in your server
   - Check that Message Content Intent is enabled in the Discord Developer Portal

3. **"Can't join voice channel:"**
   - Make sure you're in a voice channel when using music commands
   - Check that the bot has Connect and Speak permissions

4. **"No audio playing:"**
   - Check your Discord voice settings
   - Make sure the bot has Speak permission
   - Try adjusting the volume in Discord

### Debug Mode

To enable more detailed logging, modify the bot.py file and change:
```python
'quiet': True,
```
to:
```python
'quiet': False,
```

## Dependencies

- `discord.py[voice]` - Discord API wrapper with voice support
- `yt-dlp` - YouTube video/audio downloader
- `PyNaCl` - Voice encryption for Discord
- `python-dotenv` - Environment variable management

## Important Notes

- This bot is for educational purposes and personal use
- Make sure to respect YouTube's Terms of Service
- The bot requires FFmpeg to be installed on the system
- Audio files are streamed directly and not stored locally
- The bot supports most YouTube content that yt-dlp can access

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Make sure all dependencies are installed correctly
3. Verify your Discord bot token and permissions
4. Check that FFmpeg is properly installed

## License

This project is open source and available under the MIT License.