<p align="center" width="10%">
    <img width="20%" src="logo.png"></a>
</p>

# <p align="center">OnalBot</p>

<br><p align="center" width="100%">
<a href="https://www.buymeacoffee.com/kimsec">
  <img src="https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&amp;emoji=%E2%98%95&amp;slug=kimsec&amp;button_colour=FFDD00&amp;font_colour=000000&amp;font_family=Inter&amp;outline_colour=000000&amp;coffee_colour=ffffff" alt="Buy Me A Coffee"></a></p>
<p align="center">
    <a href="https://github.com/Kimsec/OnalBot">
    <img src="https://img.shields.io/badge/Platform-Self%20Hosted-success" alt="Self Hosted"></a>
    <a href="https://github.com/kimsec/OnalBot/releases/latest">
    <img src="https://img.shields.io/badge/Download-OnalBot-blue" alt="Download Badge" style="margin-right: 10px;"></a>
    <a href="https://github.com/Kimsec/OnalBot/releases">
    <img src="https://img.shields.io/github/v/release/kimsec/OnalBot" alt="Release Badge" style="margin-right: 0px;"></a>
</p>



# Description

A Discord music bot using discord.py and Wavelink (Lavalink), with optional Spotify lookup and a simple SQLite cache.

## Setup

1. Python 3.10+ recommended. Install dependencies:

```pwsh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Create a `.env` file based on `.env.example` and fill in your values:

```
DISCORD_TOKEN=your-bot-token
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret
LAVALINK_URI=http://192.168.1.20:2333
LAVALINK_PASSWORD=your-password
ALLOWED_GUILD_IDS=214461949574905857,1064940616208883792
FONT_PATH=./arial.ttf
```

- Spotify is optional; leave SPOTIFY_* empty to disable.
- FONT_PATH defaults to `./arial.ttf`.

3. Run Lavalink and ensure the URI/password match your `.env`.

4. Run the bot:

```pwsh
python OnalBot.py
```

## Auto Reconnect

- Bot will automatically reconnect to lavalink if lavalink is disconnected

## Notes

- The bot restricts usage to guilds in `ALLOWED_GUILD_IDS`.
- Caches Spotify and Apple Music -> YouTube searches and YouTube direct links in `music_cache.db`.
- Commands: see `!info`.
