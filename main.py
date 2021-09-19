import asyncio
import atexit
import os
import discord
from discord.ext import commands
from requests import get
import youtube_dl

print('start')

videos_list = []

# Remove mp3 files on exit
def on_exit():
    files = os.listdir(os.getcwd())
    mp3_files = [file for file in files if file.endswith(".mp3")]
    for file in mp3_files:
        os.remove(file)

atexit.register(on_exit)

# FFmpeg path, required for playing music
ffmpeg_path_file = open('ffmpeg-path.txt')
ffmpeg_path = ffmpeg_path_file.read()

# Setup youtube dl
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'audio.mp3',
    'age_limit:': '18',
}

ydl = youtube_dl.YoutubeDL(ydl_opts)

def video_search(arg):
    try:
        get(arg) 
    except:
        video = ydl.extract_info(f"ytsearch:{arg}", download=False)['entries'][0]
    else:
        video = ydl.extract_info(arg, download=False)

    return video

# Setup bot
bot = commands.Bot(command_prefix='!')

global file_for_deletion
file_for_deletion = -1

# Playing audio
async def play_next_audio(ctx):
    # Connect to voice channel
    voicechannel = ctx.author.voice.channel
    if ctx.voice_client == None or not ctx.voice_client.channel == voicechannel:
        vc = await voicechannel.connect()
    else:
        vc = ctx.voice_client

    if vc.is_connected() and not vc.is_playing() and not vc.is_paused() and not len(videos_list) == 0 :
        # Remove previous audio
        global file_for_deletion

        print(file_for_deletion)

        if os.path.isfile(file_for_deletion):
            os.remove(file_for_deletion)
        
        # Get video data
        video = videos_list.pop()

        url = video['webpage_url']
        video_file = video['title'] + '.mp3'
        countdown = video['duration']

        # Rich Presence
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=video['title']))

        # Download
        if not os.path.isfile(video_file):
            try:
                ydl.download([url])
            except:
                await ctx.send('Ich kann ' + video['title'] + ' nicht spielen :(')
                return
            os.rename('audio.mp3', video_file)

        # Play audio
        vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=video_file))

        # Mark file for deletion
        file_for_deletion = video_file;

        # Tell the users which video is playing
        await ctx.send('Ich spiele: ' + url)

        # Next video countdown
        await next_audio_countdown(ctx, countdown)

async def next_audio_countdown(ctx, countdown):
    def check(message):
        return False
    try:
        m = await bot.wait_for("message", check=check, timeout=countdown)
        await ctx.send("Countdown cancelled")
    except asyncio.TimeoutError:
        await play_next_audio(ctx)

# Commands

# Play command
@commands.command(name='play', aliases=['paul', 'p', 'q', 'queue'])
async def play(ctx, *args):
    # Not enough arguments
    if len(args) == 0:
        # Unpause if paused
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Ich spiele weiter. *b z k z*')
        
        return
    
    # Create search term, or link
    term = ''
    for string in args:
        term += string + ' '
    
    # Remove redundant space
    term = term.rstrip()

    # Create audio to be played later
    video = video_search(term)
    videos_list.append(video)

    # Start first video
    await ctx.send('Ok')
    await play_next_audio(ctx)

@commands.command(name='stop')
async def stop(ctx):
    # Remove all videos from list and stop playing
    if not ctx.voice_client == None:
        videos_list.clear()
        ctx.voice_client.disconnect()
        await ctx.send("Tschüss :wave:")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='nichts'))

@commands.command(name='pause', aliases=['resume'])
async def pause(ctx):
    # (Un)pause audio
    if not ctx.voice_client == None:
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send('Ich spiele weiter. *b z k z*')
        else:
            ctx.voice_client.pause()
            await ctx.send('Ich habe aufgehört zu spielen.')

@commands.command(name='skip', aliases=['s'])
async def skip(ctx):
    # Skip one audio
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
    ctx.voice_client.stop()

    await ctx.send('Ich habe ein Lied übersprungen.')
    await play_next_audio(ctx)

# Register commands
bot.add_command(play)
bot.add_command(stop)
bot.add_command(pause)
bot.add_command(skip)

# Read token from file
token_file = open('token.txt')
token = token_file.read()

# Run bot
bot.run(token)