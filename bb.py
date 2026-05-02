import discord
from discord.ext import tasks, commands
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask
from threading import Thread
import os

# --- TẠO WEB SERVER ĐỂ TREO TRÊN RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot Discord đang hoạt động 24/7!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CẤU HÌNH BOT DISCORD ---
TOKEN = os.environ.get('BOT_TOKEN') # Lấy từ Environment Variable trên Render
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', 0))
URL = "https://vulcanvalues.com/grow-a-garden/stock"

class GrowBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    def get_stock_data(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(URL, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            grid = soup.find('div', class_='grid')
            if not grid: return None

            cols = grid.find_all('div', recursive=False)
            stock_fields = []
            for col in cols:
                header = col.find('h2')
                if not header: continue
                
                items = col.find_all('li')
                item_list = "".join([f"• {li.find('span').get_text(' ', strip=True)}\n" for li in items if li.find('span')])
                
                if item_list:
                    stock_fields.append({"name": f"📦 {header.get_text(strip=True)}", "value": item_list})
            return stock_fields
        except Exception as e:
            print(f"Lỗi quét web: {e}")
            return None

    async def on_ready(self):
        print(f'✅ Đã đăng nhập: {self.user}')
        if not self.update_stock_task.is_running():
            self.update_stock_task.start()

    @tasks.loop(minutes=3) # Cập nhật mỗi 3 phút
    async def update_stock_task(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel: return

        fields = self.get_stock_data()
        if not fields: return

        embed = discord.Embed(
            title="🌿 GROW A GARDEN - MARKET STOCK",
            url=URL,
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        for f in fields:
            embed.add_field(name=f['name'], value=f['value'], inline=False)
        
        embed.set_footer(text="Cập nhật tự động mỗi 3 phút")
        await channel.send(embed=embed)

if __name__ == "__main__":
    keep_alive() # Chạy server web song song
    bot = GrowBot()
    bot.run(TOKEN)