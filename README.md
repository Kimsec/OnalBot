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

Self-hosted Discord music bot built with discord.py + Wavelink. Streams from YouTube, resolves Spotify/Apple links, caches lookups locally, and can greet newcomers with custom cards.

## Highlights

- Lavalink playback, queue embeds, and button controls.
- Apple Music/Spotify support with SQLite caching.
- Admin tools: `!reset`, cache ops, guild allow-list.
- Optional welcome artwork with custom fonts.

## What you need

- Discord bot token with intents enabled.
- Lavalink node you control.
- Optional Spotify credentials for tighter matching.
- Font file (default `arial.ttf`) for welcome cards.

## Self-host in minutes

1. Clone + install:

   ```pwsh
   git clone https://github.com/Kimsec/OnalBot.git
   cd OnalBot
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` → `.env` and set Discord token, Lavalink URI/password, allowed guild IDs, and optional Spotify keys.

3. Start Lavalink, then run:

   ```pwsh
   python OnalBot.py
   ```

## Hosting tips

- Use `systemd` on Linux for auto-restarts (`!reset` can hook into it).
- Lock down Lavalink ports with firewall rules or a proxy.
- Keep `.env` secrets private and rotate them regularly.

## Commands at a glance

- `!play` / `!p` — play a track, Apple Music link, Spotify URL, or plain search.
- `!queue`, `!remove`, `!prioritize`, `!shuffle` — manage what’s coming up next.
- `!clearqueue`, `!stop`, `!reset` — clean slate when you need it.
- `!showcache`, `!clearcache`, `!healthcheck` — keep an eye on the bot’s internals.
- `!info`, `!music` — share a command overview with your server.

Sit back, drop a `!p miley cyrus flowers`, and let OnalBot set the vibe. 🌸
