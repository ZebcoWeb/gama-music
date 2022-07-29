import asyncio
import discord
import youtube_dl
import re
import os

from discord import VoiceClient
from discord.colour import Colour
from discord.embeds import Embed
from discord.ext.commands.context import Context
from discord import FFmpegPCMAudio
from discord.ext import commands

TOKEN = os.environ.get('TOKEN')

PREFIX = os.environ.get('PREFIX')

intents = discord.Intents.all()
client = commands.Bot(command_prefix=PREFIX, intents=intents)
client.remove_command('help')

@client.event
async def on_ready():
    print(f"Alright we are ready! - Gama Music\n- ID: {client.application_id}")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.streaming, name=f'Music | {PREFIX}help'))


def red_embed(title, des):
    embed = Embed(description=des, color=Colour.red())
    if title:
        embed.title = title
    embed.set_footer(icon_url=client.user.avatar.url, text=f'Gama music client | {PREFIX}help for more help')
    return embed

def green_embed(title, des):
    embed = Embed(description=des, color=Colour.green())
    if title:
        embed.title = title
    embed.set_footer(icon_url=client.user.avatar.url, text=f'Gama music client | {PREFIX}help for more help')
    return embed

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {"options": "-vn"}

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
    
    @classmethod
    async def from_search(cls, query, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(f"ytsearch:{query}", download=not stream)
        )

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

def yt_validate(url: str):
    return re.match('^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$', url)

def mp3_validate(url: str):
    return re.match('^(https?|ftp|file):\/\/(www.)?(.*?)\.(mp3)$', url)


@client.command(aliases=['join'])
async def join_to_vc(ctx: Context, *, channel: discord.VoiceChannel = None):
    """Joins a voice channel"""
    if channel:
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()
    
    elif ctx.author.voice:
        await ctx.author.voice.channel.connect()

    else:
        await ctx.reply(embed=red_embed(
            None,
            des=f'``{PREFIX}join [#Channel](optional)``\n- Use this command when entering VC or use it with VC mention.')
        )

@client.command(aliases=['p', 'play'])
async def play_sound(ctx :Context, *, query = None):
    """Plays from a url (YouTube and mp3 urls are supported)"""
    if query:
        if yt_validate(query):
            async with ctx.typing():
                player = await YTDLSource.from_url(query, loop=client.loop, stream=True)
                ctx.voice_client.play(
                    player, after=lambda e: print(f"Player error: {e}") if e else None
                )
                await ctx.send(embed=green_embed(
                    None,
                    des=f'Now playing: [{player.title}]({query})'
                ))

        elif mp3_validate(query):
            player = FFmpegPCMAudio(query, executable="ffmpeg", **ffmpeg_options)
            ctx.voice_client.play(
                player, after=lambda e: print(f"> Player error: {e}") if e else None
            )
            title = query.split('/')[-1]
            await ctx.send(embed=green_embed(
                None,
                des=f'Now playing: [{title}]({query})'
            ))
        else:
            async with ctx.typing():
                player = await YTDLSource.from_search(query, loop=client.loop, stream=True)
                ctx.voice_client.play(
                    player, after=lambda e: print(f"Player error: {e}") if e else None
                )
                await ctx.send(embed=green_embed(
                    None,
                    des=f'Now playing: [{player.title}]({query})'
                ))

    else:
        await ctx.reply(embed=red_embed(
            None,
            des=f'``{PREFIX}p|play [URL]``\n- Send url from YouTube or mp3 source!'
        ))
        await ctx.voice_client.disconnect(force=True)

@client.command(aliases=['volume', 'v'])
async def change_volume(ctx, volume: int = None):
    """Change the volume of the sound(only for YT source)"""

    if ctx.voice_client is None:
        return await ctx.reply(embed=red_embed(
            None,
            des='Not connected to a voice channel'
        ))
    else:
        if volume:
            try:
                ctx.voice_client.source.volume = volume / 100
                await ctx.send(embed=green_embed(
                    None,
                    des=f'Changed volume to {volume}%'
                ))
            except:
                await ctx.reply(embed=red_embed(
                None,
                des=f'There is no sound playing from YouTube'
                ))
        else:
            await ctx.reply(embed=red_embed(
                None,
                des=f'``{PREFIX}v|volume [value](To number)``\n- Change the volume of the sound(only for YT source)'
            ))

@client.command(aliases=['pause'])
async def pause_sound(ctx: Context):
    """Pause the sound while playing"""

    if ctx.voice_client is None:
        return await ctx.reply(embed=red_embed(
            None,
            des='Not connected to a voice channel'
        ))
    else:
        voice_client: VoiceClient = ctx.voice_client

        if voice_client.is_playing():
            if not voice_client.is_paused():
                voice_client.pause()
                await ctx.reply(embed=green_embed(
                    None,
                    des='The sound paused'
                ))
        elif voice_client.is_paused():
            await ctx.reply(embed=red_embed(
                None,
                des='The sound has already paused'
            ))

        else:
            await ctx.reply(embed=red_embed(
                None,
                des='Sound is not playing'
            ))
    

@client.command(aliases=['resume'])
async def resume_sound(ctx: Context):
    """Resume the sound while paused"""

    if ctx.voice_client is None:
        return await ctx.reply(embed=red_embed(
            None,
            des='Not connected to a voice channel'
        ))
    else:
        voice_client: VoiceClient = ctx.voice_client

        if voice_client.is_paused():
            voice_client.resume()
            await ctx.send(embed=green_embed(
                None,
                des='The sound resumed'
            )) 

        else:
            await ctx.reply(embed=red_embed(
                None,
                des='The sound has already playing'
            )) 

@client.command(aliases=['dc', 'disconnect'])
async def disconnect_bot(ctx: commands.Context):
    """Stops and disconnects the client from voice"""
    await ctx.voice_client.disconnect()

@play_sound.before_invoke
async def ensure_voice(ctx):
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.reply(embed=red_embed(
                None,
                des='You are not connected to a voice channel'
            ))
    elif ctx.voice_client.is_playing():
        ctx.voice_client.stop()

@client.command(aliases=["help"])
async def help_sound(ctx: Context):
    """Music client commands help"""
    
    commands = client.commands
    help_des = []

    for c in commands:
        aliases = '|'.join(c.aliases)
        help = c.help if c.help else 'No help'
        help_des.append(f'``{PREFIX}{aliases}`` - {help}\n')
    help_des = '\n'.join(help_des)

    embed = green_embed(
        f'<:Rules4:871705388918128640> {client.user.name} client commands help',
        help_des
        )
    
    await ctx.send(embed=embed)

    # ------------------------

client.run(TOKEN, log_handler=None)
