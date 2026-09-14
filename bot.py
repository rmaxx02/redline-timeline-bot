import os
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import asyncio
import random
import io
from datetime import datetime, timezone
from collections import deque
import re
import urllib.request
import urllib.parse
import json
from PIL import Image, ImageDraw, ImageFont

load_dotenv()  # reads variables from a .env file in the same folder, if present

# 📡 PRODUCTION CHANNEL ID MATRIX - HARDWIRED ROUTING
LOG_ID = 1546911999051694123          # #🛠️┃bot-terminal Logs ID
WELCOME_CH_ID = 1546908252250443917   # ✅ welcome messages post in #general chat
LIVE_CH_ID = 1548192164037656607      # ✅ live streams ONLY get posted here
UPLOAD_CH_IDS = [1547061966520979457]  # ✅ new uploads get posted here only
LORE_CH_ID = 1547061966520979457      # ✅ your lore/timeline channel - watched for community links AND gets upload alerts
CLIPS_CH_ID = 1546911191568490556    # ✅ community clip submissions go here - Shorts only (under 2 minutes)
DAILY_RECAP_CH_ID = 1548174655934824539  # ✅ daily recap summary posts here every 24 hours
GET_ROLES_CH_ID = 1546895557715562567    # ✅ requests posted here get DM'd to everyone with the Recruiter role
RULES_CH_ID = 1546898931458379907        # ✅ #📜┃rules channel - where !postrules posts the pinnable highlights

# 🔒 HARDWIRED UNIFIED FORUM TIMELINE ENDPOINT
FORUM_CH_ID = 1547336797724479519     # Your #📋┃timeline-archive ID

# 🔑 SECRETS - loaded from environment, never hardcoded
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# 🎮 ONE-CLICK TEAM PICKER BUTTONS - persistent across bot restarts (custom_id + timeout=None)
class TeamPickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _assign(self, interaction: discord.Interaction, role_name: str):
        if not interaction.guild:
            await interaction.response.send_message(
                "⚠️ Team picking only works inside the server, not in DMs - head to the welcome channel!",
                ephemeral=True,
            )
            return

        # Fuzzy match: works even if the role name has an emoji, extra spacing, or different casing
        # added to it (e.g. "🏎️ Opie Fan" or "OPIE FAN" both still match "Opie fan").
        required_words = role_name.lower().split()  # e.g. ["opie", "fan"]
        role = None
        for candidate in interaction.guild.roles:
            candidate_lower = candidate.name.lower()
            if all(word in candidate_lower for word in required_words):
                role = candidate
                break

        if not role:
            await interaction.response.send_message(
                f"⚠️ Couldn't find a role matching **{role_name}** on this server - ask an admin to check the role name.",
                ephemeral=True,
            )
            return
        member = interaction.user
        if role in member.roles:
            await interaction.response.send_message(f"You're already a **{role.name}**! ✅", ephemeral=True)
            return
        await member.add_roles(role)
        await interaction.response.send_message(f"🎉 You're locked in as a **{role.name}**! Welcome to the crew.", ephemeral=True)

    @discord.ui.button(label="🏎️ Team Opie", style=discord.ButtonStyle.primary, custom_id="redline_team_opie")
    async def opie_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._assign(interaction, "Opie fan")

    @discord.ui.button(label="💻 Team Tray", style=discord.ButtonStyle.success, custom_id="redline_team_tray")
    async def tray_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._assign(interaction, "Tray fan")

    @discord.ui.button(label="🚓 Team Frenchie", style=discord.ButtonStyle.danger, custom_id="redline_team_frenchie")
    async def frenchie_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._assign(interaction, "Frenchie fan")

# 🧠 THE KEYWORD BRAIN TABLES
GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta", "war", "cg", "gg", "pdw"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing", "heist", "casino", "yacht"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal", "trial", "case", "arrested"]

# 👥 AI PLAYER IDENTITIES DATABASE FOR AUTOMATIC DISCORD MEMBER TAGGING
# Empty for now - no real Discord User IDs available yet. Every place this dict is used
# already handles a missing entry gracefully (falls back to no mention), so leaving it
# empty just means the bot doesn't @mention anyone until you add real IDs later, e.g.:
# PLAYERS_DATABASE = {"opie": "<@REAL_DISCORD_USER_ID>", "tray": "<@...>", "frenchie": "<@...>"}
PLAYERS_DATABASE = {}

# 📺 YOUTUBE CHANNEL IDS FOR LIVE/UPLOAD POLLING
# NOTE: these must be YouTube "Channel ID" values (start with "UC..."), not @handles.
# Each streamer now supports MULTIPLE channels (e.g. their main channel + their "extras" channel) -
# just add more IDs to that streamer's list. All channels in the list get polled the same way.
STREAMER_YOUTUBE_CHANNELS = {
    "Opie": ["UC8Uy6FP4vuSA_pTRXvCJmPQ", "UCntCTaM2Jz1sLN3iRwabpMA"],   # Elanip Extra + Elanip (main)
    "Tray": ["UCa1R0o4KutQTmi6ObmngGRQ", "UCk9xNdmgY8im4RDCops9YYw"],   # Treyten Extra + Treyten (main)
    "Frenchie": ["UCcISgmobjhJQzMqXMnnzgeQ"],   # ⬅️ add Frenchie's 2nd channel ID here if/when you confirm he has one
}

# 🔁 REVERSE LOOKUP - given a video's actual YouTube channel ID, find which streamer it belongs to.
CHANNEL_ID_TO_STREAMER = {
    channel_id: name
    for name, channel_ids in STREAMER_YOUTUBE_CHANNELS.items()
    for channel_id in channel_ids
}

# 🏆 SHARED TRACK/RANK CONSTANTS - used by the message handler AND commands like !rank, !addpoint
TRACK_EMOJI_MAP = {"Opie": "🏎️", "Tray": "💻", "Frenchie": "🚓"}
RANK_MAP = {
    "Opie": [(500, "Wheelman"), (250, "Getaway Driver"), (100, "Street Racer"), (25, "Grease Monkey")],
    "Tray": [(500, "Master Hacker"), (250, "Elite Hacker"), (100, "Green Hat"), (25, "Script Kiddie")],
    "Frenchie": [(500, "Ghost Operator"), (250, "Infiltrator"), (100, "Scout"), (25, "Lookout")],
}

# 📊 TRACKING DATA ARCHIVE, ANTI-DUPLICATE MEMORY & COOLDOWNS
USER_DATABASE = {}
SPAM_COOLDOWN = {}
PROCESSED_VIDEOS_CACHE = set()  # Brain memory cache that permanently blocks duplicate video links

# 📺 LIVE/UPLOAD POLLING MEMORY - tracked per INDIVIDUAL CHANNEL ID now (not per streamer name),
# since each streamer can have more than one channel and each needs its own "last seen" memory.
LAST_ANNOUNCED_VIDEO_ID = {channel_id: None for channel_id in CHANNEL_ID_TO_STREAMER}
LAST_ANNOUNCED_LIVE_ID = {channel_id: None for channel_id in CHANNEL_ID_TO_STREAMER}

# 🧵 RECENT ACTIVITY MEMORY - keeps the last 8 known video/live events per streamer, newest first.
# (Not currently used for anything beyond bookkeeping - reserved for a future feature.)
RECENT_VIDEOS_LOG = {name: deque(maxlen=8) for name in STREAMER_YOUTUBE_CHANNELS}

# 📅 DAILY RECAP TRACKING - accumulates throughout the day, gets posted and reset every 24 hours.
DAILY_STATS = {
    "clips_submitted": 0,
    "track_points": {"Opie": 0, "Tray": 0, "Frenchie": 0},
    "contributor_counts": {},   # {uid: clips submitted today}
    "uploads_today": [],        # list of (streamer_name, title, url)
    "lives_today": [],          # list of (streamer_name, title, url)
}


def reset_daily_stats():
    DAILY_STATS["clips_submitted"] = 0
    DAILY_STATS["track_points"] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
    DAILY_STATS["contributor_counts"] = {}
    DAILY_STATS["uploads_today"] = []
    DAILY_STATS["lives_today"] = []


# 📆 WEEKLY RECAP TRACKING - same idea as daily, but resets every 7 days for a bigger wrap-up.
WEEKLY_STATS = {
    "clips_submitted": 0,
    "track_points": {"Opie": 0, "Tray": 0, "Frenchie": 0},
    "contributor_counts": {},
    "uploads_this_week": [],
    "lives_this_week": [],
}


def reset_weekly_stats():
    WEEKLY_STATS["clips_submitted"] = 0
    WEEKLY_STATS["track_points"] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
    WEEKLY_STATS["contributor_counts"] = {}
    WEEKLY_STATS["uploads_this_week"] = []
    WEEKLY_STATS["lives_this_week"] = []


