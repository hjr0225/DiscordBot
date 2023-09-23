import discord
from discord.ext import commands, tasks
from itertools import cycle
import yt_dlp
import asyncio
from collections import deque
from googleapiclient.discovery import build


status=cycle(["IZ*ONE", "NewJeans", "IVE", "fromis_9","aespa", "LE SSERAFIM", "STAYC", ])
youtube = build('youtube', 'v3', developerKey="Youtube-API-Key")
playlist=deque()
channels = {}

dChannel=None


bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    await bot.tree.sync()
    change_status.start()
    track_channel.start()

@tasks.loop(seconds=3600)
async def change_status():
    await bot.change_presence(activity=discord.Activity(type =discord.ActivityType.listening, name=next(status)))

@tasks.loop(seconds=600)
async def track_channel():
    if not channels:
        return
    for channel in channels.items():
        search_response = youtube.channels().list(
            id=channel[0],
            part = 'statistics',
            maxResults=1
        ).execute()
        video_count = search_response['items'][0]['statistics']['videoCount']

        if video_count > channel[2]:
            search_response2 = youtube.search().list(
                channelId=channel[0],
                type='video',
                part='id',
                order='date',
                maxResults=1
            ).execute()
            video_id = search_response2['items'][0]['id']['videoId']
            await dChannel.send(f"https://www.youtube.com/watch?v={video_id}")
        
        channel[2]=video_count
        



@bot.tree.command(name = "ping", description="Will reply \"Pong!\". For latency check")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong!")

@bot.event
async def on_command_error(interaction: discord.Interaction, err):
        await interaction.channel.send(f"An error occurred: {err}")

ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'extractaudio': True,
        'quiet': True,
        'source_address': '0.0.0.0'
    }

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

async def play_music(interaction):
    await asyncio.sleep(1)
    if len(playlist) != 0 and not bot.voice_clients[0].is_playing():
        URL = playlist.popleft()[0]
        bot.voice_clients[0].play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_music(interaction), bot.loop))
    
    else:
        await asyncio.sleep(300)
        
        if not bot.voice_clients[0].is_playing() and not bot.voice_clients[0].is_paused():
            await interaction.channel.send("Left voice channel due to inactivity")
            await bot.voice_clients[0].disconnect()



#Join the voice channel and play music
@bot.tree.command(name = "play", description="Play music, Add to the playlist")
async def play(interaction: discord.Interaction, title:str):
    await interaction.response.defer(thinking = True)

    url = get_video_link(title)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        URL = info['url']
        title=info["title"]
        author=info["channel"]
        nail=info["thumbnail"]
        playlist.append((URL, title))

    try:
        #when music is playing or paused
        voice = bot.voice_clients[0]
        if voice.is_playing() or voice.is_paused():
            return await embed(interaction,title,"Added to PlayList",nail,author)
        
        else:
            await embed(interaction,title,"Now Playing",nail,author)
            return await play_music(interaction)
    except:

        if interaction.user.voice is not None:
            await interaction.user.voice.channel.connect()
            await embed(interaction,title,"Now Playing",nail,author)
            return await play_music(interaction)
            
        #when the author is not in the channel  
        else: 
            playlist.clear()
            return await interaction.followup.send("Please join voice Channel")


@bot.tree.command(name = "show", description="Display PlayList")
async def show(interaction: discord.Interaction):
    query = "\n".join(title[1] for title in playlist)
    
    await interaction.response.send_message(embed=discord.Embed(colour=discord.Colour.random(),description=query+"",title=" Play List "))

@bot.tree.command(name = "stop", description="Stop playing, clear PlayList and exit the voice channel")
async def stop(interaction: discord.Interaction):
    playlist.clear()
    await interaction.response.send_message("Exiting voice channel, PlayList is cleared")
    await bot.voice_clients[0].disconnect()

@bot.tree.command(name = "skip", description="Skip music")
async def skip(interaction: discord.Interaction):
    await interaction.response.send_message("Skipping...")
    interaction.client.voice_clients[0].stop()

@bot.tree.command(name = "pause", description="Pause music")
async def pause(interaction: discord.Interaction):
    if not bot.voice_clients[0].is_paused():
        await interaction.response.send_message("Paused")
        bot.voice_clients[0].pause()
    else:
        await interaction.response.send_message("Already paused")

@bot.tree.command(name = "resume", description="Resume music")
async def resume(interaction: discord.Interaction):
    if bot.voice_clients[0].is_paused():
        await interaction.response.send_message("Resuming...")
        bot.voice_clients[0].resume()
    else:
        await interaction.response.send_message("Already playing")

@bot.tree.command(name = "remove", description="Remove a song from PlayList from latest")
async def remove(interaction: discord.Interaction):
    if not playlist:
        await interaction.response.send_message("PlayList is empty")
    else:
        await interaction.response.send_message(f"{playlist.pop()[1]} has been removed from the PlayList")

@bot.tree.command(name = "clear", description="Clear PlayList")
async def clear(interaction: discord.Interaction):
    playlist.clear()
    await interaction.response.send_message("PlayList cleared")

async def embed(interaction, name, author, nail, message):
    embed1=discord.Embed(colour=discord.Colour.random(),description=message,title=name)
    embed1.set_author(name=author)
    embed1.set_thumbnail(url=nail)

    await interaction.followup.send(embed=embed1)


@bot.tree.command(name = "track", description="Tracks YouTube channel. Notify when new video is uploaded")
async def track(interaction: discord.Interaction, name:str):
    await interaction.response.defer(thinking = True)

    search_response = youtube.search().list(
            q=name,
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
    name = search_response2['items'][0]['snippet']['title']
    custom = search_response2['items'][0]['snippet']['customUrl']
    tumbnail = search_response2['items'][0]['snippet']['thumbnails']['medium']['url']
    description = search_response2['items'][0]['snippet']['description']
    
    channels[channel_id] = [video_count, name + "("+custom+")"]
    return await embed(interaction, name + "("+custom+")", "Now tracking", tumbnail, description)

@bot.tree.command(name = "delete", description="Delete YouTube channel from tracking list")
async def delete(interaction: discord.Interaction, name:str):  

    search_response = youtube.search().list(
            q=name,
            type='channel',
            part='id',
            maxResults=1
        ).execute()

    channel_id = search_response['items'][0]['id']['channelId']

    if channel_id not in channels:
        return await interaction.response.send_message(f"Channel: {name} is not being tracked")
    else:
        title = channels[channel_id][0]
        del channels[channel_id]
        return await interaction.response.send_message(f"Channel: {title} is no longer being tracked")
    
@bot.tree.command(name = "tracking", description="Display tracking list")
async def tracking(interaction: discord.Interaction):
    query = "\n".join(channel[1] for channel in channels.values())
    
    await interaction.response.send_message(embed=discord.Embed(colour=discord.Colour.random(),description=query+"",title=" Tracking List "))

@bot.tree.command(name = "set", description="Fix a channel where tracking notifications appear")
async def set(interaction: discord.Interaction):
    await interaction.response.send_message("Tracking channel fixed")
    global dChannel
    dChannel = interaction.channel

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
    

 
bot.run('Discord-Bot-Tocken')
