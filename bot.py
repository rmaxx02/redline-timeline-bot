import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime

# 📡 PRODUCTION CHANNEL ID MATRIX - HARDWIRED ROUTING
LOG_ID = 1546911999051694123 # #🛠️┃bot-terminal Logs ID
WELCOME_CH_ID = 1546898931458379907 # #📜┃rules Channel ID

# 🔒 HARDWIRED TOPIC CHANNEL ENDPOINTS
GANG_WAR_CH_ID = 1547328181105860739 # Target ID for #🔴┃gang-war-log
HEIST_CH_ID = 1547328294838472884 # Target ID for #💰┃heist-log
COURT_CH_ID = 1547328384592519208 # Target ID for #⚖️┃court-log
GENERAL_CH_ID = 1547329890292867204 # Target ID for #📦┃general-log

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
    print("Redline Automated Multi-Channel Router Active...")
    print("==================================================")
    
    log_ch = bot.get_channel(LOG_ID)
    if log_ch:
        await log_ch.send("📟 **SYSTEM ONLINE:** Multi-Channel Log Tagging Router running successfully.")
    status_rotator.start()

# 🔄 AUTOMATED LIVE STATUS ROTATOR LOOP
bot.status_index = 0
@tasks.loop(seconds=15)
async def status_rotator():
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name="🏎️ Opie's POV (Driver)"),
        discord.Activity(type=discord.ActivityType.watching, name="💻 Tray's POV (Hacker)"),
        discord.Activity(type=discord.ActivityType.watching, name="🟢 Frenchie's POV (Spotter)"),
        discord.Activity(type=discord.ActivityType.listening, name="!stats commands")
    ]
    await bot.change_presence(activity=statuses[bot.status_index % len(statuses)])
    bot.status_index += 1

# 🚀 AUTOMATIC MEMBER JOIN GREETING & ROLE ASSIGNER
@bot.event
async def on_member_join(member):
    base_role = discord.utils.get(member.guild.roles, name="Member")
    if base_role:
        await member.add_roles(base_role)
        
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

# 📊 LEADERBOARD STATS COMMAND
@bot.command()
async def stats(ctx):
    uid = ctx.author.id
    user_data = USER_DATABASE.get(uid, {"Opie": 0, "Tray": 0, "Frenchie": 0})
    
    embed = discord.Embed(
        title=f"📊 {ctx.author.name}'s Track Progression Stats",
        description="Your verified roleplay milestone submission records.",
        color=0xe67e22
    )
    embed.add_field(name="🏎️ Opie (Driver Track)", value=f"Submissions: **{user_data['Opie']}**", inline=True)
    embed.add_field(name="💻 Tray (Hacker Track)", value=f"Submissions: **{user_data['Tray']}**", inline=True)
    embed.add_field(name="🟢 Frenchie (Spotter Track)", value=f"Submissions: **{user_data['Frenchie']}**", inline=True)
    embed.set_footer(text="Keep submitting clips to level up your character ranks!")
    await ctx.send(embed=embed)

# 🛠️ SYSTEM ROUTING EVENT FILTER WITH TIMESTAMPS & STREAMER TAGS
@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    content_lower = msg.content.lower()
    
    if "youtube.com" in msg.content or "youtu.be" in msg.content:
        uid = msg.author.id
        
        # Anti-Spam Gate
        current_time = msg.created_at.timestamp()
        last_post = SPAM_COOLDOWN.get(uid, 0)
        if current_time - last_post < 5:
            await msg.channel.send(f"⚠️ {msg.author.mention}, please slow down!", delete_after=3)
            try:
                await msg.delete()
            except:
                pass
            return
        SPAM_COOLDOWN[uid] = current_time

        # Match tags and choose target endpoint
        if any(word in content_lower for word in GANG_WAR_WORDS):
            target_channel_id = GANG_WAR_CH_ID
            detected_tag, embed_color = "🔴 GANG WAR LOG", 0xff0000
        elif any(word in content_lower for word in HEIST_WORDS):
            target_channel_id = HEIST_CH_ID
            detected_tag, embed_color = "💰 ACTIVE HEIST TIMELINE", 0x39ff14
        elif any(word in content_lower for word in COURT_WORDS):
            target_channel_id = COURT_CH_ID
            detected_tag, embed_color = "⚖️ COURT CASE RECORD", 0x00f0ff
        else:
            target_channel_id = GENERAL_CH_ID
            detected_tag, embed_color = "📦 GENERAL LOG", 0x808080

        # Calculate Scores
        if uid not in USER_DATABASE:
            USER_DATABASE[uid] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
        
        member = msg.author
        roles_found = [r.name for r in member.roles]
        tracked_streamer = None
        
        # 🔗 HARDWIRED PROFILE LINKS & TAG MATRIX
        streamer_tag = "Unknown Operative"
        if "Opie fan" in roles_found:
            USER_DATABASE[uid]["Opie"] += 1
            tracked_streamer = ("Opie's Driver Track", USER_DATABASE[uid]["Opie"])
            streamer_tag = "[🏎️ Opie (Driver Track)](https://youtube.com)"
        elif "Tray fan" in roles_found:
            USER_DATABASE[uid]["Tray"] += 1
            tracked_streamer = ("Tray Sander's Hacker Track", USER_DATABASE[uid]["Tray"])
            streamer_tag = "[💻 Tray (Hacker Track)](https://youtube.com)"
        elif "Frenchie fan" in roles_found:
            USER_DATABASE[uid]["Frenchie"] += 1
            tracked_streamer = ("Frenchie's Spotter Track", USER_DATABASE[uid]["Frenchie"])
            streamer_tag = "[🟢 Frenchie (Spotter Track)](https://youtube.com)"

        # 📅 CREATE DISCORD LIVE TIMESTAMP STRINGS
        epoch_now = int(msg.created_at.timestamp())
        discord_time_string = f"<t:{epoch_now}:F> (<t:{epoch_now}:R>)"

        # Construct the beautiful verified log panel card
        user_embed = discord.Embed(
            title=f"{detected_tag} DETECTED", 
            color=embed_color
        )
        user_embed.add_field(name="🎬 Track Perspective", value=streamer_tag, inline=True)
        user_embed.add_field(name="🕒 Log Timestamp", value=discord_time_string, inline=True)
        user_embed.add_field(name="📥 Submission Link", value=msg.content, inline=False)
        user_embed.add_field(name="👤 Filed By", value=msg.author.mention, inline=True)

        if tracked_streamer:
            track_title, track_count = tracked_streamer
            user_embed.add_field(name="📊 Score Progression", value=f"{track_title}: **{track_count} clips**", inline=True)

        # 🚀 Send the structured card block straight to the specific topic room!
        destination_channel = bot.get_channel(target_channel_id)
        if destination_channel:
            await destination_channel.send(embed=user_embed)
            try:
                await msg.delete()
            except:
                pass

    await bot.process_commands(msg)

bot.run('MTU0Njg2Mjc1MTA5ODQ3ODY1Mg.GKxOw6.QuDKh_y1nVPobt3GXYix9r81pofCvTOnf75CgY')