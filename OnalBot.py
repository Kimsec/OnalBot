import discord
from discord.ext import commands
from discord.ext.commands import CommandNotFound, CheckFailure
import pomice
import asyncio
import time
import math
import os
from io import BytesIO
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont
import requests
import aiosqlite
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Secrets and configuration from environment variables
DISCORD_TOKEN           = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID       = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET   = os.getenv("SPOTIFY_CLIENT_SECRET")
LAVALINK_URI            = os.getenv("LAVALINK_URI")
LAVALINK_PASSWORD       = os.getenv("LAVALINK_PASSWORD")
LAVALINK_RESUME_KEY     = os.getenv("LAVALINK_RESUME_KEY", "onalbot-session")
LAVALINK_RESUME_TIMEOUT = int(os.getenv("LAVALINK_RESUME_TIMEOUT", "120"))  # sekunder
FONT_PATH               = os.getenv("FONT_PATH", os.path.join(BASE_DIR, "arial.ttf"))
ALLOWED_GUILD_IDS_ENV   = os.getenv("ALLOWED_GUILD_IDS")
APPLE_MUSIC_COUNTRY     = os.getenv("APPLE_MUSIC_COUNTRY", "NO")  # Default landkode for Apple Music lookup
WELCOME_GUILD_ID        = int(os.getenv("WELCOME_GUILD_ID", "0"))  # Kun denne serveren får welcome-bilde (0 = deaktivert)
PAUSE_DISCONNECT_TIMEOUT = int(os.getenv("PAUSE_DISCONNECT_TIMEOUT", "3600"))  # sekunder pauset før auto-stop
VOICE_CONNECT_TIMEOUT    = float(os.getenv("VOICE_CONNECT_TIMEOUT", "30"))  # sekunder før voice connect timeout
DEFAULT_VOLUME           = int(os.getenv("DEFAULT_VOLUME", "100"))  # 0-1000 (Lavalink), 100 er normalt
ALLOWED_GUILD_IDS       = []
if ALLOWED_GUILD_IDS_ENV:
    for part in ALLOWED_GUILD_IDS_ENV.split(','):
        part = part.strip()
        if part.isdigit():
            ALLOWED_GUILD_IDS.append(int(part))

sp = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        ))
    except Exception as e:
        print(f"Spotify init error: {e}")
DB_PATH = os.path.join(BASE_DIR, "music_cache.db")
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
LAVALINK_NODE_ID = "onalbot"
POMICE_NO_NODES = getattr(pomice.exceptions, "NoNodesAvailable", Exception)
POMICE_NODE_EXCEPTION = getattr(pomice.exceptions, "NodeException", Exception)
POMICE_TRACK_LOAD_ERROR = getattr(pomice.exceptions, "TrackLoadError", Exception)


def _parse_lavalink_uri(uri: str) -> tuple[str, int, bool]:
    if not uri:
        raise ValueError("LAVALINK_URI mangler.")

    parsed = urlparse(uri if "://" in uri else f"http://{uri}")
    host = parsed.hostname
    if not host:
        raise ValueError("LAVALINK_URI mangler gyldig host.")

    secure = parsed.scheme == "https"
    port = parsed.port or (443 if secure else 2333)
    return host, port, secure


def get_lavalink_node():
    return pomice.NodePool.get_node(identifier=LAVALINK_NODE_ID)


def resolve_player(guild: discord.Guild | None):
    if guild is None:
        return None

    vc = getattr(guild, "voice_client", None)
    if isinstance(vc, pomice.Player) and not getattr(vc, "is_dead", False):
        return vc

    try:
        node = get_lavalink_node()
    except POMICE_NO_NODES:
        return None
    except Exception:
        return None

    player = node.get_player(guild.id)
    if player and not getattr(player, "is_dead", False):
        return player
    return None


async def fetch_tracks(query: str, *, ctx=None):
    node = get_lavalink_node()
    is_url = bool(urlparse(query).scheme)
    has_search_prefix = query.startswith(("ytsearch:", "ytmsearch:", "scsearch:", "spsearch:", "sprec:", "amsearch:"))
    if not is_url and not has_search_prefix:
        query = f"ytsearch:{query}"
    return await node.get_tracks(query=query, ctx=ctx, search_type=None)


async def connect_lavalink() -> bool:
    if not LAVALINK_URI or not LAVALINK_PASSWORD:
        print("[Lavalink] Mangler URI eller PASS i miljøvariabler.")
        return False
    try:
        try:
            await pomice.NodePool.disconnect()
        except Exception:
            pass

        host, port, secure = _parse_lavalink_uri(LAVALINK_URI)
        node = await pomice.NodePool.create_node(
            bot=bot,
            host=host,
            port=port,
            password=LAVALINK_PASSWORD,
            identifier=LAVALINK_NODE_ID,
            secure=secure,
            resume_key=LAVALINK_RESUME_KEY,
            resume_timeout=LAVALINK_RESUME_TIMEOUT,
        )
        if not node.is_connected:
            raise RuntimeError("Node connected flag was false.")
        print("[Lavalink] Tilkoblet.")
        return True
    except Exception as e:
        print(f"[Lavalink] Kunne ikke koble til: {e}")
        return False


async def ensure_lavalink_ready() -> bool:
    try:
        node = get_lavalink_node()
        if node and node.is_connected:
            return True
    except POMICE_NO_NODES:
        pass
    except Exception:
        pass
    return await connect_lavalink()


@bot.check
async def globally_block_servers(ctx):
    if not ALLOWED_GUILD_IDS:
        return True
    if ctx.guild and ctx.guild.id in ALLOWED_GUILD_IDS:
        return True
    raise commands.CheckFailure(":x: **The bot is not allowed on this server.**")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CheckFailure):
        await ctx.send(str(error), delete_after=10)

    elif isinstance(error, CommandNotFound):
        await ctx.send(":x: Ugyldig kommando.", delete_after=8)

    elif isinstance(error, commands.CommandInvokeError):
        original = getattr(error, "original", error)

        if isinstance(original, asyncio.TimeoutError):
            await ctx.send(
                ":x: Klarte ikke å koble til voice-kanalen (timeout). Sjekk at botten har **Connect** + **Speak** og prøv igjen.",
                delete_after=10,
            )
            return

        if isinstance(original, POMICE_NO_NODES):
            await ctx.send(":x: Lavalink/Pomice-node er ikke tilgjengelig akkurat nå. Prøv !reset.", delete_after=8)
            return

        if isinstance(original, (POMICE_NODE_EXCEPTION, POMICE_TRACK_LOAD_ERROR)):
            await ctx.send(f":x: Musikkfeil: `{original}`", delete_after=8)
            return

        if isinstance(original, discord.Forbidden):
            await ctx.send(":x: Mangler Discord-permisjoner for denne handlingen.", delete_after=8)
            return

        print(f"CommandInvokeError i {getattr(ctx.command, 'qualified_name', 'ukjent kommando')}: {repr(original)}")
        await ctx.send(f":x: Uventet feil i kommandoen: `{original}`", delete_after=10)
        return

    else:
        print(f"Uventet feil: {error}")