# 🎉 GLOBAL MILESTONE CELEBRATIONS - fires an immediate special announcement every time the
# server's ALL-TIME total clip count crosses a round number, instead of waiting for a recap.
TOTAL_CLIPS_ALL_TIME = 0
MILESTONE_STEP = 50  # celebrates every 50 total clips: 50, 100, 150, 200...
LAST_CELEBRATED_MILESTONE = 0


def record_recent_activity(streamer_name: str, kind: str, title: str, url: str, date_str: str):
    """Adds an event (upload/live/community-submitted clip) to the in-memory recent activity log."""
    if streamer_name not in RECENT_VIDEOS_LOG:
        RECENT_VIDEOS_LOG[streamer_name] = deque(maxlen=8)
    RECENT_VIDEOS_LOG[streamer_name].appendleft({
        "kind": kind,       # "upload", "live", or "community_clip"
        "title": title,
        "url": url,
        "date": date_str,
    })


def fetch_youtube_video_metadata(video_id: str):
    """
    Calls the official YouTube Data API v3 videos.list endpoint to get reliable
    metadata for a single video, including its real publish date (snippet.publishedAt),
    live broadcast status (liveStreamingDetails / snippet.liveBroadcastContent), and
    its duration (contentDetails.duration, ISO 8601 format e.g. "PT1M30S").
    Returns a dict or None if the lookup fails.
    """
    if not YOUTUBE_API_KEY:
        print("YOUTUBE_API_KEY not set - cannot fetch reliable publish date.")
        return None
    try:
        params = urllib.parse.urlencode({
            "part": "snippet,liveStreamingDetails,contentDetails",
            "id": video_id,
            "key": YOUTUBE_API_KEY,
        })
        url = f"https://www.googleapis.com/youtube/v3/videos?{params}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            items = data.get("items", [])
            if not items:
                return None
            return items[0]
    except Exception as e:
        print(f"YouTube Data API video lookup failed: {e}")
        return None


def parse_iso8601_duration_to_seconds(duration_str: str):
    """
    Converts a YouTube API ISO 8601 duration string (e.g. "PT1M30S", "PT45S", "PT2H")
    into total seconds. Returns None if it can't be parsed.
    """
    if not duration_str:
        return None
    match = re.match(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', duration_str)
    if not match:
        return None
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def fetch_latest_channel_activity(channel_id: str):
    """
    Calls YouTube Data API v3 search.list for a channel, ordered by date, to find
    the most recent upload. Also checks specifically for an active live broadcast.
    Returns (latest_video_item_or_None, live_video_item_or_None).
    """
    if not YOUTUBE_API_KEY:
        return None, None

    latest_video = None
    live_video = None

    try:
        # Most recent upload (any type)
        params = urllib.parse.urlencode({
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "maxResults": 1,
            "type": "video",
            "key": YOUTUBE_API_KEY,
        })
        url = f"https://www.googleapis.com/youtube/v3/search?{params}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            items = data.get("items", [])
            if items:
                latest_video = items[0]
    except Exception as e:
        print(f"YouTube latest-upload lookup failed for {channel_id}: {e}")

    try:
        # Active live broadcast, if any
        live_params = urllib.parse.urlencode({
            "part": "snippet",
            "channelId": channel_id,
            "eventType": "live",
            "type": "video",
            "key": YOUTUBE_API_KEY,
        })
        live_url = f"https://www.googleapis.com/youtube/v3/search?{live_params}"
        with urllib.request.urlopen(live_url, timeout=5) as live_response:
            live_data = json.loads(live_response.read().decode())
            live_items = live_data.get("items", [])
            if live_items:
                live_video = live_items[0]
    except Exception as e:
        print(f"YouTube live-check lookup failed for {channel_id}: {e}")

    return latest_video, live_video


@bot.event
async def on_ready():
    print("==================================================")
    print(f"🟢 LOGGED IN SUCCESS: {bot.user.name}")
    print("Redline Duplicate-Proof Forum Router Active...")
    print("==================================================")
    bot.add_view(TeamPickerView())  # keeps the team-picker buttons clickable even after a restart
    log_ch = bot.get_channel(LOG_ID)
    if log_ch:
        await log_ch.send("📟 **SYSTEM ONLINE:** Upgraded Chronological Forum Router running successfully.")
    status_rotator.start()
    youtube_activity_poller.start()
    daily_recap.start()
    weekly_recap.start()

# 🔄 AUTOMATED LIVE STATUS ROTATOR LOOP
bot.status_index = 0
@tasks.loop(seconds=15)
async def status_rotator():
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name="🏎️ Opie's POV (Driver)"),
        discord.Activity(type=discord.ActivityType.watching, name="💻 Tray's POV (Hacker)"),
        discord.Activity(type=discord.ActivityType.watching, name="🚓 Frenchie's POV (Recon)"),
        discord.Activity(type=discord.ActivityType.listening, name="!stats commands")
    ]
    await bot.change_presence(activity=statuses[bot.status_index % len(statuses)])
    bot.status_index += 1


