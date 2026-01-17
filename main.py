import discord
from discord.ext import commands
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# --- 設定 ---
TOKEN = os.getenv('DISCORD_TOKEN')
# Renderの環境変数にJSONの中身をそのまま貼り付けてください
GCP_JSON = os.getenv('GCP_SERVICE_ACCOUNT') 
SPREADSHEET_KEY = os.getenv('SPREADSHEET_KEY') # スプレッドシートのURLにあるID

# Googleスプレッドシートへの認証
def get_gspread_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(GCP_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

# --- 執筆管理：スプレッドシート連携コマンド ---

@bot.command()
async def write(ctx, title: str, count: int):
    """執筆報告: !write 作品名 文字数"""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SPREADSHEET_KEY).sheet1 # 最初のシート
        
        # 記録用データの作成
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        date_str = now.strftime("%Y/%m/%d %H:%M")
        user_name = ctx.author.name
        
        # シートの末尾に行を追加 [日付, ユーザー, 作品名, 文字数]
        sheet.append_row([date_str, user_name, title, count])
        
        # 応援メッセージの抽選
        cheers = ["その調子です！", "素晴らしい進捗ですね！", "執筆お疲れ様です！", "一歩前進ですね！"]
        
        embed = discord.Embed(title="📝 執筆を記録しました", color=0x2ecc71)
        embed.add_field(name="作品名", value=title, inline=True)
        embed.add_field(name="今回報告", value=f"{count} 字", inline=True)
        embed.set_footer(text=random.choice(cheers))
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"⚠️ 記録に失敗しました: {e}")

@bot.command()
async def stats(ctx):
    """これまでの合計執筆文字数を集計"""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SPREADSHEET_KEY).sheet1
        records = sheet.get_all_records()
        
        total = sum(int(row['文字数']) for row in records if row['ユーザー'] == ctx.author.name)
        
        embed = discord.Embed(title=f"📊 {ctx.author.name}さんの統計", color=0x9b59b6)
        embed.add_field(name="累計執筆文字数", value=f"{total} 字", inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"⚠️ 集計に失敗しました: {e}")

# (以前の朝の通知やチケット機能のコードと組み合わせて使用してください)
            except:
                await weather_ch.send("⚠️ 天気情報の取得に失敗しました。")

        # 3. ニュース
        news_ch = self.get_channel(NEWS_CH_ID)
        if news_ch:
            try:
                feed = feedparser.parse("https://news.yahoo.co.jp/rss/topics/top-picks.xml")
                news_text = "\n".join([f"・[{e.title}]({e.link})" for e in feed.entries[:5]])
                
                embed_n = discord.Embed(title="📰 最新ニュース", description=news_text, color=0xff0000)
                await news_ch.send(embed=embed_n)
            except:
                await news_ch.send("⚠️ ニュースの取得に失敗しました。")

# --- 以降、管理コマンドやボット起動は前回と同じ ---
bot = MyBot()

@bot.command()
@commands.has_permissions(administrator=True)
async def ping(ctx):
    await ctx.send(f"Pong! ({round(bot.latency * 1000)}ms)")

if TOKEN:
    bot.run(TOKEN)
# --- 作品登録機能 ---
@bot.command()
async def entry(ctx, title: str, theme: str, goal: int, deadline: str):
    """作品の基本情報を登録: !entry タイトル テーマ 目標字数 2024/12/31"""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("Works")
        
        # データの追加
        sheet.append_row([title, theme, goal, deadline, "執筆中"])
        
        embed = discord.Embed(title="📔 新規作品を登録しました", color=0x3498db)
        embed.add_field(name="タイトル", value=title, inline=True)
        embed.add_field(name="テーマ", value=theme, inline=True)
        embed.add_field(name="目標文字数", value=f"{goal} 字", inline=True)
        embed.add_field(name="締切", value=deadline, inline=True)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"⚠️ 登録に失敗しました。シート名「Works」があるか確認してください: {e}")

# --- 進捗・ペース分析機能 ---
@bot.command()
async def check(ctx, title: str):
    """作品の進捗と必要ペースを分析: !check タイトル"""
    try:
        client = get_gspread_client()
        # 作品情報の取得
        works_sheet = client.open_by_key(SPREADSHEET_KEY).worksheet("Works")
        work = next((r for r in works_sheet.get_all_records() if r['作品名'] == title), None)
        
        # 執筆履歴の取得
        log_sheet = client.open_by_key(SPREADSHEET_KEY).sheet1
        current_total = sum(int(r['文字数']) for r in log_sheet.get_all_records() if r['作品名'] == title)
        
        if not work:
            return await ctx.send("作品が見つかりません。先に !entry で登録してください。")

        goal = int(work['目標字数'])
        deadline = datetime.datetime.strptime(work['締切日'], "%Y/%m/%d").date()
        days_left = (deadline - datetime.date.today()).days
        
        # 進捗計算
        percent = (current_total / goal) * 100
        bar_num = int(percent // 10)
        bar = "🟦" * bar_num + "⬜" * (10 - bar_num)
        
        # 必要ペース計算
        remaining_chars = goal - current_total
        pace = remaining_chars / days_left if days_left > 0 else remaining_chars

        embed = discord.Embed(title=f"📊 進捗レポート: {title}", color=0xf1c40f)
        embed.add_field(name="現在の進捗", value=f"{bar} {percent:.1f}%", inline=False)
        embed.add_field(name="書いた文字数", value=f"{current_total} / {goal} 字", inline=True)
        embed.add_field(name="残り日数", value=f"{max(0, days_left)} 日", inline=True)
        
        if days_left > 0 and remaining_chars > 0:
            embed.add_field(name="📈 完遂に必要なペース", value=f"1日あたり **{int(pace)}** 字", inline=False)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"⚠️ 分析に失敗しました: {e}")

# --- 音楽再生用の設定 ---
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
    'source_address': '0.0.0.0', # IPv6問題を避けるための設定
    # プロキシを使用する場合は以下を有効にします
    # 'proxy': os.getenv('PROXY_URL') 
}

ffmpeg_options = {
    'options': '-vn',
    # 接続が切れないようにするための再接続設定
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

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

# --- 音楽コマンド群 ---

@bot.command()
async def join(ctx):
    """ボイスチャンネルに接続: !join"""
    if not ctx.author.voice:
        return await ctx.send("ボイスチャンネルに参加してからコマンドを打ってください。")
    channel = ctx.author.voice.channel
    await channel.connect()

@bot.command()
async def play(ctx, *, url):
    """YouTubeから再生: !play [URLまたは検索ワード]"""
    async with ctx.typing():
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
    await ctx.send(f'🎵 再生中: **{player.title}**')

@bot.command()
async def stop(ctx):
    """再生停止して退出: !stop"""
    await ctx.voice_client.disconnect()

# ※これまでの !write, !entry, 朝の通知などのコードと統合して使用してください
