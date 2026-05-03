import discord
from discord.ext import tasks, commands
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask
from threading import Thread
import os

# ==========================================
# CẤU HÌNH BIẾN MÔI TRƯỜNG (ENVIRONMENT)
# ==========================================
TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID_STR = os.environ.get('CHANNEL_ID')
# Đảm bảo chuyển ID kênh sang dạng số nguyên (integer), nếu không có trả về 0
CHANNEL_ID = int(CHANNEL_ID_STR) if CHANNEL_ID_STR and CHANNEL_ID_STR.isdigit() else 0
URL = "https://vulcanvalues.com/grow-a-garden/stock"

# ==========================================
# 1. WEB SERVER ĐỂ TREO TRÊN RENDER
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Discord đang hoạt động 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==========================================
# 2. CẤU HÌNH BOT DISCORD
# ==========================================
class GrowBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    def get_stock_data(self):
        """Hàm lấy dữ liệu website"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(URL, headers=headers, timeout=15)
            
            if response.status_code != 200:
                print(f"[LỖI WEB] Web trả về mã lỗi: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            grid = soup.find('div', class_='grid')
            if not grid:
                print("[LỖI WEB] Không tìm thấy cấu trúc dữ liệu lưới (grid) trên web.")
                return None

            cols = grid.find_all('div', recursive=False)
            stock_fields = []
            
            for col in cols:
                header = col.find('h2')
                if not header: continue
                
                items = col.find_all('li')
                item_list = ""
                for li in items:
                    span = li.find('span')
                    if span:
                        item_list += f"• {span.get_text(' ', strip=True)}\n"
                
                if item_list:
                    stock_fields.append({
                        "name": f"📦 {header.get_text(strip=True)}", 
                        "value": item_list
                    })
            return stock_fields
        except Exception as e:
            print(f"[LỖI CÀO DỮ LIỆU] {e}")
            return None

    # Khởi động loop thông qua setup_hook (Chuẩn mới của Discord.py)
    async def setup_hook(self):
        self.update_stock_task.start()

    async def on_ready(self):
        print(f'✅ Đã đăng nhập thành công vào: {self.user}')
        print(f'⚙️ Kênh đang cấu hình gửi tin: {CHANNEL_ID}')

    # Đảm bảo bot load xong server mới bắt đầu quét
    @tasks.loop(minutes=3)
    async def update_stock_task(self):
        print("\n[LOG] Đang tiến hành quét dữ liệu từ web...")
        channel = self.get_channel(CHANNEL_ID)
        
        if not channel:
            print(f"❌ [LỖI KÊNH] Không tìm thấy kênh ID: {CHANNEL_ID}. Hãy kiểm tra ID và quyền View Channel của bot.")
            return

        fields = self.get_stock_data()
        if not fields:
            print("⚠️ [CẢNH BÁO] Quét web không ra kết quả (Web thay đổi HTML hoặc bị chặn).")
            return

        embed = discord.Embed(
            title="🌿 GROW A GARDEN - MARKET STOCK",
            url=URL,
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        for f in fields:
            embed.add_field(name=f['name'], value=f['value'], inline=False)
        
        embed.set_footer(text="Cập nhật tự động mỗi 3 phút")
        
        try:
            await channel.send(embed=embed)
            print(f"[THÀNH CÔNG] Đã gửi tin nhắn lúc {datetime.now().strftime('%H:%M:%S')}")
        except discord.Forbidden:
            print("❌ [LỖI QUYỀN] Bot không có quyền 'Send Messages' hoặc 'Embed Links' trong kênh này.")
        except Exception as e:
            print(f"❌ [LỖI GỬI TIN] {e}")

    # CHỜ BOT SẴN SÀNG 100% MỚI CHẠY LOOP
    @update_stock_task.before_loop
    async def before_update(self):
        print("⏳ Đang chờ bot đồng bộ dữ liệu với Discord...")
        await self.wait_until_ready()

# ==========================================
# 3. CHẠY CHƯƠNG TRÌNH
# ==========================================
if __name__ == "__main__":
    keep_alive() # Khởi động web server Flask
    
    if not TOKEN:
        print("❌ LỖI NGHIÊM TRỌNG: Chưa có BOT_TOKEN trong biến môi trường của Render!")
    elif CHANNEL_ID == 0:
        print("❌ LỖI NGHIÊM TRỌNG: ID Kênh không hợp lệ hoặc bị trống!")
    else:
        bot = GrowBot()
        bot.run(TOKEN)
