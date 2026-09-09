import discord
from discord.ext import commands, tasks
import asyncio

# 📡 HARDWIRED SYSTEM CONFIGURATIONS
FORUM_ID = 1547061966520979457 # #🗂️┃lore-timeline Text Channel ID
LOG_ID = 1546911999051694123 # #🛠️┃bot-terminal Logs ID
WELCOME_CH_ID = 1546898931458379907 # 🔒 YOUR HARDWIRED WELCOME/RULES CHANNEL ID

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
SPAM_COOLDOWN = {} # Anti-Spam time stamp log

@bot.event
async def on_ready():
    print("==================================================")
    print(f"🟢 LOGGED IN SUCCESS: {bot.user.name}")
    print("Redline Advanced Multi-Track Engine Active...")
    print("==================================================")
    
    log_ch = bot.get_channel(LOG_ID)
    if log_ch:
        await log_ch.send("📟 **SYSTEM ONLINE:** Production Auto-Tagging Matrix running successfully.")
    
    # Start the automated status loop activity shifter
    status_rotator.start()

# 🔄 UPGRADE 1: AUTOMATED LIVE STATUS ROTATOR LOOP
@tasks.loop(seconds=15)
async def status_rotator():
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name="🏎️ Opie's POV (Driver)"),
        discord.Activity(type=discord.ActivityType.watching, name="💻 Tray's POV (Hacker)"),
        discord.Activity(type=discord.ActivityType.watching, name="🟢 Frenchie's POV (Spotter)"),
        discord.Activity(type=discord.ActivityType.listening, name="!stats commands")
    ]
    for act in statuses:
        await bot.change_presence(activity=act)
        await asyncio.sleep(15)

# 🚀 UPGRADE 2: THE INSTANT JOIN WELCOME TEXT & ROLE ASSIGNER
@bot.event
async def on_member_join(member):
    # Automatically tag them with the base server permission role
    base_role = discord.utils.get(member.guild.roles, name="Member")
    if base_role:
        await member.add_roles(base_role)
        
    # Fire the gorgeous custom greeting card into your rules channel
    welcome_ch = bot.get_channel(WELCOME_CH_ID)
    if welcome_ch:
        embed = discord.Embed(
            title="🏁 WELCOME TO THE REDLINE MATRIX 🏁",
            description=f"Welcome {member.mention} to the ultimate roleplay tracking grid!",
            color=0xff0000
        )
        embed.add_field(
            name="📜 Server Information Center", 
            value=f"You have been granted the **Member** role! Read the guidelines right here in <#{WELCOME_CH_ID}> and drop clip links in <#{FORUM_ID}> to level up!", 
            inline=False
        )
        embed.set_footer(text=f"Redline operative #{len(member.guild.members)}")
        await welcome_ch.send(embed=embed)

# 📊 UPGRADE 3: LEADERBOARD STATS COMMAND
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

@bot.command()
async def trigger_test(ctx, category_choice: str):
    if ctx.channel.id != LOG_ID:
        await ctx.send("❌ Error: Command must be executed inside your private terminal.")
        return

    choice_lower = category_choice.lower()
    if "war" in choice_lower or "gang" in choice_lower:
        tag, box_color = "🔴 GANG WAR LOG", 0xff0000
    elif "court" in choice_lower or "case" in choice_lower:
        tag, box_color = "⚖️ COURT CASE RECORD", 0x00f0ff
    else:
        tag, box_color = "💰 ACTIVE HEIST TIMELINE", 0x39ff14

    await ctx.send(f"⚡ *Ingesting simulated YouTube notification payload... Routing to {tag}...*")
    
    embed = discord.Embed(
        title=f"{tag}: The Great Los Santos Operation",
        description="Chronological stream data compiled and matched via AI keyword scanning.",
        color=box_color
    )
    embed.add_field(name="🔴 Opie's POV (Driver)", value="[Watch Perspective ➔](https://youtube.com)\n*Status: Synced*", inline=False)
    embed.add_field(name="🔵 Tray Sander's POV (Hacker)", value="[Watch Perspective ➔](https://youtube.com)\n*Status: Synced*", inline=False)
    embed.add_field(name="🟢 Frenchie's POV (Lookout)", value="[Watch Perspective ➔](https://youtube.com)\n*Status: Synced*", inline=False)
    embed.set_footer(text=f"AI Data Hub Routing: {category_choice.upper()} | Block Verification: #101")
    
    target_channel = bot.get_channel(FORUM_ID)
    if target_channel:
        await target_channel.send(embed=embed)
        await ctx.send("✅ Success! Multi-POV tagged array streamed straight to your timeline wall.")

