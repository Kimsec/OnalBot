<p align="center" width="10%">
    <img width="20%" src="logo.png" alt="OnalBot logo">
</p>

# <p align="center">OnalBot</p>

<br><p align="center" width="100%">
<a href="https://www.buymeacoffee.com/kimsec">
  <img src="https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=%E2%98%95&slug=kimsec&button_colour=FFDD00&font_colour=000000&font_family=Inter&outline_colour=000000&coffee_colour=ffffff" alt="Buy Me A Coffee"></a></p>

<p align="center">
    <a href="https://github.com/Kimsec/OnalBot">
    <img src="https://img.shields.io/badge/Platform-Self%20Hosted-success" alt="Self Hosted"></a>
    <a href="https://github.com/Kimsec/OnalBot?tab=readme-ov-file#quick-setup">
    <img src="https://img.shields.io/badge/Download-OnalBot-blue" alt="Download Badge"></a>
</p>

## What Is OnalBot?

OnalBot is a self-hosted Discord music bot built with `discord.py`, `Pomice`, and `Lavalink`.
Simple to run and easy to use — drop in a search term, YouTube URL, Spotify link, or Apple Music track and it plays. Lookups are cached locally to keep things snappy.

## Highlights

- `Pomice + Lavalink` playback
- Queue system with now-playing embeds and button controls
- Spotify track and playlist resolving
- Apple Music track link support
- Local SQLite cache for Spotify and YouTube lookups
- Admin commands: `!reset`, `!healthcheck`, `!showcache`, `!clearcache`
- Optional welcome-card image generation

## Core Commands

- `!play` / `!p` — play or queue a track
- `!queue`, `!remove`, `!prioritize`, `!shuffle`, `!clearqueue` — manage the queue
- `!reset`, `!healthcheck`, `!showcache`, `!clearcache` — maintenance and status
- Player buttons for pause/resume, skip, stop, and queue management

## Quick Setup

1. Clone the repo and install dependencies:
```bash
git clone https://github.com/Kimsec/OnalBot.git
cd OnalBot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your values:
```env
DISCORD_TOKEN=your-bot-token
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret
LAVALINK_URI=http://127.0.0.1:2333
LAVALINK_PASSWORD=your-password
ALLOWED_GUILD_IDS=214461949574905857,1064940616208883792
WELCOME_GUILD_ID=214461949574905857
PAUSE_DISCONNECT_TIMEOUT=2400
FONT_PATH=./arial.ttf
```

3. Start your Lavalink server and make sure the URI and password match.

4. Start the bot:
```bash
python OnalBot.py
```

## Notes

- Leave `ALLOWED_GUILD_IDS` empty to allow the bot in any server.
- Spotify credentials are only needed for Spotify URL resolving.
- Apple Music support is limited to track links.
- `WELCOME_GUILD_ID` is optional — only used for the welcome-card feature.
- Cached lookups are stored in `music_cache.db`.
