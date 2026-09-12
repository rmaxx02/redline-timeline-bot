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
ANNOUNCE_CH_ID = 1546911191568490556  # ✅ live-clips channel

# 🔒 HARDWIRED UNIFIED FORUM TIMELINE ENDPOINT
FORUM_CH_ID = 1547336797724479519     # Your #📋┃timeline-archive ID

# 🔑 SECRETS - loaded from environment, never hardcoded
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# 🧠 THE KEYWORD BRAIN TABLES
GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta", "war", "cg", "gg", "pdw"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing", "heist", "casino", "yacht"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal", "trial", "case", "arrested"]

# 👥 AI PLAYER IDENTITIES DATABASE FOR AUTOMATIC DISCORD MEMBER TAGGING
PLAYERS_DATABASE = {
    "opie": "<@1547328181105860739>",      # Active tag link for Opie
    "tray": "<@1547328294838472884>",      # Active tag link for Tray Sanders
    "frenchie": "<@1547328384592519208>"   # Active tag link for Frenchie
}

# 📺 YOUTUBE CHANNEL IDS FOR LIVE/UPLOAD POLLING
# NOTE: these must be YouTube "Channel ID" values (start with "UC..."), not @handles.
# Find them via https://www.youtube.com/account_advanced while logged into that channel,
# or by viewing page source of the channel and searching for "channelId".
STREAMER_YOUTUBE_CHANNELS = {
    "Opie": "UC8Uy6FP4vuSA_pTRXvCJmPQ",
    "Tray": "UCa1R0o4KutQTmi6ObmngGRQ",
    "Frenchie": "UCcISgmobjhJQzMqXMnnzgeQ",
}

# 📊 TRACKING DATA ARCHIVE, ANTI-DUPLICATE MEMORY & COOLDOWNS
USER_DATABASE = {}
SPAM_COOLDOWN = {}
PROCESSED_VIDEOS_CACHE = set()  # Brain memory cache that permanently blocks duplicate video links

# 📺 LIVE/UPLOAD POLLING MEMORY (per streamer, so we don't re-announce the same video/stream)
LAST_ANNOUNCED_VIDEO_ID = {name: None for name in STREAMER_YOUTUBE_CHANNELS}
LAST_ANNOUNCED_LIVE_ID = {name: None for name in STREAMER_YOUTUBE_CHANNELS}