# 🏆 PROGRESSION EVALUATORS BY TRACK
def evaluate_opie_rank(count):
    if count >= 90: return "Wheelman"
    elif count >= 60: return "Getaway Driver"
    elif count >= 40: return "Street Racer"
    elif count >= 10: return "Grease Monkey"
    return None

def evaluate_tray_rank(count):
    if count >= 90: return "Master Hacker"
    elif count >= 60: return "Elite Hacker"
    elif count >= 40: return "Green Hat"
    elif count >= 10: return "Script Kiddie"
    return None

def evaluate_frenchie_rank(count):
    if count >= 90: return "Ghost Operator"
    elif count >= 60: return "Infiltrator"
    elif count >= 40: return "Scout"
    elif count >= 10: return "Lookout"
    return None

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    if msg.channel.id == FORUM_ID:
        content_lower = msg.content.lower()
        detected_tag, embed_color = "📦 GENERAL LOG", 0x808080
        
        if any(word in content_lower for word in GANG_WAR_WORDS):
            detected_tag, embed_color = "🔴 GANG WAR LOG", 0xff0000
        elif any(word in content_lower for word in HEIST_WORDS):
            detected_tag, embed_color = "💰 ACTIVE HEIST TIMELINE", 0x39ff14
        elif any(word in content_lower for word in COURT_WORDS):
            detected_tag, embed_color = "⚖️ COURT CASE RECORD", 0x00f0ff

        if "youtube.com" in msg.content or "youtu.be" in msg.content:
            uid = msg.author.id
            
            # 🛡️ UPGRADE 4: ANTI-SPAM COOLDOWN RATE WARDEN
            current_time = msg.created_at.timestamp()
            last_post = SPAM_COOLDOWN.get(uid, 0)
            if current_time - last_post < 5: # 5-second spam throttle gate
                await msg.channel.send(f"⚠️ {msg.author.mention}, please slow down! Tracking matrix entries require a 5s cool period.", delete_after=3)
                await msg.delete()
                return
            SPAM_COOLDOWN[uid] = current_time

            if uid not in USER_DATABASE:
                USER_DATABASE[uid] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
            
            member = msg.author
            roles_found = [r.name for r in member.roles]
            
            tracked_streamer = None
            r_name = None
            
            if "Opie fan" in roles_found:
                USER_DATABASE[uid]["Opie"] += 1
                s_count = USER_DATABASE[uid]["Opie"]
                tracked_streamer = ("Opie's Driver Track", s_count)
                r_name = evaluate_opie_rank(s_count)
            elif "Tray fan" in roles_found:
                USER_DATABASE[uid]["Tray"] += 1
                s_count = USER_DATABASE[uid]["Tray"]
                tracked_streamer = ("Tray Sander's Hacker Track", s_count)
                r_name = evaluate_tray_rank(s_count)
            elif "Frenchie fan" in roles_found:
                USER_DATABASE[uid]["Frenchie"] += 1
                s_count = USER_DATABASE[uid]["Frenchie"]
                tracked_streamer = ("Frenchie's Spotter Track", s_count)
                r_name = evaluate_frenchie_rank(s_count)

            user_embed = discord.Embed(
                title=f"{detected_tag} DETECTED", 
                description=f"Clip registered! Submission filed inside core matrix logs.", 
                color=embed_color
            )
            
            if tracked_streamer:
                track_title, track_count = tracked_streamer
                user_embed.add_field(name=f"📈 {track_title}", value=f"Total path submissions: **{track_count}**")
                
                if r_name and r_name not in roles_found:
                    role = discord.utils.get(member.guild.roles, name=r_name)
                    if role:
                        await member.add_roles(role)
                        await msg.channel.send(f"⚡ **TRACK OVERRIDE RANK UP:** {member.mention} has leveled up to **{r_name}** ({track_count} clips sent)! 🟢")

            await msg.channel.send(embed=user_embed)

    await bot.process_commands(msg)

bot.run('MTU0Njg2Mjc1MTA5ODQ3ODY1Mg.GKxOw6.QuDKh_y1nVPobt3GXYix9r81pofCvTOnf75CgY')