import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
import re
import urllib.request
import json
LOG_ID = 1546911999051694123
WELCOME_CH_ID = 1546898931458379907
FORUM_CH_ID = 1547336797724479519
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta", "war", "cg", "gg", "pdw"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing", "heist", "casino", "yacht"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal", "trial", "case", "arrested"]
PLAYERS_DATABASE = {
"opie": "<@1547328181105860739>",
"tray": "<@1547328294838472884>",
"frenchie": "<@1547328384592519208>"
}
USER_DATABASE = {}
SPAM_COOLDOWN = {}
PROCESSED_VIDEOS_CACHE = set()
@bot.event
async def on_ready():
    print("==================================================")
    print(f"🟢 LOGGED IN SUCCESS: {bot.user.name}")
    print("Redline Duplicate-Proof Forum Router Active...")
    print("==================================================")
log_ch = bot.get_channel(LOG_ID)
if log_ch:
    await log_ch.send("📟 SYSTEM ONLINE: Upgraded Chronological Forum Router running successfully.")
status_rotator.start()
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
"📌 SERVER REQUISITE GUIDELINES:\n"
"1. Keep Timelines Accurate: Do not post fake timestamps or spoilers.\n"
"2. Respect the Streamers: Toxicity or hate speech results in an instant ban.\n"
"3. Separate IC from OOC: Keep real-world drama completely out of this server.\n"
"4. Follow Discord ToS: No illegal links or malicious behavior.\n\n"
"🏆 PROGRESSION MILESTONE MARGINS:\n"
"• Opie Track: Grease Monkey ➔ Street Racer ➔ Getaway Driver ➔ Wheelman\n"
"• Tray Track: Script Kiddie ➔ Green Hat ➔ Elite Hacker ➔ Master Hacker\n"
"• Frenchie Track: Lookout ➔ Scout ➔ Infiltrator ➔ Ghost Operator\n\n"
"📊 UTILITY COMMAND PANEL:\n"
"• Type !stats anywhere to view your personal scoreboard!\n\n"
"👉 Tap the 🔮│get-roles channel next to pick your streamer team!"
),
color=0xff0000
)
embed.set_footer(text=f"Redline Operative #{len(member.guild.members)} | Grid Sync Active")
await welcome_ch.send(embed=embed)
@bot.command()
async def stats(ctx, *, option: str = None):
if option and option.lower() == "leaderboard":
if not USER_DATABASE:
await ctx.send("📊 Scoreboard Empty: No clips have been logged in the archive yet!")
return
leaderboard_data = []
for uid, data in USER_DATABASE.items():
total_clips = data.get("Opie", 0) + data.get("Tray", 0) + data.get("Frenchie", 0)
user_obj = ctx.guild.get_member(uid) or await bot.fetch_user(uid)
user_name = user_obj.name if user_obj else f"User {uid}"
leaderboard_data.append((user_name, total_clips, data.get("Opie", 0), data.get("Tray", 0), data.get("Frenchie", 0)))
leaderboard_data.sort(key=lambda x: x[1], reverse=True)
embed = discord.Embed(title="🏆 REDLINE OVERALL CLIPS LEADERBOARD 🏆", description="The server's top verified chronological timeline contributors.", color=0xd4af37)
for i, (name, total, opie_pts, tray_pts, frenchie_pts) in enumerate(leaderboard_data[:5], 1):
embed.add_field(
name=f"🥇 Rank #{i} | {name}",
value=f"Total Submissions: {total}\n🏎️ Opie: {opie_pts} | 💻 Tray: {tray_pts} | 🚓 Frenchie: {frenchie_pts}",
inline=False
)
embed.set_footer(text="Keep submitting clips to claim the top rank position on the dashboard!")
await ctx.send(embed=embed)
return
uid = ctx.author.id
user_data = USER_DATABASE.get(uid, {"Opie": 0, "Tray": 0, "Frenchie": 0})
embed = discord.Embed(title=f"📊 {ctx.author.name}'s Track Progression Stats", description="Your verified milestone submissions.", color=0xe67e22)
embed.add_field(name="🏎️ Opie (Driver Track)", value=f"Submissions: {user_data['Opie']}", inline=True)
embed.add_field(name="💻 Tray (Hacker Track)", value=f"Submissions: {user_data['Tray']}", inline=True)
embed.add_field(name="🚓 Frenchie (Recon Track)", value=f"Submissions: {user_data['Frenchie']}", inline=True)
embed.set_footer(text="Type '!stats leaderboard' to see the server's top 5 contributors!")
await ctx.send(embed=embed)
@bot.event
async def on_message(msg):
if msg.author.bot: return
content_lower = msg.content.lower()
yt_match = re.search(r'(https?://(?:www.)?(?:youtube.com|youtu.be/)([a-zA-Z0-9_-]{11}))', msg.content)
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
if video_id in PROCESSED_VIDEOS_CACHE:
try: await msg.delete()
except: pass
await msg.channel.send(f"❌ {msg.author.mention} Submission Blocked: That specific video clip is already logged in the archive tracker dashboard!", delete_after=10)
log_ch = bot.get_channel(LOG_ID)
if log_ch:
await log_ch.send(f"⚠️ DUPLICATE INTERCEPTED: {msg.author.mention} attempted to submit a duplicate link. Video ID: {video_id}. Message deleted automatically.")
return
PROCESSED_VIDEOS_CACHE.add(video_id)
actual_video_title = "Unknown Clip Entry Description"
video_thumbnail_url = None
try:
params = urllib.parse.urlencode({'format': 'json', 'url': video_url})
oembed_url = f"youtube.com?{params}"
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
youtube_upload_date_string = msg.created_at.strftime("%Y-%m-%d")
thread_date_prefix = msg.created_at.strftime("%b %Y")
target_year_tag_name = msg.created_at.strftime("%Y Archive")
try:
html_req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(html_req, timeout=3) as html_res:
html_text = html_res.read().decode('utf-8', errors='ignore')
date_match = re.search(r'"uploadDate"\s*:\s*"([^"]+)"', html_text)
if date_match:
raw_date_str = date_match.group(1).split("T")[0]
youtube_upload_date_string = raw_date_str
dt_obj = datetime.strptime(raw_date_str, "%Y-%m-%d")
thread_date_prefix = dt_obj.strftime("%b %Y")
if dt_obj.year == datetime.now().year:
target_year_tag_name = f"{dt_obj.year} Current"
else:
target_year_tag_name = f"{dt_obj.year} Archive"
except Exception as e:
print(f"Upload date fetch failed: {e}")
detected_player_tags = []
for player_key, discord_ping_string in PLAYERS_DATABASE.items():
if player_key in content_lower or player_key in actual_video_title.lower():
if discord_ping_string not in detected_player_tags:
detected_player_tags.append(discord_ping_string)
tagged_players_output_string = " ".join(detected_player_tags) if detected_player_tags else "No matching streamer names identified inside description blocks"
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
streamer_tag = "🏎️ Opie (Driver Track)"
target_streamer_tag_name = "🏎️ Opie"
elif "Tray fan" in roles_found:
USER_DATABASE[uid]["Tray"] += 1
track_key, tracked_streamer = "Tray", ("Tray Sander's Hacker Track", USER_DATABASE[uid]["Tray"])
streamer_tag = "💻 Tray (Hacker Track)"
target_streamer_tag_name = "💻 Tray"
elif "Frenchie fan" in roles_found:
USER_DATABASE[uid]["Frenchie"] += 1
track_key, tracked_streamer = "Frenchie", ("Frenchie's Recon Track", USER_DATABASE[uid]["Frenchie"])
streamer_tag = "🚓 Frenchie (Recon Track)"
target_streamer_tag_name = "🚓 Frenchie"
user_embed = discord.Embed(title=f"{tag_label} DETECTED", color=embed_color)
user_embed.add_field(name="🎬 Track Perspective", value=streamer_tag, inline=True)
user_embed.add_field(name="📅 YouTube Upload Date", value=f"📆 {youtube_upload_date_string}", inline=True)
user_embed.add_field(name="👥 Auto-Tagged Players In Video", value=tagged_players_output_string, inline=False)
user_embed.add_field(name="📥 Submission Link", value=video_url, inline=False)
user_embed.add_field(name="👤 Filed By", value=msg.author.mention, inline=True)
if video_thumbnail_url:
user_embed.set_image(url=video_thumbnail_url)
if tracked_streamer:
track_title, track_count = tracked_streamer
user_embed.add_field(name="📊 Score Progression", value=f"{track_title}: {track_count} clips", inline=True)
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
await msg.channel.send(f"⚡ RANK UP: {member.mention} has leveled up to {rank_name}! 🟢")
break
forum_channel = bot.get_channel(FORUM_CH_ID)
if forum_channel and isinstance(forum_channel, discord.ForumChannel):
applied_tags = [
t for t in forum_channel.available_tags
if t.name in [target_tag_name, target_streamer_tag_name, target_year_tag_name]
]
clean_streamer_name = target_streamer_tag_name.replace("🏎️ ", "").replace("💻 ", "").replace("🚓 ", "") if target_streamer_tag_name else "Unknown"
thread_title = f"[{thread_date_prefix}] {clean_streamer_name} | {actual_video_title[:45]}"
await forum_channel.create_thread(name=thread_title, embed=user_embed, applied_tags=applied_tags)
log_ch = bot.get_channel(LOG_ID)
if log_ch:
await log_ch.send(f"✅ CHRONO CARD ACTIVE: Successfully created archive thread: {thread_title} for member {msg.author.mention}. AI tags parsed.")
try: await msg.delete()
except: pass
await bot.process_commands(msg)
bot.run('MTU0Njg2Mjc1MTA5ODQ3ODY1Mg.GKxOw6.QuDkH_y1nVPobt3GXYix9r81pofCvTOnf75CgY')
