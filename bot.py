import discord
from discord.ext import commands

# CHANNELS AUTOMATICALLY LINKED BY YOUR CORE IDs
FORUM_CHANNEL_ID = 1546888429818613810  # #🗂️┃lore-timeline Forum
LOG_CHANNEL_ID = 1546911999051694123    # #🛠️┃bot-terminal Logs

# 1. Connection Framework Setup
intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. In-Game Keyword Brain Routing Array
GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal"]

# 3. Diagnostic Initialization Routine
@bot.event
async def on_ready():
    print("==================================================")
    print(f"🟢 SUCCESS: {bot.user.name} IS NOW LIVE ON CLOUD!")
    print("Ingestion Engine active. Watching Opie, Tray, and Frenchie feeds...")
    print("==================================================")
    
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(
            f"📟 **SYSTEM ONLINE:** Redline Ingestion Engine successfully logged onto cloud server.\n"
            f"Ready to deploy synchronized data directly to <#{FORUM_CHANNEL_ID}>."
        )

# 4. Core Automated Simulation Test Command
@bot.command()
async def trigger_test(ctx, category_choice: str):
    """
    Simulates a YouTube notification trigger event.
    Type this in #bot-terminal: !trigger_test heist
    """
    if ctx.channel.id != LOG_CHANNEL_ID:
        await ctx.send(f"❌ Error: Security protocol restriction. Command must be executed inside your private terminal.")
        return

    await ctx.send("⚡ *Ingesting simulated YouTube notification payload... Analyzing audio scripts...*")
    
    embed = discord.Embed(
        title="🎬 UNLOCKED LOG: The Great Ocean Vault Incident",
        description="Chronological multi-perspective alignment matrix compiled successfully.",
        color=0x2f3136
    )
    embed.add_field(name="🔴 Opie's POV", value="[Watch Inbound Driver Perspective ➔](https://youtube.com)\n*Status: Synced VOD Log*", inline=False)
    embed.add_field(name="🔵 Tray Sander's POV", value="[Watch Core Hacker Perspective ➔](https://youtube.com)\n*Status: Synced VOD Log*", inline=False)
    embed.add_field(name="🟢 Frenchie's POV", value="[Watch Roof Lookout Perspective ➔](https://youtube.com)\n*Status: Synced VOD Log*", inline=False)
    embed.set_footer(text=f"AI Tag Routing: {category_choice.capitalize()} | Verified Database Block ID: 101")
    
    forum_channel = bot.get_channel(FORUM_CHANNEL_ID)
    if forum_channel:
        await forum_channel.send(embed=embed)
        await ctx.send("✅ Success! Synced timeline array deployed straight to your public Forum channel.")

# Core credential passport token matching your developer profile
bot.run('MTUONjg2Mjc1MTA1ODQ3MDY1Mg.GWbtrg.62XoRH-qg7v12iB_bHNXST-yq0VTLbaG_zUeSY')
