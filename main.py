import discord
from discord.ext import commands, tasks
import datetime
import requests
import feedparser
import os

# --- 設定（RenderのEnvironment Variablesから取得） ---
# Renderの管理パネルで DISCORD_TOKEN と CHANNEL_ID を設定してください
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 0))

# タイムゾーンの設定（日本時間 UTC+9）
JST = datetime.timezone(datetime.timedelta(hours=9))
NOTIFY_TIME = datetime.time(hour=7, minute=0, tzinfo=JST)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True          # メンバー参加検知用
        intents.message_content = True  # コマンド読み取り用
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # バックグラウンドタスク（朝の通知）を開始
        self.morning_task.start()

    async def on_ready(self):
        print(f'Logged in as {self.user.name}')
        print('--- 朝の通知機能：待機中 ---')

    # --- ウェルカムメッセージ & 自動ロール付与 ---
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel:
            await channel.send(f"{member.mention} さん、サーバーへようこそ！")
        
        # 「新規メンバー」という役職を自動付与（事前に作成済みであること）
        role = discord.utils.get(member.guild.roles, name="新規メンバー")
        if role:
            await member.add_roles(role)

    # --- 朝の通知タスク (毎日07:00 JST) ---
    @tasks.loop(time=NOTIFY_TIME)
    async def morning_task(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            print("通知チャンネルが見つかりません。")
            return

        # 1. ニュース取得 (Yahooニュース)
        try:
            feed = feedparser.parse("https://news.yahoo.co.jp/rss/topics/top-picks.xml")
            news_list = [f"・[{e.title}]({e.link})" for e in feed.entries[:3]]
            news_text = "\n".join(news_list)
        except Exception as e:
            news_text = "ニュースの取得に失敗しました。"

        # 2. 天気取得 (Open-Meteo: 東京)
        try:
            w_url = "https://api.open-meteo.com/v1/forecast?latitude=35.6895&longitude=139.6917&daily=temperature_2m_max,temperature_2m_min&timezone=Asia%2FTokyo"
            w_res = requests.get(w_url).json()
            max_t = w_res['daily']['temperature_2m_max'][0]
            min_t = w_res['daily']['temperature_2m_min'][0]
            weather_text = f"最高: {max_t}℃ / 最低: {min_t}℃"
        except Exception as e:
            weather_text = "天気を取得できませんでした。"

        # 3. メッセージ作成
        embed = discord.Embed(title="☀️ おはようございます！", color=0xffcc00)
        embed.add_field(name="📅 日付", value=datetime.date.today().strftime("%Y/%m/%d"), inline=False)
        embed.add_field(name="🌡️ 今日の天気 (東京)", value=weather_text, inline=False)
        embed.add_field(name="📰 主要ニュース", value=news_text, inline=False)
        embed.set_footer(text="今日も素晴らしい一日になりますように！")

        await channel.send(embed=embed)

# --- 基本的な管理コマンド ---
bot = MyBot()

@bot.command()
@commands.has_permissions(administrator=True)
async def ping(ctx):
    """ボットの生存確認用コマンド"""
    await ctx.send(f"Pong! ({round(bot.latency * 1000)}ms)")

@bot.command()
@commands.has_permissions(administrator=True)
async def create_ch(ctx, name):
    """新しいテキストチャンネルを作成します"""
    new_ch = await ctx.guild.create_text_channel(name)
    await ctx.send(f"チャンネル {new_ch.mention} を作成しました。")

# ボットの起動
if TOKEN:
    bot.run(TOKEN)
else:
    print("エラー: DISCORD_TOKENが設定されていません。")
