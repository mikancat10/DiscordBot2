import discord
from discord.ext import commands
import datetime

# ボットの設定
intents = discord.Intents.default()
intents.members = True  # メンバー管理用
intents.message_content = True  # コマンド読み取り用

bot = commands.Bot(command_prefix="!", intents=intents)

# --- 1. 起動時に実行 ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

# --- 2. ウェルカムメッセージ & 自動ロール付与 ---
@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel # システムメッセージチャンネルを取得
    if channel:
        await channel.send(f"{member.mention} さん、サーバーへようこそ！")
    
    # 「新規メンバー」という名前の役職を自動付与（事前に作成が必要）
    role = discord.utils.get(member.guild.roles, name="新規メンバー")
    if role:
        await member.add_roles(role)

# --- 3. 基本的な管理コマンド (BAN/Kick/Channel作成) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def create_channel(ctx, name):
    """新しいテキストチャンネルを作成します"""
    await ctx.guild.create_text_channel(name)
    await ctx.send(f"チャンネル #{name} を作成しました。")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    """メンバーをキックします"""
    await member.kick(reason=reason)
    await ctx.send(f"{member.name} をキックしました。")

# --- 4. 執筆管理：ステータス入力の雛形 ---
@bot.command()
async def work_start(ctx, title):
    """執筆開始を宣言し、現在のステータスを表示します"""
    embed = discord.Embed(title=f"【執筆開始】{title}", color=0x00ff00)
    embed.add_field(name="開始時刻", value=datetime.datetime.now().strftime("%H:%M"), inline=True)
    embed.add_field(name="ステータス", value="着手中", inline=True)
    await ctx.send(embed=embed)

# ボットの起動（ここにトークンを入力）
# bot.run('YOUR_TOKEN_HERE')

import discord
from discord.ext import commands, tasks
import datetime
import requests
import feedparser

# --- 設定 ---
TOKEN = 'YOUR_BOT_TOKEN'
CHANNEL_ID = 123456789012345678  # 通知を送りたいチャンネルID
# 毎朝通知したい時刻 (JST)
NOTIFY_TIME = datetime.time(hour=7, minute=0, tzinfo=datetime.timezone(datetime.timedelta(hours=9)))

class MorningBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # バックグラウンドタスクの開始
        self.morning_task.start()

    @tasks.loop(time=NOTIFY_TIME)
    async def morning_task(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            return

        # 1. ニュース取得 (例: Yahooニュース RSS)
        news_url = "https://news.yahoo.co.jp/rss/topics/top-picks.xml"
        feed = feedparser.parse(news_url)
        news_text = "\n".join([f"・[{e.title}]({e.link})" for e in feed.entries[:3]])

        # 2. 天気取得 (Open-Meteo API: 東京の例)
        # 緯度・経度を変更すれば他地域も可能 (東京: lat=35.6895, lon=139.6917)
        weather_url = "https://api.open-meteo.com/v1/forecast?latitude=35.6895&longitude=139.6917&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=Asia%2FTokyo"
        response = requests.get(weather_url).json()
        max_temp = response['daily']['temperature_2m_max'][0]
        min_temp = response['daily']['temperature_2m_min'][0]

        # 3. メッセージ構築
        embed = discord.Embed(title="☀️ おはようございます！", color=0xffcc00)
        embed.add_field(name="📅 日付", value=datetime.date.today().strftime("%Y/%m/%d"), inline=False)
        embed.add_field(name="🌡️ 今日の気温", value=f"最高: {max_temp}℃ / 最低: {min_temp}℃", inline=False)
        embed.add_field(name="📰 主要ニュース", value=news_text or "ニュースを取得できませんでした。", inline=False)
        embed.set_footer(text="今日も一日頑張りましょう！")

        await channel.send(embed=embed)

bot = MorningBot()
bot.run(TOKEN)
