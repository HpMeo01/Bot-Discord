import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import random
import os
import urllib.parse
import tempfile
import re
import asyncio

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("Missing DISCORD_TOKEN")

# URL Google Image với từ khóa "ảnh se"
BASE_URL = 'https://www.google.com/search?client=ms-android-samsung-ss&hs=4MBq&sca_esv=47fdd52eba661d26&udm=2&fbs=ABfTbFW4UnGvBVgqDYjq_ksvF_WzL0qSsUjsQCJMDr-_PEHsElEq-XkTNsyVCf0qvOFQ8LnuuR9cbg58QXWYnT3_hh-_8Vra65L0ejGJoDMpRuoUqXVIF_V1qwtmZ6UodYfmS5t1ampSqHH37YJIP7yrNhqvZALTbr6AgQyVLW-7jOCm60GM0QZmIpD5nrIITe4bNjRapHYrjT7mhkWhrplv6Q4gWznEbKk6RbtJriD-sWdUKAYlpdcfps2ib1WuTYnRnbpiFSzl&q=%E1%BA%A3nh%20se&sa=X&ved=2ahUKEwjZz8r5pbOVAxXjiK8BHbtSLkUQtKgLegQIIRAB'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def fetch_image_from_url():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9',
        'Referer': 'https://www.google.com/'
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BASE_URL, headers=headers, timeout=25) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        except Exception:
            return None

    # Dùng regex để lấy tất cả URL ảnh từ Google Images (thẻ img hoặc dữ liệu)
    soup = BeautifulSoup(html, 'html.parser')
    img_urls = []

    # Tìm tất cả thẻ img có src bắt đầu http và không phải base64
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and src.startswith('http') and not src.startswith('data:'):
            # Lọc ảnh quảng cáo/logo
            if 'gstatic' not in src and 'google' not in src and 'favicon' not in src:
                img_urls.append(src)

    # Nếu không có, dùng regex để trích xuất từ script hoặc data-url
    if not img_urls:
        pattern = r'"(https?://[^"]+\.(jpg|jpeg|png|gif|webp))"'
        matches = re.findall(pattern, html, re.IGNORECASE)
        for m in matches:
            url = m[0]
            if 'gstatic' not in url and 'google' not in url:
                img_urls.append(url)

    # Nếu vẫn không có, dùng regex lấy từ thẻ a href ảnh
    if not img_urls:
        pattern = r'imgurl=([^&]+)'
        matches = re.findall(pattern, html)
        for m in matches:
            url = urllib.parse.unquote(m)
            if url.startswith('http') and 'gstatic' not in url:
                img_urls.append(url)

    if not img_urls:
        return None

    # Loại bỏ trùng lặp và chọn ngẫu nhiên
    unique_urls = list(set(img_urls))
    return random.choice(unique_urls) if unique_urls else None

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

@bot.tree.command(name='ezz', description='Lấy ảnh ngẫu nhiên từ Google (từ khóa "ảnh se")')
async def ezz(interaction: discord.Interaction):
    await interaction.response.send_message('Đang tìm ảnh...', ephemeral=False)

    img_url = await fetch_image_from_url()
    if not img_url:
        await interaction.followup.send('Không tìm thấy ảnh. Thử lại sau.')
        return

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(img_url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                if resp.status != 200:
                    await interaction.followup.send('Không tải được ảnh.')
                    return
                content = await resp.read()
                # Xác định định dạng file
                ext = 'jpg'
                if 'png' in resp.headers.get('Content-Type', ''):
                    ext = 'png'
                elif 'gif' in resp.headers.get('Content-Type', ''):
                    ext = 'gif'
                elif 'webp' in resp.headers.get('Content-Type', ''):
                    ext = 'webp'
                with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
        except Exception as e:
            await interaction.followup.send(f'Lỗi tải ảnh: {e}')
            return

    try:
        with open(tmp_path, 'rb') as f:
            await interaction.followup.send(file=discord.File(f, f'image.{ext}'))
    except Exception as e:
        await interaction.followup.send(f'Lỗi gửi ảnh: {e}')
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

bot.run(TOKEN)
