import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime

# 📡 PRODUCTION CHANNEL ID MATRIX - HARDWIRED ROUTING
LOG_ID = 1546911999051694123 # #🛠️┃bot-terminal Logs ID
WELCOME_CH_ID = 1546898931458379907 # #📜┃rules Channel ID

# 🔒 HARDWIRED UNIFIED FORUM TIMELINE ENDPOINT
FORUM_CH_ID = 1547336797724479519 # Your #📋┃timeline-archive ID

intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# 🧠 THE KEYWORD BRAIN TABLES
GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta", "war", "cg", "gg", "pdw"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing", "heist", "casino", "yacht"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal", "trial", "case", "arrested"]

# 📊 TRACKING DATA ARCHIVE & SECURITY CACHE
USER_DATABASE = {}
SPAM_COOLDOWN = {}

@bot.event
async def on_ready():
    print("==================================================")
    print(f"🟢 LOGGED IN SUCCESS: {bot.user.name}")
    print("Redline Automated Chronological Forum Router Active...")
    print("==================================================")
    log_ch = bot.get_channel(LOG_ID)
    if log_ch:
        await log_ch.send("📟 **SYSTEM ONLINE:** Chronological Forum Timeline Router running successfully.")
    embed = discord.Embed(title=f"📊 {ctx.author.name}'s Track Progression Stats", description="Your verified milestone submissions.", color=0xe67e22)
    embed.add_field(name="🏎️ Opie (Driver Track)", value=f"Submissions: **{user_data['Opie']}**", inline=True)
    embed.add_field(name="💻 Tray (Hacker Track)", value=f"Submissions: **{user_data['Tray']}**", inline=True)
    embed.add_field(name="🟢 Frenchie (Spotter Track)", value=f"Submissions: **{user_data['Frenchie']}**", inline=True)
    embed.set_footer(text="Keep submitting clips to level up your character ranks!")
    await ctx.send(embed=embed)

# 🛠️ MULTI-POV SIMULATION TEST INTERFACE FOR FORUMS
@bot.command()
async def trigger_test(ctx, category_choice: str = "war"):
    if ctx.channel.id != LOG_ID:
        await ctx.send("❌ Error: Command must be executed inside your private terminal.")
        return

    choice_lower = category_choice.lower()
    if choice_lower in ["join", "welcome", "greet"]:
        await ctx.send("⚡ *Simulating join sequence event handler...*")
        await on_member_join(ctx.author)
        return
    elif "war" in choice_lower or "gang" in choice_lower:
        tag_label, target_tag_name, box_color = "🔴 GANG WAR LOG", "🔴 Gang War", 0xff0000
    elif "court" in choice_lower or "case" in choice_lower:
        tag_label, target_tag_name, box_color = "⚖️ COURT CASE RECORD", "⚖️ Court Case", 0x00f0ff
    else:
        tag_label, target_tag_name, box_color = "💰 ACTIVE HEIST TIMELINE", "💰 Heist", 0x39ff14

    await ctx.send(f"⚡ *Ingesting simulated notification... Routing to Forum...*")
    current_date_prefix = datetime.utcnow().strftime("%Y-%m-%d")
    epoch_now = int(datetime.utcnow().timestamp())
    discord_time_string = f"<t:{epoch_now}:F> (<t:{epoch_now}:R>)"
    
    embed = discord.Embed(title=f"{tag_label} DETECTED", color=box_color)
    embed.add_field(name="🎬 Track Perspective", value="[🏎️ Opie (Driver Track)](https://youtube.com)", inline=True)
    embed.add_field(name="🕒 Log Timestamp", value=discord_time_string, inline=True)
    embed.add_field(name="📥 Submission Link", value="https://youtube.com", inline=False)
    embed.add_field(name="👤 Filed By", value=ctx.author.mention, inline=True)
    
    forum_channel = bot.get_channel(FORUM_CH_ID)
    if forum_channel and isinstance(forum_channel, discord.ForumChannel):
        applied_tags = [t for t in forum_channel.available_tags if t.name == target_tag_name]
        thread_title = f"[{current_date_prefix}] {tag_label}"
        await forum_channel.create_thread(name=thread_title, embed=embed, applied_tags=applied_tags)
        await ctx.send("✅ Success! Simulated post created inside your forum channel.")

# 📋 CHRONOLOGICAL FORUM ROUTING EVENT FILTER
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    content_lower = msg.content.lower()
    
    if "youtube.com" in msg.content or "youtu.be" in msg.content:
        uid = msg.author.id
        current_time = msg.created_at.timestamp()
        if current_time - SPAM_COOLDOWN.get(uid, 0) < 5:
            await msg.channel.send(f"⚠️ {msg.author.mention}, slow down!", delete_after=3)
            try: await msg.delete()
            except: pass
            return
        SPAM_COOLDOWN[uid] = current_time

        if any(word in content_lower for word in GANG_WAR_WORDS):
            tag_label, target_tag_name, embed_color = "🔴 GANG WAR LOG", "🔴 Gang War", 0xff0000
        elif any(word in content_lower for word in HEIST_WORDS):
            tag_label, target_tag_name, embed_color = "💰 ACTIVE HEIST TIMELINE", "💰 Heist", 0x39ff14
        elif any(word in content_lower for word in COURT_WORDS):
            tag_label, target_tag_name, embed_color = "⚖️ COURT CASE RECORD", "⚖️ Court Case", 0x00f0ff
        else:
            tag_label, target_tag_name, embed_color = "📦 GENERAL LOG", "📦 General Log", 0x808080

        if uid not in USER_DATABASE: USER_DATABASE[uid] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
        member, roles_found = msg.author, [r.name for r in msg.author.roles]
        tracked_streamer, streamer_tag, track_key = None, "Unknown Operative", None
        
        if "Opie fan" in roles_found:
            USER_DATABASE[uid]["Opie"] += 1
            track_key, tracked_streamer = "Opie", ("Opie's Driver Track", USER_DATABASE[uid]["Opie"])
            streamer_tag = "[🏎️ Opie (Driver Track)](https://youtube.com)"
        elif "Tray fan" in roles_found:
            USER_DATABASE[uid]["Tray"] += 1
            track_key, tracked_streamer = "Tray", ("Tray Sander's Hacker Track", USER_DATABASE[uid]["Tray"])
            streamer_tag = "[💻 Tray (Hacker Track)](https://youtube.com)"
        elif "Frenchie fan" in roles_found:
            USER_DATABASE[uid]["Frenchie"] += 1
            track_key, tracked_streamer = "Frenchie", ("Frenchie's Spotter Track", USER_DATABASE[uid]["Frenchie"])
            streamer_tag = "[🟢 Frenchie (Spotter Track)](https://youtube.com)"

        current_date_prefix = msg.created_at.strftime("%Y-%m-%d")
        epoch_now = int(msg.created_at.timestamp())
        discord_time_string = f"<t:{epoch_now}:F> (<t:{epoch_now}:R>)"

        user_embed = discord.Embed(title=f"{tag_label} DETECTED", color=embed_color)
        user_embed.add_field(name="🎬 Track Perspective", value=streamer_tag, inline=True)
        user_embed.add_field(name="🕒 Log Timestamp", value=discord_time_string, inline=True)
        user_embed.add_field(name="📥 Submission Link", value=msg.content, inline=False)
        user_embed.add_field(name="👤 Filed By", value=msg.author.mention, inline=True)

        if tracked_streamer:
            track_title, track_count = tracked_streamer
            user_embed.add_field(name="📊 Score Progression", value=f"{track_title}: **{track_count} clips**", inline=True)
            
            rank_map = {