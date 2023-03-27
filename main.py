import discord
from discord.ext import commands, tasks
from itertools import cycle
import yt_dlp
import random
import asyncio
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


intents = discord.Intents.default()
intents.message_content = True

status=cycle(["Sleeping", "At Virginia Tech", "Attending class", "New Jeans","Eating", "Doing Homework", "VS Code", ])

#-----------------------------------------------------------------------------
#Basic command

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    change_status.start()

@tasks.loop(seconds=3600)
async def change_status():
    await bot.change_presence(activity=discord.Game(next(status)))


@bot.command()
async def ping(ctx):
    await ctx.send("pong!")

@bot.event
async def on_command_error(ctx, err):
    if isinstance(err, commands.CommandNotFound):
        await ctx.send("Invalid Command Input")

@bot.command()
async def map(ctx):
    maps=("Haven","Split","Ascent", "Icebox", "Fracture", "Pearl", "Lotus")
    await ctx.send(maps[random.randrange(0,len(maps))])
@bot.command()
async def help(ctx):
    emb=discord.Embed(title="List of Commands", colour=discord.Colour.random())
    emb.add_field(name="ping", value="Will reply \"Pong!\". For latency check")
    emb.add_field(name="map", value="Randomly select valorant map", inline=False)
    emb.add_field(name="play", value="Add music on the PlayList and play it.\nIf music is already playing add it on the PlayList\nIf PlayList exist, add on the PlayList and play the first one on the list", inline=False)
    emb.add_field(name="show", value="Display PlayList", inline=False)
    emb.add_field(name="clear", value="Clear PlayList", inline=False)
    emb.add_field(name="skip", value="Skip to the next song in the list", inline=False)
    emb.add_field(name="stop", value="Stop playing and exit the voice channel", inline=False)
    emb.add_field(name="pasue", value="Pause music", inline=False)
    emb.add_field(name="resume", value="Resume music", inline=False)

    await ctx.send(embed=emb)



#--------------------------------------------------------------------------------
#Music portion

playlist=[]
titles=[]

ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0',
    }

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

#Stops the music and leave the voice channel
@bot.command()
async def stop(ctx):
    await ctx.voice_client.disconnect()



@bot.command()
async def embed(ctx, name, author, nail, message):
    embed1=discord.Embed(colour=discord.Colour.random(),description=message,title=name)
    embed1.set_author(name=author)
    embed1.set_thumbnail(url=nail)

    await ctx.send(embed=embed1)

async def play_music(ctx):
    await asyncio.sleep(0.5)
    if len(playlist) > 0 and not bot.voice_clients[0].is_playing():
        URL = playlist.pop()
        titles.pop()
        voice = bot.voice_clients[0]
        await voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_music(ctx), bot.loop))
    else:
        await asyncio.sleep(300)
        if not bot.voice_clients[0].is_playing() and not bot.voice_clients[0].is_paused():
            await ctx.send("Left voice channel due to inactivity")
            await ctx.voice_client.disconnect()

#Join the voice channel and play music
@bot.command()
async def play(ctx, *name):
    if len(name) ==0:
        return await ctx.send("Invalis command: Pleave enter the title of music after \"!play \"")

    query = " ".join(name)
    url = get_video_link(query)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        URL = info['formats'][9]['url']
        title=info["title"]
        author=info["channel"]
        nail=info["thumbnail"]
        titles.insert(0,title)
        playlist.insert(0,URL)


    #when bot is in the channel
    try:
        #when music is playing or paused
        if bot.voice_clients[0].is_playing() or bot.voice_clients[0].is_paused():
            return await embed(ctx,title,author,nail,"Added to PlayList")
        
        else:
            await embed(ctx,title,author,nail,"Now Playing")
            return await play_music(ctx)
            
    #when bot is not in the channel     
    except:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            if len(playlist)>1:
                await embed(ctx,title,author,nail,"Added to PlayList")
                await show(ctx)
                return await play_music(ctx)
            
            await embed(ctx,title,author,nail,"Now Playing")
            return await play_music(ctx)
            
        #when the author is not in the channel  
        else: 
            playlist.clear()
            titles.clear()
            return await ctx.send("Please join voice Channel")


@bot.command()
async def show(ctx):
    tmp=titles.copy()
    tmp.reverse()
    query = "\n".join(tmp)
    embed1=discord.Embed(colour=discord.Colour.random(),description=query+"",title=" Play List ")
    
    await ctx.send(embed=embed1)
    
@bot.command()
async def skip(ctx):
    ctx.voice_client.stop()

@bot.command()
async def pause(ctx):
    if not bot.voice_clients[0].is_paused():
        bot.voice_clients[0].pause()
    else:
         await ctx.send("Already paused")

@bot.command()
async def resume(ctx):
    if bot.voice_clients[0].is_paused():
        bot.voice_clients[0].resume()
    else:
        await ctx.send("Already playing")

@bot.command()
async def clear(ctx):
    playlist.clear()
    titles.clear()
    await ctx.send("PlayList cleared")


#---------------------------------------------------------------------------
# Helper function
api_key = "youtuve api key"
youtube = build('youtube', 'v3', developerKey=api_key)

def get_video_link(video_name):
    try:
        # Search for the video
        search_response = youtube.search().list(
            q=video_name,
            type='video',
            part='id,snippet',
            maxResults=1
        ).execute()

        # Extract the video ID and construct the video link
        video_id = search_response['items'][0]['id']['videoId']
        video_link = f"https://www.youtube.com/watch?v={video_id}"
        return video_link

    except HttpError as e:
        print(f"An error occurred: {e}")
        return None
    

 
bot.run('Discord key')
