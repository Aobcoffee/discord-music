# Discord Music Bot

A sophisticated Discord music bot that supports YouTube and Spotify (including private playlists via OAuth), built with a modular architecture for production deployment.

## Features

### YouTube Support
- Play music from YouTube by song name or direct URL
- Automatic search when providing song names  
- Support for YouTube URLs and playlists
- Optimized streaming for minimal delay

### Spotify Integration
- **Public Content**: Full support for public tracks, playlists, and albums
- **Albums**: Complete album support with all tracks
- **Radio Playlists**: Support for Spotify radio and generated playlists
- **Instant Playback**: Optimized loading for immediate playback
- **No Authentication Required**: Works with all public Spotify content

## Commands

### Basic Music Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/play <song/URL>` | Play music from YouTube or Spotify | `/play bohemian rhapsody` |
| `/skip` | Skip current track | `/skip` |
| `/pause` | Pause playback | `/pause` |
| `/resume` | Resume playback | `/resume` |
| `/stop` | Stop and disconnect | `/stop` |
| `/queue` | Show current queue | `/queue` |
| `/clear` | Clear queue | `/clear` |
| `/help_music` | Show all commands and features | `/help_music` |

## Setup Instructions

### 1. Prerequisites

- **Python 3.8+** (recommended: Python 3.10+)
- **FFmpeg** (for audio processing)
- **Discord Bot Token**
- **Spotify App Credentials** (optional, for Spotify integration)

### 2. Installation

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### Install FFmpeg

**Windows:**
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your system PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 3. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot"
5. Copy the bot token
6. Enable "Message Content Intent"

**Bot Permissions:** `3148800`
- Send Messages
- Connect (voice)  
- Speak (voice)
- Use Voice Activity
- Read Message History

**Invite URL Template:**
```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=3148800&scope=bot
```

### 4. Spotify Integration Setup (Optional)

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create an App"
3. Copy Client ID and Client Secret
4. Add redirect URI: `http://localhost:8080/callback`

### 5. Configuration

Copy `.env.example` to `.env` and configure:

```env
# Discord Bot Token (Required)
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Spotify API Credentials (Optional)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# Bot Configuration (Optional)
DISCORD_COMMAND_PREFIX=/
OAUTH_CALLBACK_HOST=localhost
OAUTH_CALLBACK_PORT=8080
```

### 6. Running the Bot

**Development Mode:**
```bash
python main.py
```

**Production Deployment** (see README section for detailed instructions):
- systemd service (Linux)
- Docker container
- Process manager (PM2)

## Usage Examples

### Basic Playback
```
/play never gonna give you up
/play https://www.youtube.com/watch?v=dQw4w9WgXcQ
/pause
/resume
/stop
```

### Spotify Integration (No Authentication Required!)
```
# Individual track
/play https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh

# Public playlist
/play https://open.spotify.com/playlist/37i9dQZF1DX0XUsuxWHRQd

# Albums (NEW!)
/play https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy

# Radio playlists (NEW!)  
/play https://open.spotify.com/station/playlist/37i9dQZF1E8UXBoz02kGID
```

### Queue Management
```
/queue
/skip
/clear
```

## Architecture

### File Structure
```
discord-music-bot/
├── bot.py              # Main bot file with commands
├── config.py           # Configuration management  
├── music_player.py     # Music queue and playback
├── audio_source.py     # Audio source management
├── oauth_server.py     # OAuth callback server
├── requirements.txt    # Python dependencies
├── .env.example       # Environment template
└── README.md          # Documentation
```

### Key Components
- **MusicManager**: Manages players per Discord server
- **MusicPlayer**: Handles playback and voice connections
- **MusicQueue**: Advanced track queue with management features
- **SpotifyHandler**: OAuth and API integration for Spotify
- **AudioSource**: YouTube-DL wrapper for audio processing
- **OAuthServer**: Handles Spotify authentication callbacks

## � Free Cloud Deployment

### 🎯 Quick Deploy Options

Your bot is now ready for **FREE** deployment! All necessary files are included:

| Provider | Free Tier | FFmpeg Support | Difficulty |
|----------|-----------|----------------|------------|
| **Heroku** | 550 hours/month | ✅ Auto-included | ⭐ Easy |
| **Railway** | $5/month (trial credit) | ✅ Auto-included | ⭐⭐ Medium |
| **Render** | 750 hours/month | ✅ Manual setup | ⭐⭐⭐ Hard |

