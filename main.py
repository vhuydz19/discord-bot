import discord
from discord.ext import commands
import yt_dlp
import asyncio

TOKEN = 'MTUxNzE4MDY0MTI0NTEzNDg3OA.GhGDwm.3UEw0FkH8dpzXwkR4PCJgNR0ufV-ywFLftYnnM'
PREFIX = '?'

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Xóa lệnh help mặc định của discord.py
bot.remove_command('help')

# Cài đặt yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

voice_timers = {}

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

@bot.event
async def on_ready():
    print(f'✅ Bot đã đăng nhập: {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help | Phát nhạc 🎵"))

# Hàm tự động rời kênh
async def start_inactivity_timer(voice_client, channel):
    if channel.id in voice_timers:
        voice_timers[channel.id].cancel()
    
    await asyncio.sleep(300)
    
    if voice_client and voice_client.is_connected():
        human_count = len([m for m in channel.members if not m.bot])
        if human_count == 0:
            await voice_client.disconnect()
            try:
                if voice_client.channel.guild.text_channels:
                    text_channel = voice_client.channel.guild.text_channels[0]
                    await text_channel.send('👋 Tự động rời kênh vì không có ai trong **5 phút**!')
            except:
                pass
    if channel.id in voice_timers:
        del voice_timers[channel.id]

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    
    if before.channel is not None:
        voice_client = member.guild.voice_client
        
        if voice_client and voice_client.channel == before.channel:
            remaining_humans = len([m for m in before.channel.members if not m.bot])
            
            if remaining_humans == 0:
                task = bot.loop.create_task(
                    start_inactivity_timer(voice_client, before.channel)
                )
                voice_timers[before.channel.id] = task

    if after.channel is not None:
        voice_client = member.guild.voice_client
        
        if voice_client and voice_client.channel == after.channel:
            if after.channel.id in voice_timers:
                voice_timers[after.channel.id].cancel()
                del voice_timers[after.channel.id]

# ==================== LỆNH HELP ====================
@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(
        title='🤖 HƯỚNG DẪN SỬ DỤNG BOT NHẠC',
        description='Dưới đây là tất cả các lệnh của bot:',
        color=0x00ff00
    )
    
    embed.add_field(
        name='🎵 LỆNH PHÁT NHẠC',
        value=(
            f'**`{PREFIX}play <tên bài hát/link>`**\n'
            '→ Phát nhạc từ YouTube (hỗ trợ link hoặc từ khóa)\n'
            '→ Ví dụ: `!play em của ngày hôm qua`\n'
            '→ Ví dụ: `!play https://youtu.be/...`\n'
        ),
        inline=False
    )
    
    embed.add_field(
        name='⏯️ LỆNH ĐIỀU KHIỂN',
        value=(
            f'**`{PREFIX}pause`** → Tạm dừng nhạc\n'
            f'**`{PREFIX}resume`** → Tiếp tục phát\n'
            f'**`{PREFIX}stop`** → Dừng phát nhạc\n'
            f'**`{PREFIX}volume <0-100>`** → Chỉnh âm lượng\n'
            '→ Ví dụ: `!volume 50`\n'
        ),
        inline=False
    )
    
    embed.add_field(
        name='🔊 LỆNH KÊNH THOẠI',
        value=(
            f'**`{PREFIX}join`** → Bot tham gia kênh thoại của bạn\n'
            f'**`{PREFIX}leave`** → Bot rời kênh thoại\n'
            '💡 Bot sẽ tự động rời kênh sau 5 phút nếu không có ai\n'
        ),
        inline=False
    )
    
    embed.add_field(
        name='📋 LỆNH KHÁC',
        value=(
            f'**`{PREFIX}help`** → Hiển thị hướng dẫn này\n'
        ),
        inline=False
    )
    
    embed.set_footer(text='Chúc bạn nghe nhạc vui vẻ! 🎶')
    
    await ctx.send(embed=embed)

# Lệnh join
@bot.command(name='join')
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f'🔊 Đã tham gia kênh: **{channel.name}**')
    else:
        await ctx.send('❌ Bạn phải ở trong kênh thoại!')

# Lệnh leave
@bot.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        if ctx.voice_client.channel.id in voice_timers:
            voice_timers[ctx.voice_client.channel.id].cancel()
            del voice_timers[ctx.voice_client.channel.id]
        
        await ctx.voice_client.disconnect()
        await ctx.send('👋 Đã rời kênh thoại!')
    else:
        await ctx.send('❌ Bot không ở trong kênh thoại nào!')

# Lệnh play
@bot.command(name='play')
async def play(ctx, *, url):
    if not ctx.voice_client:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
        else:
            await ctx.send('❌ Bạn phải ở trong kênh thoại!')
            return

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Lỗi: {e}') if e else None)
            await ctx.send(f'🎵 Đang phát: **{player.title}**')
        except Exception as e:
            await ctx.send(f'❌ Có lỗi: {e}')

# Lệnh pause
@bot.command(name='pause')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('⏸️ Đã tạm dừng!')

# Lệnh resume
@bot.command(name='resume')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('▶️ Tiếp tục phát!')

# Lệnh stop
@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send('⏹️ Đã dừng phát nhạc!')

# Lệnh volume
@bot.command(name='volume')
async def volume(ctx, volume: int):
    if ctx.voice_client is None:
        return await ctx.send('❌ Bot không ở trong kênh thoại!')
    
    if 0 <= volume <= 100:
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f'🔊 Âm lượng: **{volume}%**')

if __name__ == '__main__':
    bot.run(TOKEN)