# 🧵 RECENT ACTIVITY MEMORY - keeps the last 8 known video/live events per streamer, newest first.
# (Not currently used for anything beyond bookkeeping - reserved for a future feature.)
RECENT_VIDEOS_LOG = {name: deque(maxlen=8) for name in STREAMER_YOUTUBE_CHANNELS}


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
    log_ch = bot.get_channel(LOG_ID)
    if log_ch:
        await log_ch.send("📟 **SYSTEM ONLINE:** Upgraded Chronological Forum Router running successfully.")
    status_rotator.start()
    youtube_activity_poller.start()

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
    announce_ch = bot.get_channel(ANNOUNCE_CH_ID)
    log_ch = bot.get_channel(LOG_ID)

    for streamer_name, channel_id in STREAMER_YOUTUBE_CHANNELS.items():
        if "UCXXXX" in channel_id or "UCYYYY" in channel_id or "UCZZZZ" in channel_id:
            # Placeholder channel ID not yet configured - skip silently.
            continue

        latest_video, live_video = fetch_latest_channel_activity(channel_id)

        # --- Live broadcast check ---
        if live_video:
            live_video_id = live_video["id"]["videoId"]
            if LAST_ANNOUNCED_LIVE_ID.get(streamer_name) != live_video_id:
                LAST_ANNOUNCED_LIVE_ID[streamer_name] = live_video_id
                title = live_video["snippet"]["title"]
                thumbnail = live_video["snippet"]["thumbnails"]["high"]["url"]
                video_url = f"https://www.youtube.com/watch?v={live_video_id}"

                if announce_ch:
                    streamer_mention = PLAYERS_DATABASE.get(streamer_name.lower(), "")
                    embed = discord.Embed(
                        title=f"🔴 {streamer_name} IS LIVE NOW",
                        description=title,
                        url=video_url,
                        color=0xff0000,
                    )
                    embed.set_image(url=thumbnail)
                    embed.set_footer(text="Redline Live Alert System")
                    alert_content = f"@here {streamer_mention}".strip()
                    await announce_ch.send(content=alert_content, embed=embed)

                if log_ch:
                    await log_ch.send(f"📡 **LIVE DETECTED:** {streamer_name} started streaming. `{video_url}`")

                record_recent_activity(streamer_name, "live", title, video_url,
                                        datetime.now(timezone.utc).strftime("%Y-%m-%d"))

        # --- New upload check ---
        if latest_video:
            video_id = latest_video["id"]["videoId"]
            if LAST_ANNOUNCED_VIDEO_ID.get(streamer_name) is None:
                # First run for this streamer: just record the current latest video,
                # don't announce it (avoids blasting old content on bot startup).
                LAST_ANNOUNCED_VIDEO_ID[streamer_name] = video_id
            elif LAST_ANNOUNCED_VIDEO_ID.get(streamer_name) != video_id:
                LAST_ANNOUNCED_VIDEO_ID[streamer_name] = video_id
                title = latest_video["snippet"]["title"]
                thumbnail = latest_video["snippet"]["thumbnails"]["high"]["url"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                published_at = latest_video["snippet"].get("publishedAt", "Unknown")

                if announce_ch:
                    streamer_mention = PLAYERS_DATABASE.get(streamer_name.lower(), "")
                    embed = discord.Embed(
                        title=f"📹 {streamer_name} JUST POSTED A NEW VIDEO",
                        description=title,
                        url=video_url,
                        color=0x39ff14,
                    )
                    embed.add_field(name="📅 Published", value=published_at)
                    embed.set_image(url=thumbnail)
                    embed.set_footer(text="Redline Upload Alert System")
                    await announce_ch.send(content=streamer_mention or None, embed=embed)

                if log_ch:
                    await log_ch.send(f"📡 **NEW UPLOAD DETECTED:** {streamer_name} posted a video. `{video_url}`")

                record_recent_activity(streamer_name, "upload", title, video_url, published_at[:10] if published_at != "Unknown" else "Unknown")


@youtube_activity_poller.before_loop
async def before_youtube_poller():
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
                "• Type `!stats` anywhere to view your personal scoreboard!\n\n"
                "👉 Tap the **🔮│get-roles** channel next to pick your streamer team!"
            ),
            color=0xff0000
        )
        embed.set_footer(text=f"Redline Operative #{len(member.guild.members)} | Grid Sync Active")
        await welcome_ch.send(embed=embed)

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

