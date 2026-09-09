import discord
from discord.ext import commands

<<<<<<< HEAD
FORUM_ID = 1546888429818613810 # #🗂️┃lore-timeline Forum Channel
LOG_ID = 1546911999051694123 # #🛠️┃bot-terminal Logs
=======
# 📡 HARDWIRED SYSTEM CONFIGURATIONS
FORUM_ID = 1547061966520979457 # #🗂️┃lore-timeline Text Channel ID
LOG_ID = 1546911999051694123 # #🛠️┃bot-terminal Logs ID
>>>>>>> 8bc9e40 (deploy production multi-track matrix)

intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

<<<<<<< HEAD
GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal"]

USER_CLIPS = {}
=======
# 🧠 THE KEYWORD BRAIN TABLES
GANG_WAR_WORDS = ["vagos", "ballas", "clapped", "turf", "shootout", "block", "chonny", "marabunta", "war", "cg", "gg", "pdw"]
HEIST_WORDS = ["thermite", "vault", "fleeca", "paleto", "getaway", "hack", "drill", "robbing", "heist", "casino", "yacht"]
COURT_WORDS = ["objection", "judge", "lawyer", "warrant", "subpoena", "guilty", "court", "appeal", "trial", "case", "arrested"]

# 📊 TRACKING DATA ARCHIVE
# Structure: { user_id: { "Opie": count, "Tray": count, "Frenchie": count } }
USER_DATABASE = {}
>>>>>>> 8bc9e40 (deploy production multi-track matrix)

@bot.event
async def on_ready():
    print("==================================================")
    print(f"🟢 LOGGED IN SUCCESS: {bot.user.name}")
<<<<<<< HEAD
    print("Redline Forum Thread Ingestion Engine Active...")
=======
    print("Redline Advanced Multi-Track Engine Active...")
>>>>>>> 8bc9e40 (deploy production multi-track matrix)
    print("==================================================")
    
    log_ch = bot.get_channel(LOG_ID)
    if log_ch:
<<<<<<< HEAD
        await log_ch.send("📟 **SYSTEM ONLINE:** Forum-Thread Engine running successfully.")
=======
        await log_ch.send("📟 **SYSTEM ONLINE:** Production Auto-Tagging Matrix running successfully.")
>>>>>>> 8bc9e40 (deploy production multi-track matrix)

@bot.command()
async def trigger_test(ctx, category_choice: str):
    if ctx.channel.id != LOG_ID:
        await ctx.send("❌ Error: Command must be executed inside your private terminal.")
        return

<<<<<<< HEAD
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
=======
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
>>>>>>> 8bc9e40 (deploy production multi-track matrix)

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
<<<<<<< HEAD
            USER_CLIPS[uid] = USER_CLIPS.get(uid, 0) + 1
            count = USER_CLIPS[uid]
=======
            if uid not in USER_DATABASE:
                USER_DATABASE[uid] = {"Opie": 0, "Tray": 0, "Frenchie": 0}
            
>>>>>>> 8bc9e40 (deploy production multi-track matrix)
            member = msg.author
            roles_found = [r.name for r in member.roles]
            
<<<<<<< HEAD
            if any(r.name == "Tray fan" for r in member.roles):
                r_name = None
                if count == 5: r_name = "Script Kiddie"
                elif count == 15: r_name = "Green Hat"
                elif count == 30: r_name = "Elite Hacker"
                elif count == 50: r_name = "Master Hacker"
=======
            tracked_streamer = None
            r_name = None
            
            # 🔄 CROSS-TRACK AUTO-ROUTING GATEWAY
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
>>>>>>> 8bc9e40 (deploy production multi-track matrix)
                
                # Check and award track roles automatically
                if r_name and r_name not in roles_found:
                    role = discord.utils.get(member.guild.roles, name=r_name)
                    if role:
                        await member.add_roles(role)
                        await msg.channel.send(f"⚡ **TRACK OVERRIDE RANK UP:** {member.mention} has leveled up to **{r_name}** ({track_count} clips sent)! 🟢")

            await msg.channel.send(embed=user_embed)

    await bot.process_commands(msg)

bot.run('MTU0Njg2Mjc1MTA5ODQ3ODY1Mg.GXQ0y5.UkhBP2WUSWj-8Cn0e_4SW3muJhOT_BoZqxL1E0')