async def init_cache_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS spotify_cache (
            spotify_id TEXT PRIMARY KEY,
            yt_query TEXT NOT NULL
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS youtube_cache (
            yt_query TEXT PRIMARY KEY,
            yt_title TEXT,
            yt_url TEXT
        );
        """)
        await db.commit()

async def get_spotify_cache(spotify_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT yt_query FROM spotify_cache WHERE spotify_id = ?", (spotify_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def set_spotify_cache(spotify_id, yt_query):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO spotify_cache (spotify_id, yt_query) VALUES (?, ?)", (spotify_id, yt_query))
        await db.commit()

async def get_youtube_cache(query):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT yt_title, yt_url FROM youtube_cache WHERE yt_query = ?", (query,)) as cursor:
            row = await cursor.fetchone()
            return row if row else None

async def set_youtube_cache(query, yt_title, yt_url):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO youtube_cache (yt_query, yt_title, yt_url) VALUES (?, ?, ?)", (query, yt_title, yt_url))
        await db.commit()


# Apple Music helper (bruker iTunes public lookup API)
# Gjenbruker spotify_cache ved å lagre nøkkel 'apple:<id>' -> ytsearch...

async def fetch_apple_track(track_id: str, country: str) -> tuple | None:
    """Returner (title, artist) for Apple Music track id eller None hvis ikke funnet."""
    url = f"https://itunes.apple.com/lookup?id={track_id}&country={country}"
    try:
        data = await asyncio.to_thread(lambda: requests.get(url, timeout=8).json())
        if not data or data.get("resultCount", 0) == 0:
            return None
        res = data["results"][0]
        title = res.get("trackName") or res.get("collectionName")
        artist = res.get("artistName") or ""
        if not title:
            return None
        return title, artist
    except Exception as e:
        print(f"[AppleMusic] Lookup-feil: {e}")
        return None

# Guild state (multi-server support)
# Hver server får sin egen kø slik at flere kan spille samtidig uten å påvirke hverandre.
music_queues = {}          # guild.id -> list[pomice.Track]
embed_messages = {}        # guild.id -> discord.Message (now playing)
track_data = {}            # guild.id -> (track, ctx)
update_tasks = {}          # guild.id -> asyncio.Task (progress updater)
pause_start_times = {}     # guild.id -> pause start timestamp


def is_playing(vc):
    return bool(vc and getattr(vc, "is_playing", False) and getattr(vc, "current", None) is not None)


def get_guild_queue(guild_id: int):
    # Returner (og opprett ved behov) kø for en guild.
    return music_queues.setdefault(guild_id, [])


async def _auto_delete_message(msg: discord.Message, delay: float):
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except asyncio.CancelledError:
        pass
    except (discord.Forbidden, discord.NotFound):
        pass


async def stop_and_clear(ctx, *, notify=None, disconnect=True, delete_after=15):
    guild_id = ctx.guild.id
    vc = resolve_player(ctx.guild)
    if vc:
        try:
            await vc.stop()
        except Exception:
            pass
        if disconnect:
            try:
                await vc.destroy()
            except Exception:
                pass

    if disconnect and ctx.guild.voice_client:
        try:
            await ctx.guild.voice_client.disconnect()
        except Exception:
            pass

    get_guild_queue(guild_id).clear()
    pause_start_times.pop(guild_id, None)
    track_data.pop(guild_id, None)
    await bot.change_presence(activity=None)

    embed_msg = embed_messages.pop(guild_id, None)
    if embed_msg:
        try:
            await embed_msg.delete()
        except discord.NotFound:
            pass

    current_task = asyncio.current_task()
    task = update_tasks.pop(guild_id, None)
    if task and task is not current_task:
        task.cancel()

    if notify:
        message = await ctx.send(notify)
        if delete_after:
            asyncio.create_task(_auto_delete_message(message, delete_after))


def _queue_page_count(total_items: int, page_size: int) -> int:
    return max(1, math.ceil(total_items / page_size))


def _queue_remove_embed(page: int, total_pages: int) -> discord.Embed:
    embed = discord.Embed(
        title="Klikk for å fjerne en sang fra køen",
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Side {page}/{total_pages}")
    return embed


def _queue_button_label(position: int, title: str, *, max_length: int = 80) -> str:
    prefix = f"{position}. "
    available = max_length - len(prefix)
    if available <= 0:
        return prefix[:max_length]
    if len(title) <= available:
        return f"{prefix}{title}"
    if available <= 3:
        return f"{prefix}{title[:available]}"
    return f"{prefix}{title[:available - 3]}..."


class QueueView(discord.ui.View):
    def __init__(self, ctx, *, page: int = 0, page_size: int = 20):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.page_size = page_size
        guild_queue = get_guild_queue(ctx.guild.id)
        total_items = len(guild_queue)
        total_pages = _queue_page_count(total_items, page_size)
        self.page = min(max(page, 0), total_pages - 1)

        start = self.page * page_size
        page_tracks = guild_queue[start:start + page_size]

        for local_index, track in enumerate(page_tracks):
            global_index = start + local_index
            self.add_item(
                RemoveButton(
                    label=_queue_button_label(global_index + 1, track.title),
                    index=global_index,
                    track=track,
                    ctx=ctx,
                    page=self.page,
                    page_size=page_size,
                    row=local_index // 5,
                )
            )

        self.add_item(
            QueuePageButton(
                label="⬅️ Forrige",
                ctx=ctx,
                target_page=self.page - 1,
                page_size=page_size,
                disabled=self.page == 0,
            )
        )
        self.add_item(QueuePageIndicator(page=self.page + 1, total_pages=total_pages))
        self.add_item(
            QueuePageButton(
                label="Neste ➡️",
                ctx=ctx,
                target_page=self.page + 1,
                page_size=page_size,
                disabled=self.page >= total_pages - 1,
            )
        )
        self.add_item(QueueCloseButton(ctx=ctx))


class RemoveButton(discord.ui.Button):
    def __init__(self, label, index, track, ctx, page, page_size, row):
        super().__init__(label=label, style=discord.ButtonStyle.red, row=row)
        self.index = index
        self.track = track
        self.ctx = ctx
        self.page = page
        self.page_size = page_size

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(":x: Bare personen som ba om listen kan endre den.", ephemeral=True)
            return

        try:
            guild_queue = get_guild_queue(self.ctx.guild.id)
            if 0 <= self.index < len(guild_queue) and guild_queue[self.index] is self.track:
                removed = guild_queue.pop(self.index)
            else:
                current_index = guild_queue.index(self.track)
                removed = guild_queue.pop(current_index)

            if guild_queue:
                total_pages = _queue_page_count(len(guild_queue), self.page_size)
                next_page = min(self.page, total_pages - 1)
                await interaction.response.edit_message(
                    content=f"✅ Fjernet: **{removed.title}**",
                    embed=_queue_remove_embed(next_page + 1, total_pages),
                    view=QueueView(self.ctx, page=next_page, page_size=self.page_size)
                )
            else:
                await interaction.response.edit_message(
                    content=f"✅ Fjernet: **{removed.title}**\nKøen er nå tom.",
                    embed=None,
                    view=None
                )

            if interaction.channel:
                await interaction.channel.send(f"❌ {interaction.user.mention} fjernet: **{removed.title}**", delete_after=5)

        except (IndexError, ValueError):
            await interaction.response.send_message(":x: Listen kan ha blitt endret. Prøv på nytt.", ephemeral=True)


class QueuePageButton(discord.ui.Button):
    def __init__(self, label, ctx, target_page, page_size, disabled):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=4, disabled=disabled)
        self.ctx = ctx
        self.target_page = target_page
        self.page_size = page_size

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(":x: Bare personen som ba om listen kan endre den.", ephemeral=True)
            return

        guild_queue = get_guild_queue(self.ctx.guild.id)
        if not guild_queue:
            await interaction.response.edit_message(content="🎵 Køen er tom.", embed=None, view=None)
            return

        total_pages = _queue_page_count(len(guild_queue), self.page_size)
        target_page = min(max(self.target_page, 0), total_pages - 1)
        await interaction.response.edit_message(
            content=None,
            embed=_queue_remove_embed(target_page + 1, total_pages),
            view=QueueView(self.ctx, page=target_page, page_size=self.page_size)
        )


class QueuePageIndicator(discord.ui.Button):
    def __init__(self, page, total_pages):
        super().__init__(
            label=f"Side {page}/{total_pages}",
            style=discord.ButtonStyle.secondary,
            row=4,
            disabled=True,
        )


class QueueCloseButton(discord.ui.Button):
    def __init__(self, ctx):
        super().__init__(label="Lukk", style=discord.ButtonStyle.secondary, row=4)
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(":x: Bare personen som ba om listen kan endre den.", ephemeral=True)
            return

        await interaction.response.edit_message(content="Fjerningslisten ble lukket.", embed=None, view=None)


class SongView(discord.ui.View):
    def __init__(self, song, ctx):
        super().__init__(timeout=None)
        self.song = song
        self.ctx = ctx

    @discord.ui.button(emoji='\u23EF')
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        vc = resolve_player(interaction.guild)
        guild_id = interaction.guild.id
        if not vc:
            await self.ctx.send(":x: Ingen aktiv spiller funnet.", delete_after=4)
            return
        vc.ctx = self.ctx
        if getattr(vc, "is_paused", False):
            await vc.set_pause(False)
            pause_start_times.pop(guild_id, None)
            await self.ctx.send("**Player resumed**", delete_after=2)
        else:
            await vc.set_pause(True)
            pause_start_times[guild_id] = time.time()
            await self.ctx.send("**Player paused**", delete_after=2)

    @discord.ui.button(emoji='\u23F9')
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await stop_and_clear(self.ctx)

    @discord.ui.button(emoji='\u23ED')
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        vc = resolve_player(interaction.guild)
        if not vc or not is_playing(vc):
            return await self.ctx.send(":x: **No music is playing at the moment.**", delete_after=5)
        vc.ctx = self.ctx
        if vc.guild.id in update_tasks:
            update_tasks[vc.guild.id].cancel()
            update_tasks.pop(vc.guild.id, None)
        await vc.stop()
        await play_next(self.ctx)

    @discord.ui.button(emoji='📜')
    async def queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        ctx = self.ctx

        guild_queue = get_guild_queue(ctx.guild.id)
        if not guild_queue:
            await ctx.send("\U0001F500 Køen er tom.", delete_after=3)
            return
        description = "\n".join([f"{idx + 1}. {track.title}" for idx, track in enumerate(guild_queue)])
        embed = discord.Embed(title="🎶 Musikk-kø", description=description, color=discord.Color.blue())
        await ctx.send(embed=embed, delete_after=10)

    @discord.ui.button(emoji='❌')
    async def remove_queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_queue = get_guild_queue(self.ctx.guild.id)
        if not guild_queue:
            await self.ctx.send("🎵 Køen er tom.", delete_after=3)
            return

        total_pages = _queue_page_count(len(guild_queue), 20)
        await interaction.response.send_message(
            embed=_queue_remove_embed(1, total_pages),
            view=QueueView(self.ctx, page=0, page_size=20),
            ephemeral=True,
        )


async def show_now_playing(song, ctx):
    guild_id = ctx.guild.id
    track_data[guild_id] = (song, ctx)
    pause_start_times.pop(guild_id, None)
    duration = song.length // 1000 if hasattr(song, 'length') else 0

    title = getattr(song, 'title', 'Ukjent sang')
    uri = getattr(song, 'uri', None)

    try:
        thumbnail = f"https://img.youtube.com/vi/{song.identifier}/hqdefault.jpg"
    except:
        thumbnail = None

    song_embed = discord.Embed(title=title, color=2303786)
    if uri:
        song_embed.url = uri
    if thumbnail:
        song_embed.set_thumbnail(url=thumbnail)

    song_embed.set_author(name="Now Playing", icon_url="https://cdn3.emoji.gg/emojis/3468-skype-music.gif")
    guild_queue = get_guild_queue(ctx.guild.id)
    requester = getattr(song, 'requester', ctx.author)
    song_embed.add_field(name="Requested by", value=requester.name, inline=True)
    song_embed.add_field(name="Songs in queue", value=f"{len(guild_queue)}", inline=True)

    progress_bar = generate_progress_bar(0, duration)
    song_embed.add_field(name="Progress", value=progress_bar, inline=False)

    view = SongView(song, ctx)

    try:
        await ctx.message.delete(delay=1)
    except:
        pass

    if guild_id in embed_messages:
        await embed_messages[guild_id].edit(embed=song_embed, view=view)
    else:
        embed_messages[guild_id] = await ctx.send(embed=song_embed, view=view)

    if guild_id in update_tasks:
        update_tasks[guild_id].cancel()

    embed_id = embed_messages[guild_id].id
    update_tasks[guild_id] = asyncio.create_task(update_progress_loop(guild_id, song, embed_id))
    await bot.change_presence(activity=discord.Game(name=f"🎵 {title}"))


def generate_progress_bar(current, total, length=22):
    if total == 0:
        return ""
    progress = int((current / total) * length)
    bar = "▬" * progress + "🔘" + "▬" * (length - progress - 1)
    current_min = math.floor(current / 60)
    current_sec = int(current % 60)
    total_min = math.floor(total / 60)
    total_sec = int(total % 60)
    return f"`[{bar}]` {current_min}:{current_sec:02d} / {total_min}:{total_sec:02d}"


async def update_progress_loop(guild_id, original_song, embed_id):
    while True:
        await asyncio.sleep(2)

        if guild_id not in track_data:
            break

        current_song, ctx = track_data[guild_id]
        if current_song != original_song:
            break

        embed_msg = embed_messages.get(guild_id)
        if not embed_msg or embed_msg.id != embed_id:
            break

        vc = resolve_player(ctx.guild)
        if not vc:
            break

        if getattr(vc, "is_paused", False):
            start = pause_start_times.setdefault(guild_id, time.time())
            if time.time() - start >= PAUSE_DISCONNECT_TIMEOUT:
                if PAUSE_DISCONNECT_TIMEOUT >= 60 and PAUSE_DISCONNECT_TIMEOUT % 60 == 0:
                    minutes = PAUSE_DISCONNECT_TIMEOUT // 60
                    unit = "minutt" if minutes == 1 else "minutter"
                    timeout_text = f"{minutes} {unit}"
                else:
                    timeout_text = f"{PAUSE_DISCONNECT_TIMEOUT} sekunder"
                await stop_and_clear(
                    ctx,
                    notify=f"⏹️ Spiller stoppet etter {timeout_text} pause.",
                )
                break
        else:
            pause_start_times.pop(guild_id, None)

        # Bruk posisjon direkte fra spilleren, håndterer pause og alt
        elapsed = int(vc.position / 1000) if vc.position else 0
        duration = current_song.length // 1000 if hasattr(current_song, 'length') else 0

        # Stopp når sangen er ferdig
        if duration > 0 and elapsed > duration:
            break

        # YouTube thumbnail hvis mulig
        thumbnail = f"https://img.youtube.com/vi/{current_song.identifier}/hqdefault.jpg" if hasattr(current_song, 'identifier') else None
        progress = generate_progress_bar(elapsed, duration)

        new_embed = discord.Embed(
            title=getattr(current_song, 'title', 'Ukjent sang'),
            url=getattr(current_song, 'uri', None),
            color=2303786
        )
        if thumbnail:
            new_embed.set_thumbnail(url=thumbnail)

        new_embed.set_author(name="Now Playing", icon_url="https://cdn3.emoji.gg/emojis/3468-skype-music.gif")
        guild_queue = get_guild_queue(ctx.guild.id)
        requester = getattr(current_song, 'requester', ctx.author)
        new_embed.add_field(name="Requested by", value=requester.name, inline=True)
        new_embed.add_field(name="Songs in queue", value=f"{len(guild_queue)}", inline=True)
        new_embed.add_field(name="Progress", value=progress, inline=False)
        await embed_msg.edit(embed=new_embed)


async def play_next(ctx):
    vc: pomice.Player | None = resolve_player(ctx.guild)
    guild_id = ctx.guild.id
    guild_queue = get_guild_queue(guild_id)
    track_data.pop(guild_id, None)

    if not vc:
        await stop_and_clear(ctx, notify=":x: Fant ikke aktiv spiller. Kobler i fra.")
        return

    if guild_queue:
        next_track = guild_queue.pop(0)
        vc.ctx = ctx
        await vc.play(next_track)
        try:
            await vc.set_volume(DEFAULT_VOLUME)
        except Exception:
            pass
        await show_now_playing(next_track, ctx)
    else:
        await stop_and_clear(ctx, notify="K\u00f8en er tom. Kobler i fra.")
        try:
            await ctx.message.delete(delay=1)
        except Exception:
            pass


@bot.command(aliases=['PLAY', 'p', 'P'])
async def play(ctx, *, query: str):
    # Sjekk Lavalink uten auto-retry.
    if not await ensure_lavalink_ready():
        await ctx.send(":x: Lavalink er ikke tilkoblet. Kjør !reset for å prøve å koble på nytt.", delete_after=7)
        try:
            await ctx.message.delete(delay=1)
        except Exception:
            pass
        return
    if not await ensure_voice(ctx):
        return
    vc: pomice.Player | None = resolve_player(ctx.guild)
    if not vc:
        await ctx.send(":x: Klarte ikke å opprette Pomice-player for voice-kanalen.", delete_after=6)
        try:
            await ctx.message.delete(delay=1)
        except Exception:
            pass
        return
    guild_queue = get_guild_queue(ctx.guild.id)
    if any(domain in query for domain in ("music.youtube.com/watch", "m.youtube.com/watch")):
        if "v=" in query:
            vid = query.split("v=")[1].split("&")[0]
            query = f"https://www.youtube.com/watch?v={vid}"
    # --- Apple Music enkeltspor ---
    if "music.apple.com" in query and "/song/" in query:
        try:
            # Ekstraher land og ID
            parts = query.split('/')
            # ID sist som er heltall
            track_id = next((p.split('?')[0] for p in reversed(parts) if p.split('?')[0].isdigit()), None)
            if not track_id:
                await ctx.send(":x: Fant ikke Apple Music ID i lenken.", delete_after=5)
                await ctx.message.delete(delay=1)
                return
            # Cache-nøkkel
            cache_key = f"apple:{track_id}"
            search = await get_spotify_cache(cache_key)  # gjenbruk tabell
            if not search:
                meta = await fetch_apple_track(track_id, APPLE_MUSIC_COUNTRY)
                if not meta:
                    await ctx.send(":x: Fant ikke Apple Music metadata.", delete_after=5)
                    await ctx.message.delete(delay=1)
                    return
                title, artist = meta
                search = f"ytsearch:{title} {artist}".strip()
                await set_spotify_cache(cache_key, search)
            track = None
            yt_cache = await get_youtube_cache(search)
            if yt_cache:
                cached_tracks = await fetch_tracks(yt_cache[1], ctx=ctx)
                if cached_tracks:
                    track = cached_tracks[0]
                else:
                    yt_cache = None
            if not yt_cache:
                fetched_tracks = await fetch_tracks(search, ctx=ctx)
                if not fetched_tracks:
                    await ctx.send(":x: Fant ikke YouTube-video.", delete_after=5)
                    await ctx.message.delete(delay=1)
                    return
                track = fetched_tracks[0]
                await set_youtube_cache(search, track.title, track.uri)
            if track is None:
                await ctx.send(":x: Fant ikke YouTube-video.", delete_after=5)
                await ctx.message.delete(delay=1)
                return
            if not is_playing(vc):
                vc.ctx = ctx
                track.requester = ctx.author
                await vc.play(track)
                try:
                    await vc.set_volume(DEFAULT_VOLUME)
                except Exception:
                    pass
                await show_now_playing(track, ctx)
            else:
                track.requester = ctx.author
                guild_queue.append(track)
                embed = discord.Embed(title=track.title, color=2303786)
                embed.set_author(name="Added To Queue", icon_url="https://cdn3.emoji.gg/emojis/3468-skype-music.gif")
                embed.add_field(name="Requested by", value=ctx.author.name, inline=True)
                embed.add_field(name="Position in queue", value=str(len(guild_queue)), inline=True)
                await ctx.send(embed=embed, delete_after=5)
            await ctx.message.delete(delay=1)
        except Exception as e:
            await ctx.send(f":x: Apple Music-feil: {e}", delete_after=6)
            await ctx.message.delete(delay=1)
        return
    # --- Spotify: enkeltspor ---
    if "open.spotify.com/track" in query:
        try:
            if sp is None:
                await ctx.send(":x: Spotify-støtte er ikke konfigurert. Sett SPOTIFY_CLIENT_ID og SPOTIFY_CLIENT_SECRET i .env.", delete_after=6)
                await ctx.message.delete(delay=1)
                return
            track_id = query.split("/")[-1].split("?")[0]
            search = await get_spotify_cache(track_id)
            if not search:
                track = sp.track(track_id)
                search = f"ytsearch:{track['name']} {track['artists'][0]['name']}"
                await set_spotify_cache(track_id, search)
            yt_cache = await get_youtube_cache(search)
            if yt_cache:
                track = await fetch_tracks(yt_cache[1], ctx=ctx)
                if not track:
                    raise Exception("YouTube-cache tom.")
                track = track[0]
            else:
                results = await fetch_tracks(search, ctx=ctx)
                if not results:
                    await ctx.send("Fant ikke sang på YouTube.", delete_after=5)
                    await ctx.message.delete(delay=1)
                    return
                track = results[0]
                await set_youtube_cache(search, track.title, track.uri)
            if not is_playing(vc):
                vc.ctx = ctx
                track.requester = ctx.author
                await vc.play(track)
                try:
                    await vc.set_volume(DEFAULT_VOLUME)
                except Exception:
                    pass
                await show_now_playing(track, ctx)
            else:
                track.requester = ctx.author
                guild_queue.append(track)
                SongEmbed = discord.Embed(title=f"{track.title}",  color=2303786)
                SongEmbed.set_author(name="Added To Queue", icon_url="https://cdn3.emoji.gg/emojis/3468-skype-music.gif")
                SongEmbed.add_field(name="Requested by", value=ctx.author.name, inline=True)
                SongEmbed.add_field(name="\u200b", value="\u200b", inline=True)
                SongEmbed.add_field(name="Position in queue", value=f"{len(guild_queue)}", inline=True)
                await ctx.send(embed=SongEmbed, delete_after=5)
                await ctx.message.delete(delay=1)
        except Exception as e:
            await ctx.send(f":x: Spotify-feil: {e}", delete_after=5)
            await ctx.message.delete(delay=1)
        return

    # --- Spotify: spilleliste ---
    elif "open.spotify.com/playlist" in query:
        await ctx.send("🔁 Henter spilleliste... (maks 20 sanger)", delete_after=7)
        await ctx.message.delete(delay=1)
        try:
            if sp is None:
                await ctx.send(":x: Spotify-støtte er ikke konfigurert. Sett SPOTIFY_CLIENT_ID og SPOTIFY_CLIENT_SECRET i .env.", delete_after=6)
                return
            playlist_id = query.split("/")[-1].split("?")[0]
            playlist_data = sp.playlist(playlist_id)
            total_tracks = playlist_data['tracks']['total']
            offset = max(0, total_tracks - 20)
            results = sp.playlist_tracks(playlist_id, offset=offset, limit=20)

            added = 0
            for item in reversed(results['items']):
                track = item['track']
                if not track or not track.get("id"):
                    continue
                spotify_id = track["id"]

                search = await get_spotify_cache(spotify_id)
                if not search:
                    search = f"ytsearch:{track['name']} {track['artists'][0]['name']}"
                    await set_spotify_cache(spotify_id, search)

                yt_cache = await get_youtube_cache(search)
                if yt_cache:
                    track_obj = await fetch_tracks(yt_cache[1], ctx=ctx)
                    if not track_obj:
                        continue
                    track_obj = track_obj[0]
                else:
                    yt_results = await fetch_tracks(search, ctx=ctx)
                    if not yt_results:
                        continue
                    track_obj = yt_results[0]
                    await set_youtube_cache(search, track_obj.title, track_obj.uri)

                track_obj.requester = ctx.author
                guild_queue.append(track_obj)
                added += 1

            await ctx.send(f"✅ Lagt til {added} sanger fra Spotify-spilleliste.", delete_after=6)
            if not is_playing(vc):
                vc.ctx = ctx
                await play_next(ctx)

        except Exception as e:
            await ctx.send(f":x: Klarte ikke hente spilleliste: {e}", delete_after=6)
        return

    # --- YouTube: spilleliste ---
    if "list=" in query and ("youtube.com" in query or "youtu.be" in query):
        playlist_url = query.strip()

        # Normaliser youtu.be-lenker slik at Lavalink gjenkjenner spillelisteparametere
        if "youtu.be/" in playlist_url:
            base, _, params = playlist_url.partition("?")
            video_id = base.rsplit("/", 1)[-1]
            if params:
                playlist_url = f"https://www.youtube.com/watch?v={video_id}&{params}"
            else:
                playlist_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            fetched = await fetch_tracks(playlist_url, ctx=ctx)
        except Exception as e:
            await ctx.send(f":x: Klarte ikke hente YouTube-spilleliste: {e}", delete_after=6)
            await ctx.message.delete(delay=1)
            return

        if hasattr(fetched, "tracks"):
            tracks = list(fetched.tracks)
            playlist_name = getattr(fetched, "name", None)
        else:
            tracks = list(fetched) if isinstance(fetched, list) else []
            playlist_name = None

        if not tracks:
            await ctx.send(":x: Fant ingen spor i spillelisten.", delete_after=5)
            await ctx.message.delete(delay=1)
            return

        for t in tracks:
            t.requester = ctx.author
        first_track, remaining_tracks = tracks[0], tracks[1:]
        if not is_playing(vc):
            vc.ctx = ctx
            await vc.play(first_track)
            try:
                await vc.set_volume(DEFAULT_VOLUME)
            except Exception:
                pass
            await show_now_playing(first_track, ctx)
            guild_queue.extend(remaining_tracks)
        else:
            guild_queue.extend(tracks)

        info_name = f" **{playlist_name}**" if playlist_name else ""
        await ctx.send(f"✅ Lagt til {len(tracks)} sanger fra YouTube-spilleliste{info_name}.", delete_after=6)
        await ctx.message.delete(delay=1)
        return

    # --- Vanlig YouTube-søk ---
    if (query.startswith("https://www.youtube.com/watch") or query.startswith("https://youtu.be/")) and "list=" not in query:
        query = query.split("&")[0]
    try:
        tracks = await fetch_tracks(query, ctx=ctx)
    except Exception as e:
        await ctx.send(f"Feil ved henting av sang: {e}", delete_after=5)
        await ctx.message.delete(delay=1)
        return

    if not tracks:
        await ctx.send("Fant ingen resultater.", delete_after=5)
        await ctx.message.delete(delay=1)
        return

    track = tracks[0]
    track.requester = ctx.author
    if not is_playing(vc):
        vc.ctx = ctx
        await vc.play(track)
        try:
            await vc.set_volume(DEFAULT_VOLUME)
        except Exception:
            pass
        await show_now_playing(track, ctx)
    else:
        guild_queue.append(track)
        SongEmbed = discord.Embed(title=f"{track.title}",  color=2303786)
        SongEmbed.set_author(name="Added To Queue", icon_url="https://cdn3.emoji.gg/emojis/3468-skype-music.gif")
        SongEmbed.add_field(name="Requested by", value=ctx.author.name, inline=True)
        SongEmbed.add_field(name="\u200b", value="\u200b", inline=True)
        SongEmbed.add_field(name="Position in queue", value=f"{len(guild_queue)}", inline=True)
        await ctx.send(embed=SongEmbed, delete_after=5)
    await ctx.message.delete(delay=1)


async def ensure_voice(ctx):
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await ctx.send(":x: Du m\u00e5 v\u00e6re i en voice-kanal.", delete_after=3)
        await ctx.message.delete(delay=1)
        return False
    try:
        me = ctx.guild.me or ctx.guild.get_member(bot.user.id)
        if me:
            perms = voice_channel.permissions_for(me)
            if not perms.connect:
                await ctx.send(":x: Botten mangler **Connect** i denne voice-kanalen.", delete_after=6)
                await ctx.message.delete(delay=1)
                return False
            if not perms.speak:
                await ctx.send(":x: Botten mangler **Speak** i denne voice-kanalen (da får du ingen lyd).", delete_after=8)
                await ctx.message.delete(delay=1)
                return False
    except Exception:
        pass

    vc = resolve_player(ctx.guild)
    if not vc or not getattr(vc, "channel", None):
        vc = await voice_channel.connect(
            cls=pomice.Player,
            self_deaf=True,
            reconnect=True,
            timeout=VOICE_CONNECT_TIMEOUT,
        )
        vc.ctx = ctx
        try:
            if isinstance(voice_channel, discord.StageChannel):
                try:
                    await voice_channel.request_to_speak()
                except Exception:
                    if ctx.guild.me:
                        await ctx.guild.me.edit(suppress=False)
        except Exception:
            pass

        await ctx.send(f":thumbsup: **Koblet til** `{voice_channel}` og laster sang...", delete_after=3)
        await ctx.message.delete(delay=1)
        return True
    elif vc.channel != voice_channel:
        await vc.move_to(voice_channel)
        try:
            if isinstance(voice_channel, discord.StageChannel):
                try:
                    await voice_channel.request_to_speak()
                except Exception:
                    if ctx.guild.me:
                        await ctx.guild.me.edit(suppress=False)
        except Exception:
            pass

        await ctx.send(f"Flyttet til `{voice_channel}`", delete_after=3)
        await ctx.message.delete(delay=1)
        return True
    return True


@bot.event
async def on_ready():
    print(f"Logget inn som {bot.user.name}")
    await init_cache_db()
    await ensure_lavalink_ready()

@bot.event
async def on_pomice_track_end(player, track, reason):
    reason = str(reason).lower()
    ctx = getattr(player, "ctx", None)
    if ctx and reason == "finished":
        await play_next(ctx)


@bot.event
async def on_pomice_track_exception(player, track, exception):
    ctx = getattr(player, "ctx", None)
    print(f"[Pomice] Track exception: {exception}")
    if ctx:
        await play_next(ctx)


@bot.event
async def on_pomice_track_stuck(player, track, threshold):
    ctx = getattr(player, "ctx", None)
    print(f"[Pomice] Track stuck: {threshold}")
    if ctx:
        await play_next(ctx)


def _stat_value(obj, *path):
    current = obj
    for key in path:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current


def _format_uptime_ms(uptime_ms):
    uptime_ms = int(uptime_ms or 0)
    hours, rem = divmod(uptime_ms // 1000, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


@bot.command(aliases=['q', 'list', 'que', 'Q'])
async def queue(ctx):
    guild_queue = get_guild_queue(ctx.guild.id)
    if not guild_queue:
        await ctx.send("\U0001F500 Køen er tom.", delete_after=3)
        await ctx.message.delete(delay=1)
    else:
        description = "\n".join([f"{idx + 1}. {track.title}" for idx, track in enumerate(guild_queue)])
        embed = discord.Embed(title="Musikk-kø", description=description, color=discord.Color.blue())
        await ctx.send(embed=embed, delete_after=10)
        await ctx.message.delete(delay=1)


@bot.command(aliases=['rm', 'delete', 'del'])
async def remove(ctx, index: int):
    guild_queue = get_guild_queue(ctx.guild.id)
    if 0 < index <= len(guild_queue):
        removed = guild_queue.pop(index - 1)
        await ctx.send(f"\u274C Fjernet fra køen: **{removed.title}**", delete_after=3)
        await ctx.message.delete(delay=1)
    else:
        await ctx.send(f":x: Ugyldig indeks. Velg et tall mellom 1 og {len(guild_queue)}", delete_after=5)
        await ctx.message.delete(delay=1)


@bot.command(aliases=["clearq", "clr", "resetq", "emptyq"])
async def clearqueue(ctx):
    guild_queue = get_guild_queue(ctx.guild.id)
    if not guild_queue:
        await ctx.send("🧹 Køen er allerede tom.", delete_after=4)
        await ctx.message.delete(delay=1)
        return

    guild_queue.clear()
    await ctx.send("🧹 Køen ble tømt.", delete_after=4)
    await ctx.message.delete(delay=1)


@bot.command(aliases=["prior", "movefirst", "top", "up", "move", "moveup", "prio", "pri", "priority"])
async def prioritize(ctx, index: int):
    guild_queue = get_guild_queue(ctx.guild.id)
    if not (1 <= index <= len(guild_queue)):
        await ctx.message.delete(delay=1)
        await ctx.send(f":x: Ugyldig indeks. Velg et tall mellom 1 og {len(guild_queue)}", delete_after=5)
        return

    track = guild_queue.pop(index - 1)
    guild_queue.insert(0, track)
    await ctx.message.delete(delay=1)
    await ctx.send(f"⏫ **{track.title}** er flyttet til toppen av køen!", delete_after=5)


@bot.command(aliases=["sh", "shuffleq", "mix", "randomize", "random", "rnd"])
async def shuffle(ctx):
    guild_queue = get_guild_queue(ctx.guild.id)
    if not guild_queue:
        await ctx.send("🎵 Køen er tom, ingenting å shuffle.", delete_after=5)
        await ctx.message.delete(delay=1)
        return

    from random import shuffle as rnd_shuffle
    rnd_shuffle(guild_queue)
    await ctx.send("🔀 Køen er shufflet!", delete_after=5)
    await ctx.message.delete(delay=1)


@bot.command()
async def showcache(ctx):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM spotify_cache") as cursor:
            spotify_count = (await cursor.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM youtube_cache") as cursor:
            youtube_count = (await cursor.fetchone())[0]

    embed = discord.Embed(title="🎶 Cache-status", color=discord.Color.green())
    embed.add_field(name="Spotify-ID ➜ YouTube-søk", value=str(spotify_count), inline=False)
    embed.add_field(name="YouTube-søk ➜ Direktelenke", value=str(youtube_count), inline=False)
    await ctx.send(embed=embed, delete_after=15)
    await ctx.message.delete(delay=1)


@bot.command()
@commands.has_permissions(administrator=True)
async def clearcache(ctx):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM spotify_cache")
        await db.execute("DELETE FROM youtube_cache")
        await db.commit()
    await ctx.send("🧹 Cache ble tømt!", delete_after=10)
    await ctx.message.delete(delay=1)


@bot.command(aliases=['commands', 'cmds', 'hjelp'])
async def info(ctx):
    commands_info = [
        ("!play / !p <sang/URL>", "Spill av sang eller legg til i køen"),
        ("!queue / !q / !list / !que / !Q", "Vis musikk-køen"),
        ("!remove / !rm / !delete / !del <nr>", "Fjern sang fra køen (indeks)"),
        ("!prioritize / !prior / !movefirst / !top / !up / !move / !moveup / !prio / !pri <nr>", "Flytt sang til toppen av køen"),
        ("!shuffle / !sh / !shuffleq / !mix / !randomize / !random / !rnd", "Shuffle køen"),
        ("!clearqueue / !clearq / !clr / !resetq / !emptyq", "Tøm køen"),
        ("!reset", "Full reset av botten i serveren"),
        ("!showcache", "Vis cache-status"),
        ("!clearcache", "Tøm cache (admin)"),
        ("!healthcheck / !ping / !status / !health", "Vis systemstatus"),
        ("!music / !musikk", "Vis musikk-kommandoer og bruk"),
        ("!invite / !inv / !discord / !disc / !link", "Vis invitasjonslink"),
    ]
    embed = discord.Embed(title="🎵 Bot Commands", color=discord.Color.blurple())
    for cmd, desc in commands_info:
        embed.add_field(name=cmd, value=desc, inline=False)
    embed.set_footer(text="Skriv !info for å vise denne listen igjen.")
    await ctx.send(embed=embed, delete_after=30)
    await ctx.message.delete(delay=1)


@bot.command(aliases=["ping", "status", "health"])
async def healthcheck(ctx):
    try:
        node = get_lavalink_node()
        stats = getattr(node, "stats", None)

        players = _stat_value(stats, "players")
        if players is None:
            players = getattr(node, "player_count", None)

        used = _stat_value(stats, "memory", "used")
        allocated = _stat_value(stats, "memory", "allocated")
        uptime_ms = _stat_value(stats, "uptime")
        ping = getattr(node, "ping", None)

        lines = ["🟢 Tilkoblet" if getattr(node, "is_connected", False) else "⚠️ Ikke tilkoblet"]
        if players is not None:
            lines.append(f"• Spillere: {players}")
        if used is not None and allocated is not None:
            lines.append(f"• RAM: {used // 1024**2}MB / {allocated // 1024**2}MB")
        if uptime_ms is not None:
            lines.append(f"• Uptime: {_format_uptime_ms(uptime_ms)}")
        if ping is not None:
            lines.append(f"• Ping: {ping}ms")
        lavalink_info = "\n".join(lines)
    except Exception as e:
        lavalink_info = f"🔴 Lavalink-feil: `{e}`"

    # Cache
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM spotify_cache") as cursor:
            spotify_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM youtube_cache") as cursor:
            youtube_count = (await cursor.fetchone())[0]

    # Spotify test
    if sp is None:
        spotify_status = "⚠️ Spotify ikke konfigurert"
    else:
        try:
            test = sp.track("3n3Ppam7vgaVa1iaRUc9Lp")  # Random test-ID
            spotify_status = f"🟢 Spotify OK"
        except Exception as e:
            spotify_status = f"🔴 Spotify-feil: `{e}`"

    embed = discord.Embed(title="📊 Systemstatus", color=discord.Color.green())
    embed.add_field(name="🎧 Lavalink", value=lavalink_info, inline=False)
    embed.add_field(name="🎶 Spotify", value=spotify_status, inline=False)
    embed.add_field(name="💽 Cache", value=f"Spotify: {spotify_count}\nYouTube: {youtube_count}", inline=False)
    embed.add_field(name="🔊 Voice", value="✅ Tilkoblet" if resolve_player(ctx.guild) else "⚠️ Ikke tilkoblet", inline=False)

    await ctx.send(embed=embed, delete_after=20)
    await ctx.message.delete(delay=1)


@bot.command()
@commands.has_permissions(administrator=True)
async def reset(ctx):
    await stop_and_clear(ctx)
    # Forsøk å koble Lavalink på nytt (manuell trigger)
    success = await connect_lavalink()
    status_txt = "Tilkoblet." if success else "Kunne ikke koble til Lavalink. Prøv igjen senere."
    await ctx.send(f"🔄 Server-reset ferdig. {status_txt}", delete_after=8)
    try:
        await ctx.message.delete(delay=1)
    except Exception:
        pass


@bot.command(aliases=['musikk'])
async def music(ctx):
    await ctx.message.delete(delay=1)
    embed_gather = discord.Embed(color=discord.Color.purple())
    embed_gather.set_author(name="Commands to play music:", icon_url="https://cdn3.emoji.gg/emojis/4579-pepediscodj.gif")
    embed_gather.add_field(
        name="Command:",
        value="```yaml\n!play | !p\n      | ⏯️\n      | ⏯️\n      | ⏭️\n      | ⏹️\n!q    | 📜\n!rm   | ❌\n!shuffle\n!Prio <nr>\n!clearq\n!reset```",
        inline=True
    )
    embed_gather.add_field(
        name="Functionality:",
        value="```yaml\nPlay <song> or queue more songs\nPause song\nResume playing song\nSkip to next song in the queue\nStop playing, leave, & clear the queue\nSee the queue\nRemove song from Queue.\nMix/Shuffle the queue\nMove song to front queue\nClear the queue\nReset the bot```",
        inline=True
    )
    embed_gather.add_field(
        name="Usage",
        value="```yaml\n!p <URL> or <artist - song name>\n\nExample: !p https://youtu.be/dQw4w9WgXcQ\nExample: !p miley cyrus flowers```",
        inline=False
    )
    embed_gather.set_footer(text="Music bot by Mus❤️ Enjoy.")
    await ctx.send(embed=embed_gather)


@bot.command(aliases=['inv', 'discord', 'disc', 'link'])
async def invite(ctx):
    await ctx.message.delete(delay=1)
    embed_inv = discord.Embed(title="Onal Discord server", color=discord.Color.purple())
    embed_inv.set_thumbnail(url="https://cdn.mos.cms.futurecdn.net/my8AUCgUhKERqBBwdPQuXG.jpg")
    embed_inv.add_field(name="Link:", value="```https://kimsec.net/discord```")
    embed_inv.set_footer(text="Everyone are welcome!", icon_url="https://cdn3.emoji.gg/emojis/8823-surroundedbyhearts.gif")
    await ctx.send(embed=embed_inv)


@bot.event
async def on_member_join(member):
    # Kjør kun på spesifikk server hvis WELCOME_GUILD_ID er satt
    if WELCOME_GUILD_ID and member.guild.id != WELCOME_GUILD_ID:
        return

    system_channel = member.guild.system_channel
    if not system_channel:
        return

    # Create welcome message
    welcome_message = f"Hey {member.mention}, Welcome to **{member.guild.name}** !"

    # Load the profile picture
    if member.avatar:
        profile_pic_url = member.avatar.url
        response = requests.get(profile_pic_url)
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        img = img.resize((330, 330))
    else:
        discriminator = int(member.discriminator)
        url = f"https://cdn.discordapp.com/embed/avatars/{discriminator % 5}.png"
        response = requests.get(url)
        img = Image.open(BytesIO(response.content)).convert("RGBA")
        img = img.resize((330, 330))

    # Create a circular mask
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + img.size, fill=255)

    # Apply the mask to the profile picture
    rounded_image = img.copy()
    rounded_image.putalpha(mask)

    # Create a new mask with a larger radius for the border
    border_size = 5
    border_mask = Image.new("L", (rounded_image.width + border_size*2, rounded_image.height + border_size*2), 0)
    draw = ImageDraw.Draw(border_mask)
    draw.ellipse((0, 0) + border_mask.size, fill=255, outline=255)

    # Apply the border mask to the rounded profile picture
    bordered_image = Image.new("RGBA", (rounded_image.width + border_size*2, rounded_image.height + border_size*2), (255, 255, 255, 0))
    bordered_image.paste(rounded_image, (border_size, border_size), rounded_image)
    bordered_image.putalpha(border_mask)

    # Create a new image with a solid color
    background_color = (23, 24, 30)
    background_size = (1100, 500)
    background = Image.new("RGB", background_size, background_color)

    # Create a mask with rounded corners for the black small background
    small_background_size = (990, 450)
    small_background = Image.new("RGB", small_background_size, (0, 0, 0))
    small_corner_radius = 10
    small_corner_mask = Image.new("L", small_background_size, 0)
    draw = ImageDraw.Draw(small_corner_mask)
    draw.rounded_rectangle((0, 0, small_background.width, small_background.height), small_corner_radius, fill=255)

    # Apply the corner mask to the small background
    small_background.putalpha(small_corner_mask)

    # Paste the small background onto the main background
    background.paste(small_background, (50, 25), small_background)

    # Create a mask with rounded corners for the main background
    corner_radius = 20
    corner_mask = Image.new("L", background_size, 0)
    draw = ImageDraw.Draw(corner_mask)
    draw.rounded_rectangle((0, 0, background.width, background.height), corner_radius, fill=255)

    # Apply the corner mask to the main background
    background.putalpha(corner_mask)

    # Paste the profile picture onto the background at the center
    offset = ((background.width - bordered_image.width) // 2, (background.height - bordered_image.height) // 4)
    result = background.copy()
    result.paste(bordered_image, offset, bordered_image)

    # Add text overlay below the circle image
    if member.discriminator == "0":
        text_overlay = f"{member.name} just joined the server"
    else:
        text_overlay = f"{member} just joined the server"
    font_size = 50
    font_color = (255, 255, 255)
    font = ImageFont.truetype(FONT_PATH, font_size)
    draw = ImageDraw.Draw(result)
    text_bbox = draw.textbbox((0, 0), text_overlay, font=font)
    text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
    text_position = ((result.width - text_size[0]) // 2, offset[1] + bordered_image.height + 20)
    draw.text(text_position, text_overlay, font=font, fill=font_color)

    # Convert the result image to bytes for uploading to Discord
    img_byte_arr = BytesIO()
    result.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    # Upload the image to Discord
    await system_channel.send(f"{welcome_message}", file=discord.File(fp=img_byte_arr, filename="welcome_card.png"))

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable. Set it in a .env file or environment before running.")

bot.run(DISCORD_TOKEN)
