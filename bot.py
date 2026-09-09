import discord
from discord.ext import commands

FORUM_ID = 1546888429818613810 # #🗂️┃lore-timeline Forum Channel
LOG_ID = 1546911999051694123 # #🛠️┃bot-terminal Logs

intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal"]

USER_CLIPS = {}

@bot.event
async def on_ready():
    print("==================================================")
    print(f"🟢 LOGGED IN SUCCESS: {bot.user.name}")
    print("Redline Forum Thread Ingestion Engine Active...")
    print("==================================================")
    
    log_ch = bot.get_channel(LOG_ID)
    if log_ch:
        await log_ch.send("📟 **SYSTEM ONLINE:** Forum-Thread Engine running successfully.")

@bot.command()
async def trigger_test(ctx, category_choice: str):
    if ctx.channel.id != LOG_ID:
        await ctx.send("❌ Error: Command must be executed inside your private terminal.")
        return

    await ctx.send("⚡ *Ingesting simulated YouTube notification payload... Creating Forum Thread...*")
    
    embed = discord.Embed(
        title="🎬 UNLOCKED LOG: The Great Ocean Vault Incident",
        description="Chronological multi-perspective alignment matrix compiled successfully.",
        color=0x2f3136
    )
    embed.add_field(name="🔴 Opie's POV", value="[Watch Inbound Driver Perspective ➔](https://youtube.com)\n*Status: Synced VOD Log*", inline=False)
    embed.add_field(name="🔵 Tray Sander's POV", value="[Watch Core Hacker Perspective ➔](https://youtube.com)\n*Status: Synced VOD Log*", inline=False)
    embed.add_field(name="🟢 Frenchie's POV", value="[Watch Roof Lookout Perspective ➔](https://youtube.com)\n*Status: Synced VOD Log*", inline=False)
    embed.set_footer(text=f"AI Tag Routing: {category_choice.capitalize()} | Verified Database Block ID: 101")
    
    forum_channel = bot.get_channel(FORUM_ID)
    if forum_channel and isinstance(forum_channel, discord.ForumChannel):
        # 🚨 THE MASTER FIX: Automatically creates a brand-new Forum Thread Topic!
        await forum_channel.create_thread(
            name=f"🚨 SYNCED MULTI-POV: {category_choice.upper()} LOG #101",
            embed=embed
        )
        await ctx.send("✅ Success! New timeline tracking thread deployed straight to your public Forum list.")

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    if msg.channel.id == FORUM_ID:
        if "youtube.com" in msg.content or "youtu.be" in msg.content:
            uid = msg.author.id
            USER_CLIPS[uid] = USER_CLIPS.get(uid, 0) + 1
            count = USER_CLIPS[uid]
            member = msg.author
            
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

bot.run('MTUONjg2Mjc1MTA1ODQ3MDY1Mg.GWbtrg.62XoRH-qg7v12iB_bHNXST-yq0VTLbaG_zUeSY')
