import discord
from discord.ext import commands, tasks
from itertools import cycle
import yt_dlp
import random
import asyncio
import queue
from googleapiclient.discovery import build


intents = discord.Intents.default()
intents.message_content = True

status=cycle(["Sleeping", "At Virginia Tech", "Attending class", "New Jeans","Eating", "Doing Homework", "VS Code", ])
youtube = build('youtube', 'v3', developerKey="your_api_key")
playlist=queue.Queue()
titles=queue.Queue()
channel=[]
videoCount=[]
cTitle=[]
dChannel=None


#-----------------------------------------------------------------------------
#Basic command

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    change_status.start()
    track_channel.start()

@tasks.loop(seconds=3600)
async def change_status():
    await bot.change_presence(activity=discord.Game(next(status)))

@tasks.loop(seconds=300)
async def track_channel():
    if len(channel) == 0:
        return
    for i in range(len(channel)):
        search_response = youtube.channels().list(
            id=channel[i],
            part = 'statistics',
            maxResults=1
        ).execute()
        video_count = search_response['items'][0]['statistics']['videoCount']

        if video_count > videoCount[i]:
             videoCount[i]=video_count
             search_response2 = youtube.search().list(
                channelId=channel[i],
                type='video',
                part='id',
                order='date',
                maxResults=1
            ).execute()
             video_id = search_response2['items'][0]['id']['videoId']
             await dChannel.send(f"https://www.youtube.com/watch?v={video_id}")


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
    emb.add_field(name="pplay", value="Same as 'play' but plays with lower audio quality. Will play most of the songs on youutbe", inline=False)
    emb.add_field(name="show", value="Display PlayList", inline=False)
    emb.add_field(name="clear", value="Clear PlayList", inline=False)
    emb.add_field(name="skip", value="Skip to the next song in the list", inline=False)
    emb.add_field(name="stop", value="Stop playing and exit the voice channel", inline=False)
    emb.add_field(name="pasue", value="Pause music", inline=False)
    emb.add_field(name="resume", value="Resume music", inline=False)
    emb.add_field(name="track", value="Keeps track of Youtube channel and notify when new video is uploaded", inline=False)
    emb.add_field(name="delete", value="Delete the given channel from the tracking list", inline=False)
    emb.add_field(name="tracking", value="Display list of Youtube Channels being tracked", inline=False)

    await ctx.send(embed=emb)

#--------------------------------------------------------------------------------
#Music portion

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


async def embed(ctx, name, author, nail, message):
    embed1=discord.Embed(colour=discord.Colour.random(),description=message,title=name)
    embed1.set_author(name=author)
    embed1.set_thumbnail(url=nail)

    await ctx.send(embed=embed1)

async def play_music(ctx):
    await asyncio.sleep(1)
    if not playlist.empty() and not bot.voice_clients[0].is_playing():
        URL = playlist.get()
        titles.get()
        voice = bot.voice_clients[0]
        await voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_music(ctx), bot.loop))
    else:
        await asyncio.sleep(300)
        if not bot.voice_clients[0].is_playing() and not bot.voice_clients[0].is_paused():
            await ctx.send("Left voice channel due to inactivity")
            await ctx.voice_client.disconnect()

#Join the voice channel and play music
@bot.command()
async def pplay(ctx, *name):
    if len(name) ==0:
        return await ctx.send("Invalid command: Please enter the title of music after \"!pplay \"")

    query = " ".join(name)
    url = get_video_link(query)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        URL = info['formats'][4]['url']
        title=info["title"]
        author=info["channel"]
        nail=info["thumbnail"]
        titles.put(title)
        playlist.put(URL)


    #when bot is in the channel
    try:
        #when music is playing or paused
        if bot.voice_clients[0].is_playing() or bot.voice_clients[0].is_paused():
            return await embed(ctx,title,"Added to PlayList",nail,author)
        
        else:
            await embed(ctx,title,"Now Playing",nail,author)
            return await play_music(ctx)
            
    #when bot is not in the channel     
    except:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            #If PlayList exists
            if playlist.empty():
                await embed(ctx,title,"Added to PlayList",nail,author)
                await show(ctx)
                return await play_music(ctx)
            await asyncio.sleep(1)
            await embed(ctx,title,"Now Playing",nail,author)
            return await play_music(ctx)
            
        #when the author is not in the channel  
        else: 
            playlist.queue.clear()
            titles.qeueue.clear()
            return await ctx.send("Please join voice Channel")

