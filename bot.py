import discord
from discord.ext import commands

# 🚨 CORE HARDCODED INFRASTRUCTURE IDENTIFIERS
FORUM_ID = 1546888429818613810  # #🗂️┃lore-timeline Forum / Clips channel
LOG_ID = 1546911999051694123    # #🛠️┃bot-terminal Logs

# 1. Platform Gateway Permissions Matrix
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True # Grants automation permission to update ranks
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. In-Game Keyword Brain Tables
GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal"]

# Central server clip database file counter
USER_CLIPS = {}

# 3. Diagnostic Ingestion Checklist
@bot.event
async def on_ready():
    print("==================================================")
    print(f"🟢 LOGGED IN SUCCESS: {bot.user.name}")
    print("Redline Automation & Leveling Engines Active...")
    print("==================================================")
    
    log_ch = bot.get_channel(LOG_ID)
    if log_ch:
        await log_ch.send("📟 **SYSTEM ONLINE:** Full Matrix Progression Engine running successfully.")

# 4. Automated Message Evaluation & Leveling Loop
@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    # Scans messages inside your tracking target zone
    if msg.channel.id == FORUM_ID:
        if "youtube.com" in msg.content or "youtu.be" in msg.content:
            uid = msg.author.id
            
            # Increments member data counter metric
            USER_CLIPS[uid] = USER_CLIPS.get(uid, 0) + 1
            count = USER_CLIPS[uid]
            member = msg.author
            
            # Hacker Path Leveling Logic
            if any(r.name == "Tray fan" for r in member.roles):
                r_name = None
                if count == 5: r_name = "Script Kiddie"
                elif count == 15: r_name = "Green Hat"
                elif count == 30: r_name = "Elite Hacker"
                elif count == 50: r_name = "Master Hacker"
                
                if r_name:
                    role = discord.utils.get(member.guild.roles, name=r_name)
                    if role:
                        await member.add_roles(role)
                        await msg.channel.send(f"⚡ **MATRIX RANK UP:** {member.mention} unlocked **{r_name}** ({count} clips sent)! 🟢")

    await bot.process_commands(msg)

# 5. Core Application Passport Credential Key
bot.run('MTUONjg2Mjc1MTA1ODQ3MDY1Mg.GWbtrg.62XoRH-qg7v12iB_bHNXST-yq0VTLbaG_zUeSY')
