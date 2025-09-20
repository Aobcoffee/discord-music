# Discord Music Bot

A sophisticated Discord music bot that supports YouTube and Spotify (including private playlists via OAuth), built with a modular architecture for production deployment.

## Features

### YouTube Support
- Play music from YouTube by song name or direct URL
- Automatic search when providing song names  
- Support for YouTube URLs and playlists
- Optimized streaming for minimal delay

### Spotify Integration
- **Public Playlists**: Direct support without authentication
- **Private Playlists**: OAuth authentication for personal content
- **Track Support**: Individual Spotify tracks
- **Instant Playback**: Optimized loading for immediate playback

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

### Spotify Authentication

| Command | Description | Example |
|---------|-------------|---------|
| `/spotify_auth` | Get Spotify authentication link | `/spotify_auth` |
| `/my_playlists` | Show your Spotify playlists (requires auth) | `/my_playlists` |

### Help

| Command | Description |
|---------|-------------|
| `/help_music` | Show all commands and features |

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

### Spotify Integration
```
# Public playlist (no auth needed)
/play https://open.spotify.com/playlist/37i9dQZF1DX0XUsuxWHRQd

# For private playlists:
/spotify_auth
# Click the provided link to authenticate
/my_playlists
/play https://open.spotify.com/playlist/your_private_playlist_id
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
├── spotify_auth.py     # Spotify OAuth handler
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

## 🔧 Environment Variables

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