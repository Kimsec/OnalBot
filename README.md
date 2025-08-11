# OnalBot

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

## Publishing to GitHub

- Ensure `.env` and `music_cache.db` are ignored by `.gitignore`.
- Initialize git and push to a new GitHub repo:

```pwsh
git init
git add .
# Optional: ensure the .env file is NOT added
git reset .env
git commit -m "Initial commit: OnalBot with env-based config"
# Create a repo on GitHub first, then add the remote:
# git remote add origin https://github.com/<user>/<repo>.git
# git branch -M main
# git push -u origin main
```

## Notes

- The bot restricts usage to guilds in `ALLOWED_GUILD_IDS`.
- Caches Spotify->YouTube searches and YouTube direct links in `music_cache.db`.
- Commands: see `!info`.
