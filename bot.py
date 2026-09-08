import discord
from discord.ext import commands

# CHANNELS AUTOMATICALLY LINKED BY YOUR CORE IDs
FORUM_CHANNEL_ID = 1546888429818613810  # #🗂️┃lore-timeline Forum
LOG_CHANNEL_ID = 1546911999051694123    # #🛠️┃bot-terminal Logs

# 1. Connection Framework Setup
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True # Required to assign roles automatically
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. In-Game Keyword Brain Routing Array
GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal"]

# Hidden clip tracker database
USER_CLIP_COUNTS = {}

# 3. Diagnostic Initialization Routine
@bot.event
async def on_ready():
    print("==================================================")
    print(f"🟢 SUCCESS: {bot.user.name} IS NOW LIVE ON CLOUD!")
    print("Leveling engine active. Monitoring #live-clips updates...")
    print("==================================================")
    
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(
            f"📟 **SYSTEM ONLINE:** Redline Ingestion Engine successfully logged onto cloud server.\n"
            f"Hacker Progression Engine is fully tracking roles."
        )

# 4. Automated Message Scanner & Clip Leveler
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Checks if a clip link is dropped into your logging channel
    if message.channel.id == FORUM_CHANNEL_ID:
        if "youtube.com" in message.content or "youtu.be" in message.content:
            user_id = message.author.id
            USER_CLIP_COUNTS[user_id] = USER_CLIP_COUNTS.get(user_id, 0) + 1
            clips_sent = USER_CLIP_COUNTS[user_id]
            
            # Grabs the user's current roles inside your server
            member = message.author
            
            # Logic rules to promote Tray Sander fans to the Hacker ranks
            if any(role.name == "Tray fan" for role in member.roles):
                role_to_add = None
                
                if clips_sent == 5:
                    role_to_add = discord.utils.get(member.guild.roles, name="Script Kiddie")
                elif clips_sent == 15:
                    role_to_add = discord.utils.get(member.guild.roles, name="Green Hat")
                elif clips_sent == 30:
                    role_to_add = discord.utils.get(member.guild.roles, name="Elite Hacker")
                elif clips_sent == 50:
                    role_to_add = discord.utils.get(member.guild.roles, name="Master Hacker")
                
                if role_to_add:
                    await member.add_roles(role_to_add)
                    await message.channel.send(
                        f"⚡ **MATRIX RANK UP:** {member.mention} has submitted {clips_sent} clips! "
                        f"They have been automatically promoted to the **{role_to_add.name}** tier! 🟢"
                    )

    await bot.process_commands(message)

# Core credential passport token matching your developer profile
bot.run('MTUONjg2Mjc1MTA1ODQ3MDY1Mg.GWbtrg.62XoRH-qg7v12iB_bHNXST-yq0VTLbaG_zUeSY')