# 📺 AUTOMATED YOUTUBE LIVE / NEW-UPLOAD ANNOUNCEMENT LOOP
@tasks.loop(minutes=5)
async def youtube_activity_poller():
    live_ch = bot.get_channel(LIVE_CH_ID)
    upload_channels = [ch for ch in (bot.get_channel(cid) for cid in UPLOAD_CH_IDS) if ch]
    forum_channel = bot.get_channel(FORUM_CH_ID)
    log_ch = bot.get_channel(LOG_ID)

    for streamer_name, channel_ids in STREAMER_YOUTUBE_CHANNELS.items():
        for channel_id in channel_ids:
            if "UCXXXX" in channel_id or "UCYYYY" in channel_id or "UCZZZZ" in channel_id:
                # Placeholder channel ID not yet configured - skip silently.
                continue

            latest_video, live_video = fetch_latest_channel_activity(channel_id)

            # --- Live broadcast check ---
            if live_video:
                live_video_id = live_video["id"]["videoId"]
                if LAST_ANNOUNCED_LIVE_ID.get(channel_id) != live_video_id:
                    LAST_ANNOUNCED_LIVE_ID[channel_id] = live_video_id
                    title = live_video["snippet"]["title"]
                    thumbnail = live_video["snippet"]["thumbnails"]["high"]["url"]
                    video_url = f"https://www.youtube.com/watch?v={live_video_id}"

                    # Pull the real description straight from YouTube for this live broadcast
                    live_metadata = fetch_youtube_video_metadata(live_video_id)
                    live_description = ""
                    if live_metadata:
                        live_description = live_metadata.get("snippet", {}).get("description", "")[:400]

                    streamer_mention = PLAYERS_DATABASE.get(streamer_name.lower(), "")
                    embed = discord.Embed(
                        title=f"🔴 {streamer_name} IS LIVE NOW",
                        description=f"**{title}**\n\n{live_description}".strip(),
                        url=video_url,
                        color=0xff0000,
                    )
                    embed.set_image(url=thumbnail)
                    embed.set_footer(text="Redline Live Alert System")
                    alert_content = f"@here {streamer_mention}".strip()

                    if live_ch:
                        await live_ch.send(content=alert_content, embed=embed)

                    # Also archive it in the forum channel - guarded so the SAME video/live
                    # never creates a second thread there, even if seen through another path.
                    if forum_channel and isinstance(forum_channel, discord.ForumChannel) and live_video_id not in PROCESSED_VIDEOS_CACHE:
                        try:
                            live_thread_result = await forum_channel.create_thread(
                                name=f"[LIVE] {streamer_name} | {title[:45]}",
                                embed=embed,
                            )
                            PROCESSED_VIDEOS_CACHE.add(live_video_id)
                            starter = getattr(live_thread_result, "message", None)
                            if starter:
                                await starter.add_reaction("🔴")
                        except Exception as e:
                            print(f"Forum thread creation failed for live stream: {e}")

                    if log_ch:
                        await log_ch.send(f"📡 **LIVE DETECTED:** {streamer_name} started streaming. `{video_url}`")

                    record_recent_activity(streamer_name, "live", title, video_url,
                                            datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                    DAILY_STATS["lives_today"].append((streamer_name, title, video_url, thumbnail))
                    WEEKLY_STATS["lives_this_week"].append((streamer_name, title, video_url, thumbnail))

            # --- New upload check ---
            if latest_video:
                video_id = latest_video["id"]["videoId"]
                if LAST_ANNOUNCED_VIDEO_ID.get(channel_id) is None:
                    # First run for this channel: just record the current latest video,
                    # don't announce it (avoids blasting old content on bot startup).
                    LAST_ANNOUNCED_VIDEO_ID[channel_id] = video_id
                elif LAST_ANNOUNCED_VIDEO_ID.get(channel_id) != video_id:
                    LAST_ANNOUNCED_VIDEO_ID[channel_id] = video_id
                    title = latest_video["snippet"]["title"]
                    thumbnail = latest_video["snippet"]["thumbnails"]["high"]["url"]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

                    # Pull the real publish date + full description from the official API
                    upload_metadata = fetch_youtube_video_metadata(video_id)
                    published_at = "Unknown"
                    video_description = ""
                    if upload_metadata:
                        published_at = upload_metadata.get("snippet", {}).get("publishedAt", "Unknown")
                        video_description = upload_metadata.get("snippet", {}).get("description", "")[:400]

                    streamer_mention = PLAYERS_DATABASE.get(streamer_name.lower(), "")
                    embed = discord.Embed(
                        title=f"📹 {streamer_name} JUST POSTED A NEW VIDEO",
                        description=f"**{title}**\n\n{video_description}".strip(),
                        url=video_url,
                        color=0x39ff14,
                    )
                    embed.add_field(name="📅 Published", value=published_at)
                    embed.set_image(url=thumbnail)
                    embed.set_footer(text="Redline Upload Alert System")

                    # Uploads go to BOTH configured upload channels (one of which is your lore channel)
                    for target_ch in upload_channels:
                        await target_ch.send(content=streamer_mention or None, embed=embed)

                    # Also archive it in the forum channel - guarded so the SAME video never
                    # creates a second thread there, even if it was already community-submitted.
                    if forum_channel and isinstance(forum_channel, discord.ForumChannel) and video_id not in PROCESSED_VIDEOS_CACHE:
                        try:
                            upload_thread_result = await forum_channel.create_thread(
                                name=f"[UPLOAD] {streamer_name} | {title[:45]}",
                                embed=embed,
                            )
                            PROCESSED_VIDEOS_CACHE.add(video_id)
                            starter = getattr(upload_thread_result, "message", None)
                            if starter:
                                await starter.add_reaction("📹")
                        except Exception as e:
                            print(f"Forum thread creation failed for upload: {e}")

                    if log_ch:
                        await log_ch.send(f"📡 **NEW UPLOAD DETECTED:** {streamer_name} posted a video. `{video_url}`")

                    record_recent_activity(streamer_name, "upload", title, video_url, published_at[:10] if published_at != "Unknown" else "Unknown")
                    DAILY_STATS["uploads_today"].append((streamer_name, title, video_url, thumbnail))
                    WEEKLY_STATS["uploads_this_week"].append((streamer_name, title, video_url, thumbnail))


@youtube_activity_poller.before_loop
async def before_youtube_poller():
    await bot.wait_until_ready()


# 📅 DAILY RECAP - posts a summary of the day's activity every 24 hours, then resets the counters.
RECAP_INTROS = [
    "🌆 The sun's setting on another day in Redline...",
    "📼 Rolling the tape back on the last 24 hours...",
    "🎙️ Tonight's broadcast is ready to roll...",
    "🌃 Another day, another set of stories logged...",
    "⚡ Here's what went down today...",
]
RECAP_OUTROS = [
    "🔥 Let's see what tomorrow brings.",
    "💤 That's a wrap - get some rest, operatives.",
    "🚦 See you on the streets tomorrow.",
    "📺 Same time tomorrow. Keep the clips coming.",
    "🏁 Another lap in the books.",
]
RECAP_COLORS = [0x9b59b6, 0xe74c3c, 0x3498db, 0xf1c40f, 0x2ecc71, 0xff6ec7]


def make_progress_bar(value: int, total: int, length: int = 12) -> str:
    if total <= 0:
        return "░" * length
    filled = round((value / total) * length)
    return "█" * filled + "░" * (length - filled)


# 🤠 WANTED POSTER GENERATOR - procedurally drawn frame (no external template needed),
# with the target's real Discord avatar composited into the middle.
WANTED_CHARGES = [
    "Grand Theft Auto", "Evading Police", "Reckless Driving", "Bank Robbery",
    "Vault Cracking", "Gang Activity", "Resisting Arrest", "Illegal Racing",
    "Breaking & Entering", "Assault on an Officer", "Hacking Municipal Systems",
]


def _get_poster_font(size: int, bold: bool = True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


# 🎬 ANIMATED WELCOME BANNER - pulsing color, scrolling checkered flag stripes, auto-loops in Discord.
BANNER_COLOR_CYCLE = [(255, 60, 60), (60, 120, 255), (60, 220, 120), (255, 215, 0)]  # red/blue/green/gold


def generate_welcome_banner() -> io.BytesIO:
    import math
    W, H = 700, 220
    n_frames = 24
    frames = []
    font_big = _get_poster_font(54)

    for i in range(n_frames):
        frame = Image.new("RGB", (W, H), (10, 10, 15))
        draw = ImageDraw.Draw(frame)

        offset = (i * 14) % 40
        check_size = 20
        for y_base in [0, H - check_size]:
            for x in range(-40, W + 40, check_size):
                xpos = x + offset
                col_index = ((xpos // check_size) + (0 if y_base == 0 else 1)) % 2
                color = (255, 255, 255) if col_index == 0 else (20, 20, 20)
                draw.rectangle([xpos, y_base, xpos + check_size, y_base + check_size], fill=color)

        t = i / n_frames
        color_idx = int(t * len(BANNER_COLOR_CYCLE)) % len(BANNER_COLOR_CYCLE)
        next_idx = (color_idx + 1) % len(BANNER_COLOR_CYCLE)
        blend = (t * len(BANNER_COLOR_CYCLE)) % 1
        c1, c2 = BANNER_COLOR_CYCLE[color_idx], BANNER_COLOR_CYCLE[next_idx]
        glow_color = tuple(int(c1[j] + (c2[j] - c1[j]) * blend) for j in range(3))

        text = "WELCOME TO REDLINE"
        tw = draw.textlength(text, font=font_big)
        y_bob = 90 + int(4 * math.sin(t * 2 * math.pi))
        draw.text(((W - tw) / 2, y_bob), text, font=font_big, fill=glow_color)

        frames.append(frame)

    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=80, loop=0)
    buffer.seek(0)
    return buffer


def generate_wanted_poster(avatar_bytes: bytes, display_name: str) -> io.BytesIO:
    """Builds a wanted-poster PNG with the given avatar image and name, returns it as an in-memory buffer."""
    W, H = 600, 800
    border_color = (60, 35, 20)

    bg = Image.new("RGB", (W, H), (222, 197, 145))
    noise = Image.effect_noise((W, H), 24).convert("L")
    bg = Image.composite(Image.new("RGB", (W, H), (200, 170, 110)), bg, noise.point(lambda p: 60 if p > 200 else 0))
    draw = ImageDraw.Draw(bg)

    draw.rectangle([15, 15, W - 15, H - 15], outline=border_color, width=8)
    draw.rectangle([28, 28, W - 28, H - 28], outline=border_color, width=2)

    font_wanted = _get_poster_font(90)
    text_w = draw.textlength("WANTED", font=font_wanted)
    draw.text(((W - text_w) / 2, 45), "WANTED", font=font_wanted, fill=border_color)

    avatar_size = 300
    avatar_pos = ((W - avatar_size) // 2, 190)
    try:
        avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize((avatar_size, avatar_size))
        avatar_img = avatar_img.convert("L").convert("RGB")  # grayscale for that old-timey mugshot look
        bg.paste(avatar_img, avatar_pos)
    except Exception as e:
        print(f"Wanted poster avatar processing failed: {e}")
        placeholder = Image.new("RGB", (avatar_size, avatar_size), (120, 120, 120))
        bg.paste(placeholder, avatar_pos)
    draw.rectangle([avatar_pos[0], avatar_pos[1], avatar_pos[0] + avatar_size, avatar_pos[1] + avatar_size], outline=border_color, width=6)

    font_name = _get_poster_font(min(44, int(2000 / max(len(display_name), 1))))
    name_w = draw.textlength(display_name, font=font_name)
    draw.text(((W - name_w) / 2, 505), display_name, font=font_name, fill=border_color)

    font_reward = _get_poster_font(30)
    reward_text = f"REWARD: ${random.randint(5, 95) * 1000:,}"
    reward_w = draw.textlength(reward_text, font=font_reward)
    draw.text(((W - reward_w) / 2, 565), reward_text, font=font_reward, fill=(120, 20, 20))

    font_charge = _get_poster_font(20, bold=False)
    charges = ", ".join(random.sample(WANTED_CHARGES, 2))
    charge_text = f"CHARGES: {charges}"
    if draw.textlength(charge_text, font=font_charge) > W - 60:
        charge_text = charges  # drop the prefix if it doesn't fit
    charge_w = draw.textlength(charge_text, font=font_charge)
    draw.text(((W - charge_w) / 2, 625), charge_text, font=font_charge, fill=border_color)

    buffer = io.BytesIO()
    bg.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


async def send_daily_recap():
    recap_ch = bot.get_channel(DAILY_RECAP_CH_ID)
    if not recap_ch:
        print("Daily recap channel not found - check DAILY_RECAP_CH_ID.")
        reset_daily_stats()
        return

    total_clips = DAILY_STATS["clips_submitted"]
    track_points = DAILY_STATS["track_points"]
    uploads_today = DAILY_STATS["uploads_today"]
    lives_today = DAILY_STATS["lives_today"]
    contributor_counts = DAILY_STATS["contributor_counts"]
    total_events = total_clips + len(uploads_today) + len(lives_today)

    intro = random.choice(RECAP_INTROS)
    outro = random.choice(RECAP_OUTROS)
    color = random.choice(RECAP_COLORS)

    # Fun "hype grade" based on how much happened today
    if total_events >= 15:
        grade, grade_line = "🌟 S-TIER", "Absolutely stacked day. This is what Redline is about."
    elif total_events >= 8:
        grade, grade_line = "🔥 A-TIER", "Big day. The archive's getting fat."
    elif total_events >= 3:
        grade, grade_line = "✅ B-TIER", "Solid, steady day of activity."
    elif total_events >= 1:
        grade, grade_line = "🌱 C-TIER", "Quiet, but something happened."
    else:
        grade, grade_line = "😴 REST DAY", "Nothing but tumbleweeds today."

    embed = discord.Embed(
        title="🌙✨ REDLINE DAILY RECAP ✨🌙",
        description=(
            f"{intro}\n\n"
            f"### {grade}\n"
            f"*{grade_line}*"
        ),
        color=color,
    )

    if total_clips > 0:
        max_points = max(track_points.values()) or 1
        bars = (
            f"🏎️ Opie     {make_progress_bar(track_points['Opie'], max_points)}  **{track_points['Opie']}**\n"
            f"💻 Tray     {make_progress_bar(track_points['Tray'], max_points)}  **{track_points['Tray']}**\n"
            f"🚓 Frenchie {make_progress_bar(track_points['Frenchie'], max_points)}  **{track_points['Frenchie']}**"
        )
        embed.add_field(name=f"🎬 {total_clips} Clip{'s' if total_clips != 1 else ''} Logged Today", value=bars, inline=False)
    else:
        embed.add_field(name="🎬 Clips Logged Today", value="Nobody submitted a clip today - be the first tomorrow!", inline=False)

    if contributor_counts:
        top_uid = max(contributor_counts, key=contributor_counts.get)
        top_user = recap_ch.guild.get_member(top_uid) if recap_ch.guild else None
        top_name = top_user.mention if top_user else f"User {top_uid}"
        embed.add_field(
            name="👑 MVP OF THE DAY",
            value=f"{top_name} — **{contributor_counts[top_uid]}** clip(s) submitted! Give 'em a round of applause. 👏",
            inline=False,
        )

    if lives_today:
        lives_text = "\n".join(f"🔴 **{name}** — [{title[:60]}]({url})" for name, title, url, _ in lives_today[:5])
        embed.add_field(name=f"📡 {len(lives_today)} Live Stream{'s' if len(lives_today) != 1 else ''} Today", value=lives_text, inline=False)

    if uploads_today:
        uploads_text = "\n".join(f"📹 **{name}** — [{title[:60]}]({url})" for name, title, url, _ in uploads_today[:5])
        embed.add_field(name=f"🆕 {len(uploads_today)} New Upload{'s' if len(uploads_today) != 1 else ''} Today", value=uploads_text, inline=False)

    # Spotlight thumbnail - prefers a live stream, falls back to an upload
    spotlight_thumb = None
    if lives_today:
        spotlight_thumb = lives_today[0][3]
    elif uploads_today:
        spotlight_thumb = uploads_today[0][3]
    if spotlight_thumb:
        embed.set_image(url=spotlight_thumb)

    # All-time top 3, for context alongside today's numbers
    if USER_DATABASE:
        alltime = sorted(
            USER_DATABASE.items(),
            key=lambda kv: kv[1].get("Opie", 0) + kv[1].get("Tray", 0) + kv[1].get("Frenchie", 0),
            reverse=True,
        )[:3]
        alltime = [(uid, total) for uid, data in alltime if (total := data.get("Opie", 0) + data.get("Tray", 0) + data.get("Frenchie", 0)) > 0]
        if alltime:
            medals = ["🥇", "🥈", "🥉"]
            lines = []
            for i, (uid, total) in enumerate(alltime):
                u = recap_ch.guild.get_member(uid) if recap_ch.guild else None
                name = u.mention if u else f"User {uid}"
                lines.append(f"{medals[i]} {name} — **{total}** all-time clips")
            embed.add_field(name="🏆 All-Time Leaderboard", value="\n".join(lines), inline=False)

    embed.set_footer(text=f"{outro}  •  New recap in 24 hours")
    await recap_ch.send(embed=embed)

    reset_daily_stats()


@tasks.loop(hours=24)
async def daily_recap():
    await send_daily_recap()


@daily_recap.before_loop
async def before_daily_recap():
    await bot.wait_until_ready()


# 📆 WEEKLY RECAP - a bigger wrap-up every 7 days, with a "Team of the Week" battle result.
@tasks.loop(hours=168)
async def weekly_recap():
    recap_ch = bot.get_channel(DAILY_RECAP_CH_ID)
    if not recap_ch:
        print("Weekly recap channel not found - check DAILY_RECAP_CH_ID.")
        reset_weekly_stats()
        return

    total_clips = WEEKLY_STATS["clips_submitted"]
    track_points = WEEKLY_STATS["track_points"]
    uploads_this_week = WEEKLY_STATS["uploads_this_week"]
    lives_this_week = WEEKLY_STATS["lives_this_week"]
    contributor_counts = WEEKLY_STATS["contributor_counts"]

    embed = discord.Embed(
        title="🏆✨ THE REDLINE WEEKLY WRAP ✨🏆",
        description="# 7 days. One archive. Let's see who showed up. 🎬",
        color=0xffd700,
    )

    # Team of the Week - whichever track earned the most points this week
    if total_clips > 0:
        winning_track = max(track_points, key=track_points.get)
        track_emojis = {"Opie": "🏎️", "Tray": "💻", "Frenchie": "🚓"}
        max_points = max(track_points.values()) or 1
        bars = "\n".join(
            f"{track_emojis[t]} {t:<9} {make_progress_bar(track_points[t], max_points, 14)}  **{track_points[t]}**"
            for t in ("Opie", "Tray", "Frenchie")
        )
        embed.add_field(
            name=f"👑 TEAM OF THE WEEK: {track_emojis[winning_track]} {winning_track}!",
            value=bars,
            inline=False,
        )
        embed.add_field(name="🎬 Total Clips This Week", value=f"**{total_clips}** clips archived", inline=False)
    else:
        embed.add_field(name="🎬 This Week", value="No clips got submitted this week - let's turn it up! 📈", inline=False)

    if contributor_counts:
        ranked = sorted(contributor_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        lines = []
        for i, (uid, count) in enumerate(ranked):
            u = recap_ch.guild.get_member(uid) if recap_ch.guild else None
            name = u.mention if u else f"User {uid}"
            lines.append(f"{medals[i]} {name} — **{count}** clip(s)")
        embed.add_field(name="🌟 Top 5 Contributors This Week", value="\n".join(lines), inline=False)

    if lives_this_week:
        embed.add_field(name="📡 Live Streams This Week", value=f"**{len(lives_this_week)}** stream(s) caught", inline=True)
    if uploads_this_week:
        embed.add_field(name="🆕 New Uploads This Week", value=f"**{len(uploads_this_week)}** video(s) caught", inline=True)

    # Spotlight the single biggest moment of the week if there is one
    spotlight = None
    if lives_this_week:
        spotlight = lives_this_week[0]
    elif uploads_this_week:
        spotlight = uploads_this_week[0]
    if spotlight:
        embed.set_image(url=spotlight[3])

    embed.set_footer(text="🔁 New weekly wrap in 7 days. Let's beat this week's numbers!")
    await recap_ch.send(content="@here", embed=embed)

    reset_weekly_stats()


@weekly_recap.before_loop
async def before_weekly_recap():
    await bot.wait_until_ready()


# 🚀 AUTOMATIC MEMBER JOIN GREETING & ROLE ASSIGNER
@bot.event
async def on_member_join(member):
    base_role = discord.utils.get(member.guild.roles, name="Member")
    if base_role: await member.add_roles(base_role)

    welcome_ch = bot.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        banner_buffer = generate_welcome_banner()
        banner_file = discord.File(fp=banner_buffer, filename="welcome_banner.gif")

        embed = discord.Embed(
            title="🏁💥 WELCOME TO REDLINE 💥🏁",
            description=(
                f"# 🚨 {member.mention} JUST ENTERED THE NETWORK 🚨\n\n"
                "**You just joined one of the most active multi-POV roleplay tracking servers running.**\n"
                "Live streams, uploads, and community clips all get caught automatically and archived forever. "
                "Milestone celebrations fire off server-wide. Daily and weekly recaps drop like clockwork. "
                "This place doesn't sleep. 🌆\n\n"
                f"📌 Make sure to check out <#{RULES_CH_ID}> before diving in.\n\n"
                "🏆 **CLIMB THE RANKS**\n"
                "🏎️ Opie: Grease Monkey ➔ Street Racer ➔ Getaway Driver ➔ **Wheelman**\n"
                "💻 Tray: Script Kiddie ➔ Green Hat ➔ Elite Hacker ➔ **Master Hacker**\n"
                "🚓 Frenchie: Lookout ➔ Scout ➔ Infiltrator ➔ **Ghost Operator**\n\n"
                "📊 **COMMANDS**\n"
                "`!help` — full guide to everything the bot does\n"
                "`!stats` — your personal scoreboard\n"
                "`!wanted` — get your own wanted poster made 🤠\n"
                "`!scanner` — police radio chatter for the vibes 📻\n\n"
                "🌙 A **Daily Recap** and 🏆 a **Weekly Wrap** post automatically so you never miss what happened.\n\n"
                "# 👇 LOCK IN YOUR TEAM RIGHT NOW 👇"
            ),
            color=random.choice([0xff3c3c, 0x3c78ff, 0x3cdc78, 0xffd700])
        )
        embed.set_image(url="attachment://welcome_banner.gif")
        embed.set_footer(text=f"Redline Operative #{len(member.guild.members)} | Grid Sync Active 🟢")
        await welcome_ch.send(embed=embed, file=banner_file, view=TeamPickerView())

    # 📬 PERSONAL DM WELCOME - a more personal touch alongside the public channel post
    try:
        dm_embed = discord.Embed(
            title="🏁 Welcome to Redline!",
            description=(
                f"Hey {member.name}, glad to have you on board!\n\n"
                "Quick start:\n"
                "1️⃣ Head back to the server and pick your team (Opie / Tray / Frenchie) using the buttons in the welcome message.\n"
                "2️⃣ Type `!help` in any channel for a full breakdown of how everything works.\n"
                "3️⃣ Post YouTube clips in the lore channel to start earning points toward your team.\n\n"
                "See you in there! 🏎️💻🚓"
            ),
            color=0xff0000,
        )
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        # Member has DMs from server members/bots disabled - not an error, just skip silently.
        pass

# 📊 UPGRADED LEADERBOARD STATS COMMAND
async def send_leaderboard(ctx):
    if not USER_DATABASE:
        await ctx.send("📊 **Scoreboard Empty:** No clips have been logged in the archive yet!")
        return

    leaderboard_data = []
    for uid, data in USER_DATABASE.items():
        total_clips = data.get("Opie", 0) + data.get("Tray", 0) + data.get("Frenchie", 0)
        if total_clips == 0:
            continue
        user_obj = ctx.guild.get_member(uid) or await bot.fetch_user(uid)
        user_name = user_obj.name if user_obj else f"User {uid}"
        leaderboard_data.append((total_clips, user_name, data.get("Opie", 0), data.get("Tray", 0), data.get("Frenchie", 0)))

    if not leaderboard_data:
        await ctx.send("📊 **Scoreboard Empty:** No clips have been logged in the archive yet!")
        return

    leaderboard_data.sort(key=lambda x: x[0], reverse=True)  # sort by total clips, highest first

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    embed = discord.Embed(
        title="🏆 REDLINE ALL-TIME LEADERBOARD 🏆",
        description=f"The top {min(10, len(leaderboard_data))} chronological timeline contributors, out of **{len(leaderboard_data)}** total.",
        color=0xd4af37,
    )
    for i, (total, name, opie_pts, tray_pts, frenchie_pts) in enumerate(leaderboard_data[:10]):
        embed.add_field(
            name=f"{medals[i]} {name} — {total} clips",
            value=f"🏎️ Opie: *{opie_pts}* | 💻 Tray: *{tray_pts}* | 🚓 Frenchie: *{frenchie_pts}*",
            inline=False
        )
    embed.set_footer(text="Keep submitting clips to climb the ranks!")
    await ctx.send(embed=embed)


@bot.command()
async def stats(ctx, *, option: str = None):
    if option and option.lower() == "leaderboard":
        await send_leaderboard(ctx)
        return

    uid = ctx.author.id
    user_data = USER_DATABASE.get(uid, {"Opie": 0, "Tray": 0, "Frenchie": 0})
    embed = discord.Embed(title=f"📊 {ctx.author.name}'s Track Progression Stats", description="Your verified milestone submissions.", color=0xe67e22)
    embed.add_field(name="🏎️ Opie (Driver Track)", value=f"Submissions: **{user_data['Opie']}**", inline=True)
    embed.add_field(name="💻 Tray (Hacker Track)", value=f"Submissions: **{user_data['Tray']}**", inline=True)
    embed.add_field(name="🚓 Frenchie (Recon Track)", value=f"Submissions: **{user_data['Frenchie']}**", inline=True)
    embed.set_footer(text="Type '!stats leaderboard' to see the server's top 5 contributors!")
    await ctx.send(embed=embed)

# 📖 CUSTOM HELP COMMAND - GO-HAM FULL EXPLANATION
@bot.command()
async def help(ctx):
    overview_embed = discord.Embed(
        title="📖 REDLINE BOT — FULL GUIDE (1/2)",
        description=(
            "This bot tracks and archives roleplay clips from **Opie**, **Tray**, and **Frenchie**, "
            "automatically catches their live streams and new YouTube uploads, and runs a "
            "points/rank system for everyone who submits clips. Here's everything it does."
        ),
        color=0x00b0f4,
    )
    overview_embed.add_field(
        name="💬 Commands",
        value=(
            "`!help` — shows this guide\n"
            "`!stats` — your own clip counts for Opie / Tray / Frenchie\n"
            "`!stats leaderboard` or `!leaderboard` — top 10 server-wide\n"
            "`!rank` — how many clips until your next rank-up\n"
            "`!milestone` — progress toward the next server-wide celebration\n"
            "`!opie` / `!tray` / `!frenchie` — that streamer's most recent activity\n"
            "`!wanted [@user]` — generates a fun wanted poster for yourself or someone else\n"
            "`!scanner` — random GTA-style police radio chatter"
        ),
        inline=False,
    )
    overview_embed.add_field(
        name="🎬 Submitting a Clip",
        value=(
            "Post a normal YouTube link (youtube.com/watch?v=... or youtu.be/...) **in the lore channel**. "
            "The bot will:\n"
            "1️⃣ Pull the video's real title, thumbnail, and actual YouTube upload date (not just when it was posted to Discord)\n"
            "2️⃣ Scan the title/description for keywords and sort it into a category automatically\n"
            "3️⃣ Detect which player's names are mentioned in the video\n"
            "4️⃣ Create an organized thread for it in the archive forum, tagged by category, streamer, and year\n"
            "5️⃣ Give the poster a point on whichever streamer's channel the video actually came from\n\n"
            "Your message stays in the lore channel afterward - it doesn't get deleted."
        ),
        inline=False,
    )
    overview_embed.add_field(
        name="🚫 What Gets Blocked",
        value=(
            "• Posting the SAME video twice - it gets deleted and rejected as a duplicate\n"
            "• Posting links too fast (within 5 seconds of your last one) - flagged as spam and deleted\n"
            "• Links posted outside the lore channel are simply ignored - they won't be processed at all"
        ),
        inline=False,
    )
    overview_embed.add_field(
        name="🏷️ Clip Categories (auto-detected from keywords)",
        value=(
            "🔴 **Gang War** — turf, shootout, gang names, block conflicts\n"
            "💰 **Heist** — vault, thermite, drilling, casino, getaway\n"
            "⚖️ **Court Case** — trial, judge, lawyer, warrant, arrest\n"
            "📦 **General Log** — everything else"
        ),
        inline=False,
    )
    overview_embed.set_footer(text="Guide continues below ⬇️")

    ranks_embed = discord.Embed(
        title="📖 REDLINE BOT — FULL GUIDE (2/2)",
        description="Points, ranks, and the automatic YouTube alert system.",
        color=0x00b0f4,
    )
    ranks_embed.add_field(
        name="🏆 Points & Ranks",
        value=(
            "Every clip you submit earns 1 point toward whichever streamer's channel the video "
            "actually came from - not your own Discord roles. Hit these milestones on a track to "
            "automatically get promoted (a role gets assigned and an announcement posts):\n\n"
            "**Opie Track:** Grease Monkey (25) ➔ Street Racer (100) ➔ Getaway Driver (250) ➔ Wheelman (500)\n"
            "**Tray Track:** Script Kiddie (25) ➔ Green Hat (100) ➔ Elite Hacker (250) ➔ Master Hacker (500)\n"
            "**Frenchie Track:** Lookout (25) ➔ Scout (100) ➔ Infiltrator (250) ➔ Ghost Operator (500)"
        ),
        inline=False,
    )
    ranks_embed.add_field(
        name="📡 Automatic Live & Upload Alerts",
        value=(
            "The bot checks Opie, Tray, and Frenchie's YouTube channels every few minutes - no one "
            "needs to post anything for this part.\n\n"
            "🔴 **Going live** gets posted immediately with an @here ping, the stream title, and description.\n"
            "📹 **New uploads** get posted with the video's real description and official publish date.\n\n"
            "Each streamer can have more than one channel tracked (e.g. their main channel plus a clips/extras channel) - "
            "activity from any of them gets caught."
        ),
        inline=False,
    )
    ranks_embed.add_field(
        name="🌙 Daily Recap & 🏆 Weekly Wrap",
        value=(
            "Every 24 hours, a **Daily Recap** posts automatically with the day's clips, an MVP shoutout, "
            "and any live streams/uploads caught that day.\n\n"
            "Every 7 days, a bigger **Weekly Wrap** posts with a Team of the Week battle, top 5 contributors, "
            "and a spotlight on the week's biggest moment."
        ),
        inline=False,
    )
    ranks_embed.add_field(
        name="🎉 Milestone Celebrations",
        value="Every time the server's all-time clip count hits a round number, a special @here announcement fires immediately - keep an eye out!",
        inline=False,
    )
    ranks_embed.add_field(
        name="💰 Heist Announcements (staff only)",
        value="Staff can run `!heist [description]` to post a stylized heist-in-progress announcement with an @here ping.",
        inline=False,
    )
    ranks_embed.add_field(
        name="📌 Rule Highlights (staff only)",
        value="Staff can run `!postrules` in the rules channel to post the pinnable rule highlights message.",
        inline=False,
    )
    ranks_embed.add_field(
        name="🎮 Picking Your Team",
        value="Use the buttons on the welcome message when you join to instantly pick Opie / Tray / Frenchie as your team - no need to hunt for a separate channel.",
        inline=False,
    )
    ranks_embed.add_field(
        name="⚠️ Good to Know",
        value="Clip counts and the leaderboard are stored in memory - if the bot restarts, those numbers reset to zero. This isn't a bug, just how the current setup works.",
        inline=False,
    )
    ranks_embed.set_footer(text="Questions? Ask a server admin.")

    await ctx.send(embeds=[overview_embed, ranks_embed])


# ⚡ !rank - shows how many clips are needed until your next rank-up, per track
@bot.command()
async def rank(ctx):
    uid = ctx.author.id
    user_data = USER_DATABASE.get(uid, {"Opie": 0, "Tray": 0, "Frenchie": 0})

    embed = discord.Embed(title=f"⚡ {ctx.author.name}'s Rank Progress", color=0x1abc9c)
    for track in ("Opie", "Tray", "Frenchie"):
        count = user_data.get(track, 0)
        tiers = sorted(RANK_MAP[track])  # ascending: (25, name), (100, name), (250, name), (500, name)
        next_tier = next((t for t in tiers if count < t[0]), None)
        current_rank = None
        for milestone, rank_name in reversed(tiers):
            if count >= milestone:
                current_rank = rank_name
                break

        if next_tier is None:
            status = f"🏆 **MAX RANK** ({current_rank}) — {count} clips"
        else:
            remaining = next_tier[0] - count
            rank_line = f"Currently: **{current_rank}**\n" if current_rank else ""
            status = f"{rank_line}{remaining} more clip(s) until **{next_tier[1]}**"
        embed.add_field(name=f"{TRACK_EMOJI_MAP[track]} {track}", value=status, inline=False)

    await ctx.send(embed=embed)


# 📋 !leaderboard - shortcut for "!stats leaderboard"
@bot.command()
async def leaderboard(ctx):
    await stats(ctx, option="leaderboard")


# 📺 !opie / !tray / !frenchie - quick check on a streamer's most recent known activity
async def _streamer_recent_activity(ctx, streamer_name: str):
    events = RECENT_VIDEOS_LOG.get(streamer_name)
    if not events:
        await ctx.send(f"{TRACK_EMOJI_MAP[streamer_name]} No recent activity recorded for **{streamer_name}** yet.")
        return
    embed = discord.Embed(title=f"{TRACK_EMOJI_MAP[streamer_name]} {streamer_name} - Recent Activity", color=0x3498db)
    for e in list(events)[:5]:
        embed.add_field(name=f"[{e['kind'].upper()}] {e['date']}", value=f"[{e['title'][:60]}]({e['url']})", inline=False)
    await ctx.send(embed=embed)


@bot.command()
async def opie(ctx):
    await _streamer_recent_activity(ctx, "Opie")


@bot.command()
async def tray(ctx):
    await _streamer_recent_activity(ctx, "Tray")


@bot.command()
async def frenchie(ctx):
    await _streamer_recent_activity(ctx, "Frenchie")


# 🎯 !milestone - shows progress toward the next server-wide milestone celebration
@bot.command()
async def milestone(ctx):
    next_milestone = ((TOTAL_CLIPS_ALL_TIME // MILESTONE_STEP) + 1) * MILESTONE_STEP
    remaining = next_milestone - TOTAL_CLIPS_ALL_TIME
    embed = discord.Embed(
        title="🎯 Milestone Tracker",
        description=(
            f"**{TOTAL_CLIPS_ALL_TIME}** total clips archived server-wide.\n"
            f"{make_progress_bar(TOTAL_CLIPS_ALL_TIME % MILESTONE_STEP, MILESTONE_STEP, 16)}\n"
            f"**{remaining}** more clip(s) until the next celebration at **{next_milestone}**! 🎉"
        ),
        color=0xffd700,
    )
    await ctx.send(embed=embed)


# 🔁 !recap - manually re-post the daily recap on demand (staff only, since it also resets the day's counters)
@bot.command()
@commands.has_permissions(manage_guild=True)
async def recap(ctx):
    await ctx.send("🌙 Generating the daily recap now...")
    await send_daily_recap()


# 🛠️ ADMIN COMMANDS - all require Manage Server permission
@bot.command()
@commands.has_permissions(manage_guild=True)
async def addpoint(ctx, member: discord.Member, track: str):
    track = track.strip().capitalize()
    if track not in ("Opie", "Tray", "Frenchie"):
        await ctx.send("⚠️ Track must be one of: `Opie`, `Tray`, `Frenchie`.")
        return
    if member.id not in USER_DATABASE:
        USER_DATABASE[member.id] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
    USER_DATABASE[member.id][track] += 1
    new_count = USER_DATABASE[member.id][track]
    await ctx.send(f"✅ Added 1 point to {member.mention}'s **{track}** track. New total: **{new_count}**.")


@bot.command()
@commands.has_permissions(manage_guild=True)
async def removepoint(ctx, member: discord.Member, track: str):
    track = track.strip().capitalize()
    if track not in ("Opie", "Tray", "Frenchie"):
        await ctx.send("⚠️ Track must be one of: `Opie`, `Tray`, `Frenchie`.")
        return
    if member.id not in USER_DATABASE:
        USER_DATABASE[member.id] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
    USER_DATABASE[member.id][track] = max(0, USER_DATABASE[member.id][track] - 1)
    new_count = USER_DATABASE[member.id][track]
    await ctx.send(f"✅ Removed 1 point from {member.mention}'s **{track}** track. New total: **{new_count}**.")


@bot.command()
@commands.has_permissions(manage_guild=True)
async def resetstats(ctx, target: str):
    if target.lower() == "all":
        USER_DATABASE.clear()
        await ctx.send("🧹 Wiped the entire leaderboard. Everyone starts fresh.")
        return
    try:
        member = await commands.MemberConverter().convert(ctx, target)
    except commands.MemberNotFound:
        await ctx.send("⚠️ Couldn't find that member. Use `!resetstats @user` or `!resetstats all`.")
        return
    USER_DATABASE[member.id] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
    await ctx.send(f"🧹 Reset {member.mention}'s stats back to zero.")


# 🤠 !wanted @user - generates a fun wanted poster using their real Discord avatar
@bot.command()
async def wanted(ctx, member: discord.Member = None):
    target = member or ctx.author
    try:
        avatar_bytes = await target.display_avatar.replace(size=256).read()
    except Exception as e:
        await ctx.send(f"⚠️ Couldn't fetch {target.mention}'s avatar right now - try again in a moment.")
        print(f"Wanted poster avatar fetch failed: {e}")
        return

    poster_buffer = generate_wanted_poster(avatar_bytes, target.display_name)
    file = discord.File(fp=poster_buffer, filename="wanted.png")
    embed = discord.Embed(
        title=f"🚨 WANTED: {target.display_name} 🚨",
        description="Last seen causing chaos on the streets of Redline. Approach with caution.",
        color=0x8b4513,
    )
    embed.set_image(url="attachment://wanted.png")
    await ctx.send(embed=embed, file=file)


# 📻 !scanner - random GTA-style police radio chatter for atmosphere
SCANNER_LINES = [
    "🚔 10-4, unit responding to a 211 in progress downtown.",
    "📻 *static* ...suspect vehicle last seen heading north on the highway...",
    "🚨 All units, BOLO for a black sedan involved in a hit and run.",
    "📻 Dispatch, we've got shots fired near the docks, requesting backup.",
    "🚔 Suspect is on foot, repeat, suspect is on foot near the train yard.",
    "📻 *static* ...vault silent alarm triggered at the downtown bank...",
    "🚨 Units be advised, high speed pursuit heading toward the freeway on-ramp.",
    "📻 Dispatch, we have a 10-15, one in custody, requesting a transport unit.",
    "🚔 Air support requested, suspects fleeing in multiple vehicles.",
    "📻 *static* ...be advised, armed and considered dangerous...",
]


@bot.command()
async def scanner(ctx):
    await ctx.send(random.choice(SCANNER_LINES))


# 💰 !heist - staff-triggered stylized heist announcement
HEIST_INTROS = [
    "🚨 ALARM TRIPPED",
    "💰 VAULT CRACKING IN PROGRESS",
    "🔓 SECURITY SYSTEMS DOWN",
    "🏦 BREACH DETECTED",
]


@bot.command()
@commands.has_permissions(manage_guild=True)
async def heist(ctx, *, description: str = "A heist is going down RIGHT NOW."):
    embed = discord.Embed(
        title=random.choice(HEIST_INTROS),
        description=f"# 💰 HEIST IN PROGRESS 💰\n{description}",
        color=0x39ff14,
    )
    embed.set_footer(text="Get in position. This one's live.")
    await ctx.send(content="@here", embed=embed)


# 📌 !postrules - posts the rule highlights to the rules channel ONCE, for staff to pin manually.
# This does NOT run automatically - it's a one-time command so the rules channel doesn't get spammed.
@bot.command()
@commands.has_permissions(manage_guild=True)
async def postrules(ctx):
    embed = discord.Embed(
        title="📌 RULE HIGHLIGHTS",
        description=(
            f"*(full rules pinned in <#{RULES_CH_ID}>)*\n\n"
            "1️⃣ No RDM, VDM, powergaming, metagaming, or NVL\n"
            "2️⃣ Zero tolerance for racism, slurs, or toxicity toward anyone\n"
            "3️⃣ Never speak OOC in-character — all reports go through the ticket system\n"
            "4️⃣ No external tools, scripts, macros, or mods to exploit mechanics or track players\n"
            "5️⃣ Quality mic required, no external/copyrighted music\n"
            "6️⃣ Follow Discord ToS — no illegal links, no malicious behavior"
        ),
        color=0xff3c3c,
    )
    embed.set_footer(text="Pin this message so it stays at the top of the channel.")
    sent_message = await ctx.send(embed=embed)
    await ctx.send(f"✅ Posted. Pin it here: {sent_message.jump_url}", delete_after=15)


# ⚠️ Friendly error message when someone without permission tries an admin-only command
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You need **Manage Server** permission to use that command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("⚠️ Couldn't find that member - make sure you @mention them correctly.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing something - check `!help` for how to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # silently ignore unknown commands rather than erroring
    else:
        print(f"Unhandled command error: {error}")


# 📋 CHRONOLOGICAL FORUM ROUTING FILTER WITH SPAM & DUPLICATE BLOCKING
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    content_lower = msg.content.lower()

    # 📨 GET-ROLES REQUEST FORWARDER - anything typed in this channel gets DM'd to every
    # member holding a role matching "Recruiter" (fuzzy-matched, so emoji/formatting is fine).
    if msg.channel.id == GET_ROLES_CH_ID:
        recruiter_roles = [r for r in msg.guild.roles if "recruiter" in r.name.lower()]
        recruiters = {member for role in recruiter_roles for member in role.members}
        if recruiters:
            request_embed = discord.Embed(
                title="📨 New Role Request",
                description=msg.content or "*(no text - attachment or embed only)*",
                color=0x3498db,
            )
            request_embed.add_field(name="👤 From", value=f"{msg.author.mention} ({msg.author.name})", inline=True)
            request_embed.add_field(name="📍 Channel", value=msg.channel.mention, inline=True)
            request_embed.add_field(name="🔗 Jump to message", value=f"[Click here]({msg.jump_url})", inline=False)
            request_embed.set_footer(text="Sent because you have a Recruiter role")

            for recruiter in recruiters:
                try:
                    await recruiter.send(embed=request_embed)
                except discord.Forbidden:
                    pass  # that recruiter has DMs disabled - skip silently
        # Note: intentionally NOT returning here, so this channel can still work
        # normally for anything else (e.g. if it also has YouTube links watched elsewhere).

    yt_match = re.search(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11}))', msg.content)
    if yt_match and msg.channel.id in (LORE_CH_ID, CLIPS_CH_ID):
        video_url = yt_match.group(1)
        video_id = yt_match.group(2)
        uid = msg.author.id
        current_time = msg.created_at.timestamp()
        
        if current_time - SPAM_COOLDOWN.get(uid, 0) < 5:
            await msg.channel.send(f"⚠️ {msg.author.mention}, slow down!", delete_after=3)
            try: await msg.delete()
            except: pass
            return
        SPAM_COOLDOWN[uid] = current_time

        # 🧠 ANTI-DUPLICATE BLOCK - still stops a repost from earning a point or creating a new thread,
        # but no longer deletes the message or treats it like a violation.
        if video_id in PROCESSED_VIDEOS_CACHE:
            await msg.channel.send(f"👀 {msg.author.mention} heads up, this one's already logged in the archive - no new thread or point for a repeat!", delete_after=10)

            log_ch = bot.get_channel(LOG_ID)
            if log_ch:
                await log_ch.send(f"ℹ️ **DUPLICATE NOTED:** {msg.author.mention} reposted an already-logged video. Video ID: `{video_id}`. Message left as-is.")
            return
        # NOTE: video_id only gets added to PROCESSED_VIDEOS_CACHE further down, AFTER the
        # Shorts-length gate passes - so a video rejected for being too long there can still
        # legitimately be posted in the lore channel afterward.

        # 📡 BROWSER-SPOOF DATA ENGINE LOOKUP - FETCH REAL YOUTUBE TITLE & PICTURE THUMBNAIL
        actual_video_title = "Unknown Clip Entry Description"
        video_thumbnail_url = None
        try:
            params = urllib.parse.urlencode({'format': 'json', 'url': video_url})
            oembed_url = f"https://www.youtube.com/oembed?{params}"
            req = urllib.request.Request(
                oembed_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                actual_video_title = data.get('title', actual_video_title)
                video_thumbnail_url = data.get('thumbnail_url')
        except Exception as e:
            print(f"Title fetch failed: {e}")

        # 📅 RELIABLE YOUTUBE PUBLISH DATE LOOKUP VIA OFFICIAL DATA API (replaces HTML scraping)
        youtube_upload_date_string = msg.created_at.strftime("%Y-%m-%d")  # fallback only, used if API lookup fails
        thread_date_prefix = msg.created_at.strftime("%b %Y")
        target_year_tag_name = f"{msg.created_at.year} Archive"

        video_metadata = fetch_youtube_video_metadata(video_id)
        source_channel_id = None
        if video_metadata:
            published_at_raw = video_metadata.get("snippet", {}).get("publishedAt")  # e.g. "2024-03-11T18:04:22Z"
            source_channel_id = video_metadata.get("snippet", {}).get("channelId")
            if published_at_raw:
                try:
                    dt_obj = datetime.strptime(published_at_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    youtube_upload_date_string = dt_obj.strftime("%Y-%m-%d")
                    thread_date_prefix = dt_obj.strftime("%b %Y")
                    target_year_tag_name = f"{dt_obj.year} Archive"
                except ValueError as e:
                    print(f"Could not parse publishedAt '{published_at_raw}': {e}")
        else:
            print("YouTube Data API lookup returned no metadata - falling back to Discord post date.")

        # ✂️ SHORTS-ONLY CHANNEL GATE - this channel only earns a point/thread for videos
        # under 2 minutes long. Longer videos posted here get skipped (message stays, no delete).
        if msg.channel.id == CLIPS_CH_ID:
            duration_str = video_metadata.get("contentDetails", {}).get("duration") if video_metadata else None
            duration_seconds = parse_iso8601_duration_to_seconds(duration_str)
            if duration_seconds is None:
                await msg.channel.send(
                    f"⚠️ {msg.author.mention} couldn't verify this video's length, so it wasn't counted here. Try again in a moment.",
                    delete_after=10,
                )
                return
            if duration_seconds > 120:
                await msg.channel.send(
                    f"✂️ {msg.author.mention} this channel is for **Shorts only** (under 2 minutes) - this one's too long to count here. Post full-length clips in the lore channel instead!",
                    delete_after=10,
                )
                return

        # Video has cleared all gates (duplicate check + Shorts-length gate if applicable) -
        # NOW it's safe to mark it as processed so it can't be double-counted elsewhere.
        PROCESSED_VIDEOS_CACHE.add(video_id)

        # 🤖 AI NATURAL LANGUAGE NLP ENGINE: Scans full text to auto-tag matching active players based on keywords
        detected_player_tags = []
        for player_key, discord_ping_string in PLAYERS_DATABASE.items():
            if player_key in content_lower or player_key in actual_video_title.lower():
                if discord_ping_string not in detected_player_tags:
                    detected_player_tags.append(discord_ping_string)
        
        tagged_players_output_string = " ".join(detected_player_tags) if detected_player_tags else "*No matching streamer names identified inside description blocks*"

        # KEYWORD DESCRIPTION AUTO-CATEGORIZATION ENGINE
        combined_metadata_text = f"{content_lower} {actual_video_title.lower()}"
        
        if any(word in combined_metadata_text for word in GANG_WAR_WORDS): tag_label, target_tag_name, embed_color = "🔴 GANG WAR LOG", "🔴 Gang War", 0xff0000
        elif any(word in combined_metadata_text for word in HEIST_WORDS): tag_label, target_tag_name, embed_color = "💰 ACTIVE HEIST TIMELINE", "💰 Heist", 0x39ff14
        elif any(word in content_lower for word in COURT_WORDS): tag_label, target_tag_name, embed_color = "⚖️ COURT CASE RECORD", "⚖️ Court Case", 0x00f0ff
        else: tag_label, target_tag_name, embed_color = "📦 GENERAL LOG", "📦 General Log", 0x808080

        if uid not in USER_DATABASE: USER_DATABASE[uid] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
        member, roles_found = msg.author, [r.name for r in msg.author.roles]
        track_emoji_map = TRACK_EMOJI_MAP

        # 🎯 TAG-BASED TRACKING - the point now goes to whoever's NAME is actually mentioned/tagged
        # in the clip's message or title (community edits, highlight clips, etc. all count),
        # regardless of which YouTube channel actually uploaded the video.
        matched_track = None
        if "opie" in combined_metadata_text:
            matched_track = "Opie"
        elif "tray" in combined_metadata_text:
            matched_track = "Tray"
        elif "frenchie" in combined_metadata_text:
            matched_track = "Frenchie"

        # Fallback ONLY if nobody's name was actually mentioned anywhere: credit whoever's own
        # channel the video came from, so a plain reupload with no caption still counts for someone.
        if not matched_track and source_channel_id:
            matched_track = CHANNEL_ID_TO_STREAMER.get(source_channel_id)

        if matched_track:
            USER_DATABASE[uid][matched_track] += 1

        user_embed = discord.Embed(title=f"{tag_label} DETECTED", color=embed_color)
        user_embed.add_field(name="📅 YouTube Upload Date", value=f"📆 **{youtube_upload_date_string}**", inline=True)
        user_embed.add_field(name="👥 Auto-Tagged Players In Video", value=tagged_players_output_string, inline=False)
        user_embed.add_field(name="📥 Submission Link", value=video_url, inline=False)
        user_embed.add_field(name="👤 Filed By", value=msg.author.mention, inline=True)

        if video_thumbnail_url:
            user_embed.set_image(url=video_thumbnail_url) 

        if matched_track:
            track_count = USER_DATABASE[uid][matched_track]
            user_embed.add_field(
                name="📊 Score Progression",
                value=f"{track_emoji_map[matched_track]} {matched_track}: **{track_count} clips**",
                inline=True,
            )

            for milestone, rank_name in RANK_MAP[matched_track]:
                if track_count >= milestone:
                    if rank_name not in roles_found:
                        role = discord.utils.get(member.guild.roles, name=rank_name)
                        if role:
                            await member.add_roles(role)
                            await msg.channel.send(f"⚡ **RANK UP:** {member.mention} has leveled up to **{rank_name}**! 🟢")
                    break

        forum_channel = bot.get_channel(FORUM_CH_ID)
        if forum_channel and isinstance(forum_channel, discord.ForumChannel):
            applied_tags = [
                t for t in forum_channel.available_tags
                if t.name == target_tag_name or t.name == target_year_tag_name
                or (matched_track and matched_track.lower() in t.name.lower())
            ]

            clean_streamer_name = matched_track if matched_track else "Unknown"
            thread_title = f"[{thread_date_prefix}] {clean_streamer_name} | {actual_video_title[:45]}"

            thread_result = await forum_channel.create_thread(name=thread_title, embed=user_embed, applied_tags=applied_tags)

            # 🔥 Auto-react on the new thread's starter message so the archive feels alive
            try:
                starter_message = thread_result.message if hasattr(thread_result, "message") else None
                if starter_message:
                    await starter_message.add_reaction("🔥")
            except Exception as e:
                print(f"Auto-react on new thread failed: {e}")

            log_ch = bot.get_channel(LOG_ID)
            if log_ch:
                await log_ch.send(f"✅ **CHRONO CARD ACTIVE:** Successfully created archive thread: `{thread_title}` for member {msg.author.mention}. AI tags parsed.")

            if matched_track:
                record_recent_activity(matched_track, "community_clip", actual_video_title, video_url, youtube_upload_date_string)

            DAILY_STATS["clips_submitted"] += 1
            WEEKLY_STATS["clips_submitted"] += 1
            if matched_track:
                DAILY_STATS["track_points"][matched_track] += 1
                WEEKLY_STATS["track_points"][matched_track] += 1
            DAILY_STATS["contributor_counts"][uid] = DAILY_STATS["contributor_counts"].get(uid, 0) + 1
            WEEKLY_STATS["contributor_counts"][uid] = WEEKLY_STATS["contributor_counts"].get(uid, 0) + 1

            # 🎉 Check for a global milestone the moment it's crossed
            global TOTAL_CLIPS_ALL_TIME, LAST_CELEBRATED_MILESTONE
            TOTAL_CLIPS_ALL_TIME += 1
            if TOTAL_CLIPS_ALL_TIME // MILESTONE_STEP > LAST_CELEBRATED_MILESTONE // MILESTONE_STEP:
                LAST_CELEBRATED_MILESTONE = TOTAL_CLIPS_ALL_TIME
                milestone_number = (TOTAL_CLIPS_ALL_TIME // MILESTONE_STEP) * MILESTONE_STEP
                recap_ch = bot.get_channel(DAILY_RECAP_CH_ID)
                if recap_ch:
                    milestone_embed = discord.Embed(
                        title="🎉🚨 MILESTONE UNLOCKED 🚨🎉",
                        description=f"# {milestone_number} CLIPS ARCHIVED!\nThe Redline archive just hit a huge milestone. Massive shoutout to everyone keeping the timeline alive. 🏁",
                        color=0xffd700,
                    )
                    milestone_embed.set_footer(text="Every clip counts. Keep them coming!")
                    await recap_ch.send(content="@here", embed=milestone_embed)

    await bot.process_commands(msg)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN environment variable is not set. "
            "Set it before running the bot, e.g.:\n"
            "  export DISCORD_BOT_TOKEN='your-token-here'   (Linux/Mac)\n"
            "  setx DISCORD_BOT_TOKEN \"your-token-here\"      (Windows)\n"
            "or load it from a .env file with python-dotenv."
        )
    bot.run(DISCORD_TOKEN)
