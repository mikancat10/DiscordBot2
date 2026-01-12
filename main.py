import discord
from discord.ext import commands, tasks
import datetime
import requests
import feedparser
import os

# --- 設定（Renderの環境変数から取得） ---
TOKEN = os.getenv('DISCORD_TOKEN')
NEWS_CH_ID = int(os.getenv('NEWS_CH_ID', 0))
WEATHER_CH_ID = int(os.getenv('WEATHER_CH_ID', 0))
GREETING_CH_ID = int(os.getenv('GREETING_CH_ID', 0))

JST = datetime.timezone(datetime.timedelta(hours=9))
NOTIFY_TIME = datetime.time(hour=7, minute=0, tzinfo=JST)

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.morning_task.start()

    async def on_ready(self):
        print(f'Logged in as {self.user.name}')

    # --- 朝の通知タスク (各チャンネルへ振り分け) ---
    @tasks.loop(time=NOTIFY_TIME)
    async def morning_task(self):
        # 1. 朝の挨拶
        greeting_ch = self.get_channel(GREETING_CH_ID)
        if greeting_ch:
            today = datetime.date.today().strftime("%Y/%m/%d")
            await greeting_ch.send(f"☀️ **{today} おはようございます！**\n今日も一日、楽しく過ごしましょう！")

        # 2. 天気予報
        weather_ch = self.get_channel(WEATHER_CH_ID)
        if weather_ch:
            try:
                w_url = "https://api.open-meteo.com/v1/forecast?latitude=35.6895&longitude=139.6917&daily=temperature_2m_max,temperature_2m_min&timezone=Asia%2FTokyo"
                w_res = requests.get(w_url).json()
                max_t = w_res['daily']['temperature_2m_max'][0]
                min_t = w_res['daily']['temperature_2m_min'][0]
                
                embed_w = discord.Embed(title="🌡️ 今日の天気 (東京)", color=0x00aaff)
                embed_w.add_field(name="最高気温", value=f"{max_t}℃", inline=True)
                embed_w.add_field(name="最低気温", value=f"{min_t}℃", inline=True)
                await weather_ch.send(embed=embed_w)
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