---

### 🏆 **Option 1: Heroku (Recommended)**

**✅ Pros:** Easiest setup, automatic FFmpeg, great documentation  
**❌ Cons:** Sleeps after 30min inactivity on free tier

#### Quick Deploy Steps:

1. **Install Heroku CLI**: [Download here](https://devcenter.heroku.com/articles/heroku-cli)

2. **Login and create app**:
   ```bash
   heroku login
   heroku create your-discord-bot-name
   ```

3. **Add FFmpeg buildpack** (automatic with app.json):
   ```bash
   heroku buildpacks:add https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
   heroku buildpacks:add heroku/python
   ```

4. **Set environment variables**:
   ```bash
   heroku config:set DISCORD_BOT_TOKEN=your_discord_token_here
   heroku config:set SPOTIFY_CLIENT_ID=your_spotify_id_here
   heroku config:set SPOTIFY_CLIENT_SECRET=your_spotify_secret_here
   ```

5. **Deploy**:
   ```bash
   git add .
   git commit -m "Deploy Discord music bot"
   git push heroku main
   ```

6. **Start worker**:
   ```bash
   heroku ps:scale worker=1
   ```

**🎉 Your bot is now live 24/7!**

---

### ⚡ **Option 2: Railway**

**✅ Pros:** Modern interface, easy deployment, good performance  
**❌ Cons:** $5/month after trial credits

#### Deploy Steps:

1. **Install Railway CLI**: 
   ```bash
   npm install -g @railway/cli
   ```

2. **Login and deploy**:
   ```bash
   railway login
   railway new
   railway add
   ```

3. **Set environment variables** in Railway dashboard or CLI:
   ```bash
   railway variables:set DISCORD_BOT_TOKEN=your_token
   railway variables:set SPOTIFY_CLIENT_ID=your_spotify_id
   railway variables:set SPOTIFY_CLIENT_SECRET=your_spotify_secret
   ```

4. **Deploy**:
   ```bash
   railway up
   ```

---

### 📋 **Environment Variables Setup**

For **ALL** deployment platforms, you need these environment variables:

| Variable | Required | Where to get it |
|----------|----------|-----------------|
| `DISCORD_BOT_TOKEN` | ✅ **Required** | [Discord Developer Portal](https://discord.com/developers/applications) |
| `SPOTIFY_CLIENT_ID` | Optional | [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) |
| `SPOTIFY_CLIENT_SECRET` | Optional | [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) |

### 🤖 **Discord Bot Setup Reminder**

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create new application → Bot section → Create Bot
3. **IMPORTANT**: Enable "Message Content Intent" under Privileged Gateway Intents
4. Copy bot token for `DISCORD_BOT_TOKEN`
5. Use this invite URL (replace YOUR_CLIENT_ID):
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=3148800&scope=bot
   ```

### ✅ **Deployment Files Included**

Your project now includes all necessary deployment files:

- **`Procfile`** - Heroku process definition
- **`runtime.txt`** - Python version specification  
- **`app.json`** - Heroku app configuration with FFmpeg buildpack
- **`railway.toml`** - Railway deployment configuration
- **`requirements.txt`** - All Python dependencies

### 🎵 **Testing Your Deployed Bot**

Once deployed, test these commands in Discord:

```
/play never gonna give you up
/queue
/skip
/help_music
```

### 🆘 **Troubleshooting**

**Bot not responding?**
- ✅ Check Message Content Intent is enabled
- ✅ Verify bot token is correct
- ✅ Ensure bot has permissions in your Discord server

**Music not playing?**
- ✅ FFmpeg buildpack added for Heroku
- ✅ `NIXPACKS_APT_PACKAGES = "ffmpeg"` in railway.toml
- ✅ Bot has voice channel permissions

**Spotify not working?**
- ✅ YouTube will still work without Spotify credentials
- ✅ Add Spotify credentials for full functionality

---

## �🔧 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | - | Discord bot token |
| `SPOTIFY_CLIENT_ID` | No | - | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | No | - | Spotify app client secret |
| `DISCORD_COMMAND_PREFIX` | No | `/` | Bot command prefix |
| `OAUTH_CALLBACK_HOST` | No | `localhost` | OAuth callback host |
| `OAUTH_CALLBACK_PORT` | No | `8080` | OAuth callback port |

## License

This project is open source and available under the MIT License.