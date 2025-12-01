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



# What is OnalBot?

OnalBot is a cozy little Discord music companion built with discord.py and Wavelink. It speaks Spotify, Apple Music, and YouTube, keeps a warm SQLite cache of your favorite searches, and sprinkles in welcome images so new members feel noticed the second they drop in.

## Highlights

- Smooth Lavalink playback with queue controls, progress embeds, and interactive buttons.
- Apple Music and Spotify lookups that fall back to YouTube when needed (and cache the result for next time).
- Admin-friendly tools: `!reset`, cache management, and strict guild allow-listing.
- Optional welcome cards with rounded avatars and custom fonts for that premium first impression.

## What you need

- A Discord bot token with the proper intents enabled.
- A running Lavalink node (local or remote) you can point the bot toward.
- Optional Spotify credentials if you want ultra-reliable track matching.
- An `arial.ttf` (or any font file) if you plan to enable the welcome artwork.

## Self-host in a few minutes

1. **Grab the code & deps**

  ```pwsh
  git clone https://github.com/Kimsec/OnalBot.git
  cd OnalBot
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

2. **Create `.env`** – copy `.env.example` and fill in your details:

  ```env
  DISCORD_TOKEN=your-token
  LAVALINK_URI=http://localhost:2333
  LAVALINK_PASSWORD=supersecret
  ALLOWED_GUILD_IDS=123456789012345678
  SPOTIFY_CLIENT_ID=
  SPOTIFY_CLIENT_SECRET=
  ```

3. **Point to Lavalink** – make sure your Lavalink server is up and the URI/password match.

4. **Run the bot**

  ```pwsh
  python OnalBot.py
  ```

## Hosting tips

- Running on Linux? Drop it into a `systemd` service and enable auto-restart so `!reset` + service restarts keep everything tidy.
- Want headless Lavalink + bot on the same box? Use a reverse proxy or firewall rules so only you can reach Lavalink’s port.
- Keep `.env` outside version control and rotate secrets whenever you rotate Discord/Lavalink credentials.

## Commands at a glance

- `!play` / `!p` — play a track, Apple Music link, Spotify URL, or plain search.
- `!queue`, `!remove`, `!prioritize`, `!shuffle` — manage what’s coming up next.
- `!clearqueue`, `!stop`, `!reset` — clean slate when you need it.
- `!showcache`, `!clearcache`, `!healthcheck` — keep an eye on the bot’s internals.
- `!info`, `!music` — share a command overview with your server.

Sit back, drop a `!p miley cyrus flowers`, and let OnalBot set the vibe. 🌸