#Join the voice channel and play music
@bot.command()
async def play(ctx, *name):
    if len(name) ==0:
        return await ctx.send("Invalid command: Please enter the title of music after \"!play \"")

    query = " ".join(name)
    url = get_video_link(query)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        URL = info['formats'][9]['url']
        title=info["title"]
        author=info["channel"]
        nail=info["thumbnail"]
        titles.put(title)
        playlist.put(URL)


    #when bot is in the channel
    try:
        #when music is playing or paused
        if bot.voice_clients[0].is_playing() or bot.voice_clients[0].is_paused():
            return await embed(ctx,title,"Added to PlayList",nail,author)
        
        else:
            await embed(ctx,title,"Now Playing",nail,author)
            return await play_music(ctx)
            
    #when bot is not in the channel     
    except:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            #If PlayList exists
            if playlist.empty():
                await embed(ctx,title,"Added to PlayList",nail,author)
                await show(ctx)
                return await play_music(ctx)
            await asyncio.sleep(1)
            await embed(ctx,title,"Now Playing",nail,author)
            return await play_music(ctx)
            
        #when the author is not in the channel  
        else: 
            playlist.queue.clear()
            titles.queue.clear()
            return await ctx.send("Please join voice Channel")


@bot.command()
async def show(ctx):
    query = "\n".join(titles.queue)
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
    playlist.queue.clear()
    titles.queue.clear()
    await ctx.send("PlayList cleared")

@bot.command()
async def track(ctx, *cName):
    if len(cName) ==0:
        return await ctx.send("Invalid command: Please enter the channel name after \"!track \"")

    query = " ".join(cName)
    search_response = youtube.search().list(
            q=query,
            type='channel',
            part='id',
            maxResults=1
        ).execute()

    channel_id = search_response['items'][0]['id']['channelId']

    search_response2 = youtube.channels().list(
            id=channel_id,
            part = 'statistics,snippet',
            maxResults=1
        ).execute()
    video_count = search_response2['items'][0]['statistics']['videoCount']

    channel.append(channel_id)
    videoCount.append(video_count)
    global dChannel
    dChannel = ctx.channel

    name = search_response2['items'][0]['snippet']['title']
    custom = search_response2['items'][0]['snippet']['customUrl']
    tumbnail = search_response2['items'][0]['snippet']['thumbnails']['medium']['url']
    description = search_response2['items'][0]['snippet']['description']
    cTitle.append(name + "("+custom+")")
    return await embed(ctx, name + "("+custom+")", "Now tracking", tumbnail, description)

@bot.command()
async def delete(ctx, *cName):
    if len(cName) ==0:
        return await ctx.send("Invalid command: Please enter the channel name after \"!delete \"")
    
    query = " ".join(cName)

    search_response = youtube.search().list(
            q=query,
            type='channel',
            part='id',
            maxResults=1
        ).execute()

    channel_id = search_response['items'][0]['id']['channelId']

    if channel.count(channel_id) == 0:
        return await ctx.send(f"Channel: {query} is not being tracked")
    else:
        i = channel.index(channel_id)
        channel.pop(i)
        videoCount.pop(i)
        return await ctx.send(f"Channel: {cTitle.pop(i)} is no longer being tracked")
    
@bot.command()
async def tracking(ctx):
    query = "\n".join(cTitle)
    embed1=discord.Embed(colour=discord.Colour.random(),description=query+"",title=" Tracking List ")
    
    await ctx.send(embed=embed1)


#---------------------------------------------------------------------------
# Helper function

def get_video_link(video_name):
        # Search for the video/
        search_response = youtube.search().list(
            q=video_name,
            type='video',
            part='id',
            maxResults=1
        ).execute()

        # Extract the video ID and construct the video link
        video_id = search_response['items'][0]['id']['videoId']
        video_link = f"https://www.youtube.com/watch?v={video_id}"
        return video_link
    

 
bot.run('bot_key')