# 📋 CHRONOLOGICAL FORUM ROUTING FILTER WITH SPAM & DUPLICATE BLOCKING
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    content_lower = msg.content.lower()
    
    yt_match = re.search(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11}))', msg.content)
    if yt_match:
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
        if video_metadata:
            published_at_raw = video_metadata.get("snippet", {}).get("publishedAt")  # e.g. "2024-03-11T18:04:22Z"
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
        tracked_streamer, streamer_tag, track_key, target_streamer_tag_name = None, "Unknown Operative", None, None
        
        if "Opie fan" in roles_found:
            USER_DATABASE[uid]["Opie"] += 1
            track_key, tracked_streamer = "Opie", ("Opie's Driver Track", USER_DATABASE[uid]["Opie"])
            streamer_tag = "[🏎️ Opie (Driver Track)](https://www.youtube.com/@Opie)"
            target_streamer_tag_name = "🏎️ Opie"
        elif "Tray fan" in roles_found:
            USER_DATABASE[uid]["Tray"] += 1
            track_key, tracked_streamer = "Tray", ("Tray Sander's Hacker Track", USER_DATABASE[uid]["Tray"])
            streamer_tag = "[💻 Tray (Hacker Track)](https://www.youtube.com/@Tray)"
            target_streamer_tag_name = "💻 Tray"
        elif "Frenchie fan" in roles_found:
            USER_DATABASE[uid]["Frenchie"] += 1
            track_key, tracked_streamer = "Frenchie", ("Frenchie's Recon Track", USER_DATABASE[uid]["Frenchie"])
            streamer_tag = "[🚓 Frenchie (Recon Track)](https://www.youtube.com/@Frenchie)"
            target_streamer_tag_name = "🚓 Frenchie"

        user_embed = discord.Embed(title=f"{tag_label} DETECTED", color=embed_color)
        user_embed.add_field(name="🎬 Track Perspective", value=streamer_tag, inline=True)
        user_embed.add_field(name="📅 YouTube Upload Date", value=f"📆 **{youtube_upload_date_string}**", inline=True) 
        user_embed.add_field(name="👥 Auto-Tagged Players In Video", value=tagged_players_output_string, inline=False) 
        user_embed.add_field(name="📥 Submission Link", value=video_url, inline=False)
        user_embed.add_field(name="👤 Filed By", value=msg.author.mention, inline=True)

        if video_thumbnail_url:
            user_embed.set_image(url=video_thumbnail_url) 

        if tracked_streamer:
            track_title, track_count = tracked_streamer
            user_embed.add_field(name="📊 Score Progression", value=f"{track_title}: **{track_count} clips**", inline=True)
            
            rank_map = {
                "Opie": [(90, "Wheelman"), (60, "Getaway Driver"), (40, "Street Racer"), (10, "Grease Monkey")],
                "Tray": [(90, "Master Hacker"), (60, "Elite Hacker"), (40, "Green Hat"), (10, "Script Kiddie")],
                "Frenchie": [(90, "Ghost Operator"), (60, "Infiltrator"), (40, "Scout"), (10, "Lookout")]
            }
            for milestone, rank_name in rank_map[track_key]:
                if track_count >= milestone:
                    if rank_name not in roles_found:
                        role = discord.utils.get(member.guild.roles, name=rank_name)
                        if role:
                            await member.add_roles(role)
                            await msg.channel.send(f"⚡ **RANK UP:** {member.mention} has leveled up to **{rank_name}**! 🟢")
                    break

        forum_channel = bot.get_channel(FORUM_CH_ID)
        if forum_channel and isinstance(forum_channel, discord.ForumChannel):
            # Smart text scanners to automatically detect and auto-press matching streamer button tags based on keywords found
            detected_streamer_tag = None
            if "opie" in combined_metadata_text:
                detected_streamer_tag = "🏎️ Opie"
            elif "tray" in combined_metadata_text:
                detected_streamer_tag = "💻 Tray"
            elif "frenchie" in combined_metadata_text:
                detected_streamer_tag = "🚓 Frenchie"
            else:
                detected_streamer_tag = target_streamer_tag_name

            applied_tags = [
                t for t in forum_channel.available_tags 
                if t.name in [target_tag_name, detected_streamer_tag, target_year_tag_name]
            ]
            
            clean_streamer_name = target_streamer_tag_name.replace("🏎️ ", "").replace("💻 ", "").replace("🚓 ", "") if target_streamer_tag_name else "Unknown"
            thread_title = f"[{thread_date_prefix}] {clean_streamer_name} | {actual_video_title[:45]}"
            
            await forum_channel.create_thread(name=thread_title, embed=user_embed, applied_tags=applied_tags)
            
            log_ch = bot.get_channel(LOG_ID)
            if log_ch:
                await log_ch.send(f"✅ **CHRONO CARD ACTIVE:** Successfully created archive thread: `{thread_title}` for member {msg.author.mention}. AI tags parsed.")

            if target_streamer_tag_name:
                record_recent_activity(clean_streamer_name, "community_clip", actual_video_title, video_url, youtube_upload_date_string)

            try: await msg.delete()
            except: pass

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
