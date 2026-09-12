import os
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timezone
from collections import deque
import re
import urllib.request
import urllib.parse
import json

load_dotenv()  # reads variables from a .env file in the same folder, if present

# 📡 PRODUCTION CHANNEL ID MATRIX - HARDWIRED ROUTING
LOG_ID = 1546911999051694123          # #🛠️┃bot-terminal Logs ID
WELCOME_CH_ID = 1546898931458379907   # #📜┃rules Channel ID
LIVE_CH_ID = 1548192164037656607      # ✅ live streams ONLY get posted here
UPLOAD_CH_IDS = [1546911191568490556, 1547061966520979457]  # ✅ new uploads get posted to BOTH of these
LORE_CH_ID = 1547061966520979457      # ✅ your lore/timeline channel - watched for community links AND gets upload alerts
DAILY_RECAP_CH_ID = 1548174655934824539  # ✅ daily recap summary posts here every 24 hours

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
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            await interaction.response.send_message(
                f"⚠️ The **{role_name}** role doesn't exist on this server yet - ask an admin to create it.",
                ephemeral=True,
            )
            return
        member = interaction.user
        if role in member.roles:
            await interaction.response.send_message(f"You're already a **{role_name}**! ✅", ephemeral=True)
            return
        await member.add_roles(role)
        await interaction.response.send_message(f"🎉 You're locked in as a **{role_name}**! Welcome to the crew.", ephemeral=True)

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
    metadata for a single video, including its real publish date (snippet.publishedAt)
    and live broadcast status (liveStreamingDetails / snippet.liveBroadcastContent).
    Returns a dict or None if the lookup fails.
    """
    if not YOUTUBE_API_KEY:
        print("YOUTUBE_API_KEY not set - cannot fetch reliable publish date.")
        return None
    try:
        params = urllib.parse.urlencode({
            "part": "snippet,liveStreamingDetails",
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

                    if log_ch:
                        await log_ch.send(f"📡 **LIVE DETECTED:** {streamer_name} started streaming. `{video_url}`")

                    record_recent_activity(streamer_name, "live", title, video_url,
                                            datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                    DAILY_STATS["lives_today"].append((streamer_name, title, video_url))

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

                    if log_ch:
                        await log_ch.send(f"📡 **NEW UPLOAD DETECTED:** {streamer_name} posted a video. `{video_url}`")

                    record_recent_activity(streamer_name, "upload", title, video_url, published_at[:10] if published_at != "Unknown" else "Unknown")
                    DAILY_STATS["uploads_today"].append((streamer_name, title, video_url))


@youtube_activity_poller.before_loop
async def before_youtube_poller():
    await bot.wait_until_ready()


# 📅 DAILY RECAP - posts a summary of the day's activity every 24 hours, then resets the counters.
@tasks.loop(hours=24)
async def daily_recap():
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

    embed = discord.Embed(
        title="🌙 REDLINE DAILY RECAP",
        description=f"Here's everything that happened in the last 24 hours, <t:{int(datetime.now(timezone.utc).timestamp())}:R>.",
        color=0x9b59b6,
    )

    embed.add_field(
        name="🎬 Clips Submitted",
        value=(
            f"**{total_clips}** total clips logged today\n"
            f"🏎️ Opie: **{track_points['Opie']}** | 💻 Tray: **{track_points['Tray']}** | 🚓 Frenchie: **{track_points['Frenchie']}**"
        ) if total_clips > 0 else "No clips were submitted today.",
        inline=False,
    )

    if contributor_counts:
        top_uid = max(contributor_counts, key=contributor_counts.get)
        top_user = recap_ch.guild.get_member(top_uid) if recap_ch.guild else None
        top_name = top_user.mention if top_user else f"User {top_uid}"
        embed.add_field(
            name="👑 Top Contributor Today",
            value=f"{top_name} with **{contributor_counts[top_uid]}** clip(s) submitted!",
            inline=False,
        )

    if lives_today:
        lives_text = "\n".join(f"🔴 **{name}** — [{title[:60]}]({url})" for name, title, url in lives_today[:5])
        embed.add_field(name="📡 Live Streams Today", value=lives_text, inline=False)

    if uploads_today:
        uploads_text = "\n".join(f"📹 **{name}** — [{title[:60]}]({url})" for name, title, url in uploads_today[:5])
        embed.add_field(name="🆕 New Uploads Today", value=uploads_text, inline=False)

    if not lives_today and not uploads_today and total_clips == 0:
        embed.add_field(name="😴 Quiet Day", value="Nothing happened today - come back tomorrow!", inline=False)

    embed.set_footer(text="New recap posts every 24 hours. Keep the clips coming!")
    await recap_ch.send(embed=embed)

    reset_daily_stats()


@daily_recap.before_loop
async def before_daily_recap():
    await bot.wait_until_ready()


# 🚀 AUTOMATIC MEMBER JOIN GREETING & ROLE ASSIGNER
@bot.event
async def on_member_join(member):
    base_role = discord.utils.get(member.guild.roles, name="Member")
    if base_role: await member.add_roles(base_role)

    welcome_ch = bot.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        embed = discord.Embed(
            title="🏁 WELCOME TO THE REDLINE MATRIX TRACKER 🏁",
            description=(
                f"{member.mention} just joined the network!\n\n"
                "Welcome to the ultimate multi-POV roleplay tracking network!\n\n"
                "📌 **SERVER REQUISITE GUIDELINES:**\n"
                "1. **Keep Timelines Accurate:** Do not post fake timestamps or spoilers.\n"
                "2. **Respect the Streamers:** Toxicity or hate speech results in an instant ban.\n"
                "3. **Separate IC from OOC:** Keep real-world drama completely out of this server.\n"
                "4. **Follow Discord ToS:** No illegal links or malicious behavior.\n\n"
                "🏆 **PROGRESSION MILESTONE MARGINS:**\n"
                "• Opie Track: Grease Monkey ➔ Street Racer ➔ Getaway Driver ➔ Wheelman\n"
                "• Tray Track: Script Kiddie ➔ Green Hat ➔ Elite Hacker ➔ Master Hacker\n"
                "• Frenchie Track: Lookout ➔ Scout ➔ Infiltrator ➔ Ghost Operator\n\n"
                "📊 **UTILITY COMMAND PANEL:**\n"
                "• Type `!help` anywhere for a full rundown of everything the bot does.\n"
                "• Type `!stats` anywhere to view your personal scoreboard!\n\n"
                "👇 **Pick your team right now with one click below:**"
            ),
            color=0xff0000
        )
        embed.set_footer(text=f"Redline Operative #{len(member.guild.members)} | Grid Sync Active")
        await welcome_ch.send(embed=embed, view=TeamPickerView())

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
@bot.command()
async def stats(ctx, *, option: str = None):
    if option and option.lower() == "leaderboard":
        if not USER_DATABASE:
            await ctx.send("📊 **Scoreboard Empty:** No clips have been logged in the archive yet!")
            return
            
        leaderboard_data = []
        for uid, data in USER_DATABASE.items():
            total_clips = data.get("Opie", 0) + data.get("Tray", 0) + data.get("Frenchie", 0)
            user_obj = ctx.guild.get_member(uid) or await bot.fetch_user(uid)
            user_name = user_obj.name if user_obj else f"User {uid}"
            leaderboard_data.append((user_name, total_clips, data.get("Opie", 0), data.get("Tray", 0), data.get("Frenchie", 0)))
            
        leaderboard_data.sort(key=lambda x: x, reverse=True)
        
        embed = discord.Embed(title="🏆 REDLINE OVERALL CLIPS LEADERBOARD 🏆", description="The server's top verified chronological timeline contributors.", color=0xd4af37)
        for i, (name, total, opie_pts, tray_pts, frenchie_pts) in enumerate(leaderboard_data[:5], 1):
            embed.add_field(
                name=f"🥇 Rank #{i} | {name}", 
                value=f"Total Submissions: **{total}**\n🏎️ Opie: *{opie_pts}* | 💻 Tray: *{tray_pts}* | 🚓 Frenchie: *{frenchie_pts}*", 
                inline=False
            )
        embed.set_footer(text="Keep submitting clips to claim the top rank position on the dashboard!")
        await ctx.send(embed=embed)
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
            "`!stats` — shows YOUR OWN clip counts for Opie / Tray / Frenchie\n"
            "`!stats leaderboard` — shows the server's top 5 contributors overall"
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
            "**Opie Track:** Grease Monkey (10) ➔ Street Racer (40) ➔ Getaway Driver (60) ➔ Wheelman (90)\n"
            "**Tray Track:** Script Kiddie (10) ➔ Green Hat (40) ➔ Elite Hacker (60) ➔ Master Hacker (90)\n"
            "**Frenchie Track:** Lookout (10) ➔ Scout (40) ➔ Infiltrator (60) ➔ Ghost Operator (90)"
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

# 📋 CHRONOLOGICAL FORUM ROUTING FILTER WITH SPAM & DUPLICATE BLOCKING
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    content_lower = msg.content.lower()
    
    yt_match = re.search(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11}))', msg.content)
    if yt_match and msg.channel.id == LORE_CH_ID:
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

        # 🧠 ANTI-DUPLICATE BLOCK
        if video_id in PROCESSED_VIDEOS_CACHE:
            try: await msg.delete()
            except: pass
            await msg.channel.send(f"❌ {msg.author.mention} **Submission Blocked:** That specific video clip is already logged in the archive tracker dashboard!", delete_after=10)
            
            log_ch = bot.get_channel(LOG_ID)
            if log_ch:
                await log_ch.send(f"⚠️ **DUPLICATE INTERCEPTED:** {msg.author.mention} attempted to submit a duplicate link. Video ID: `{video_id}`. Message deleted automatically.")
            return
        PROCESSED_VIDEOS_CACHE.add(video_id)

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
        track_emoji_map = {"Opie": "🏎️", "Tray": "💻", "Frenchie": "🚓"}

        # 🎯 VIDEO-SOURCE TRACKING - the point goes to whichever streamer's own YouTube
        # channel this video actually came from, regardless of the poster's own roles.
        matched_track = CHANNEL_ID_TO_STREAMER.get(source_channel_id) if source_channel_id else None

        # Fallback if the API lookup didn't return a channel ID for some reason:
        # guess from keywords in the message/title so a submission still gets credited.
        if not matched_track:
            if "opie" in combined_metadata_text:
                matched_track = "Opie"
            elif "tray" in combined_metadata_text:
                matched_track = "Tray"
            elif "frenchie" in combined_metadata_text:
                matched_track = "Frenchie"

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

            rank_map = {
                "Opie": [(90, "Wheelman"), (60, "Getaway Driver"), (40, "Street Racer"), (10, "Grease Monkey")],
                "Tray": [(90, "Master Hacker"), (60, "Elite Hacker"), (40, "Green Hat"), (10, "Script Kiddie")],
                "Frenchie": [(90, "Ghost Operator"), (60, "Infiltrator"), (40, "Scout"), (10, "Lookout")]
            }
            for milestone, rank_name in rank_map[matched_track]:
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
                or (matched_track and t.name == f"{track_emoji_map[matched_track]} {matched_track}")
            ]

            clean_streamer_name = matched_track if matched_track else "Unknown"
            thread_title = f"[{thread_date_prefix}] {clean_streamer_name} | {actual_video_title[:45]}"
            
            await forum_channel.create_thread(name=thread_title, embed=user_embed, applied_tags=applied_tags)
            
            log_ch = bot.get_channel(LOG_ID)
            if log_ch:
                await log_ch.send(f"✅ **CHRONO CARD ACTIVE:** Successfully created archive thread: `{thread_title}` for member {msg.author.mention}. AI tags parsed.")

            if matched_track:
                record_recent_activity(matched_track, "community_clip", actual_video_title, video_url, youtube_upload_date_string)

            DAILY_STATS["clips_submitted"] += 1
            if matched_track:
                DAILY_STATS["track_points"][matched_track] += 1
            DAILY_STATS["contributor_counts"][uid] = DAILY_STATS["contributor_counts"].get(uid, 0) + 1

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
