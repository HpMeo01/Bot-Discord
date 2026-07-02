import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import random
import os
import tempfile
import re
import urllib.parse
import asyncio

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("Missing DISCORD_TOKEN")

BASE_URL = 'https://www.google.com/search?client=ms-android-samsung-ss&hs=4MBq&sca_esv=47fdd52eba661d26&udm=2&fbs=ABfTbFW4UnGvBVgqDYjq_ksvF_WzL0qSsUjsQCJMDr-_PEHsElEq-XkTNsyVCf0qvOFQ8LnuuR9cbg58QXWYnT3_hh-_8Vra65L0ejGJoDMpRuoUqXVIF_V1qwtmZ6UodYfmS5t1ampSqHH37YJIP7yrNhqvZALTbr6AgQyVLW-7jOCm60GM0QZmIpD5nrIITe4bNjRapHYrjT7mhkWhrplv6Q4gWznEbKk6RbtJriD-sWdUKAYlpdcfps2ib1WuTYnRnbpiFSzl&q=%E1%BA%A3nh%20se&sa=X&ved=2ahUKEwjZz8r5pbOVAxXjiK8BHbtSLkUQtKgLegQIIRAB'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def fetch_image_from_url():
    # Header giả lập trình duyệt di động hoàn chỉnh
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Cookie': 'CONSENT=YES+; NID=511=abcdef123456; SOCS=CAESEwgDEgk0; __Secure-3PSID=; __Secure-3PAPISID=',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?1',
        'Sec-Ch-Ua-Platform': '"Android"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Upgrade-Insecure-Requests': '1'
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BASE_URL, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    print(f"Status: {resp.status}")
                    return None
                html = await resp.text()
                # Lưu html để debug (nếu cần)
                # print(html[:1000])
        except Exception as e:
            print(f"Error fetch: {e}")
            return None

    # Regex mạnh hơn để lấy URL ảnh từ Google Images
    # Tìm tất cả URL ảnh trong thẻ img (dạng data-src hoặc src)
    img_urls = []

    # Pattern 1: src hoặc data-src trong thẻ img
    pattern1 = r'<img[^>]+(?:src|data-src)=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|gif|webp|bmp|svg))["\']'
    matches1 = re.findall(pattern1, html, re.IGNORECASE)
    img_urls.extend(matches1)

    # Pattern 2: URL ảnh trong js hoặc data
    pattern2 = r'["\'](https?://[^"\']+\.(?:jpg|jpeg|png|gif|webp))["\']'
    matches2 = re.findall(pattern2, html, re.IGNORECASE)
    img_urls.extend(matches2)

    # Pattern 3: Tham số imgurl (thường có trong Google Images)
    pattern3 = r'imgurl=([^&]+)'
    matches3 = re.findall(pattern3, html)
    for m in matches3:
        url = urllib.parse.unquote(m)
        if url.startswith('http'):
            img_urls.append(url)

    # Lọc bỏ ảnh rác
    filtered = []
    for url in img_urls:
        if not url:
            continue
        # Bỏ ảnh quảng cáo, logo, icon, base64
        if 'gstatic' in url or 'google' in url or 'favicon' in url or 'logo' in url:
            continue
        if url.startswith('data:') or url.startswith('blob:'):
            continue
        # Ưu tiên ảnh có kích thước lớn (chứa "imgurl" hoặc không có "s1600" quá nhỏ)
        filtered.append(url)

    # Loại bỏ trùng
    unique_urls = list(set(filtered))

    if not unique_urls:
        return None

    # Chọn ngẫu nhiên 1 ảnh
    return random.choice(unique_urls)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

@bot.tree.command(name='ezz', description='Lấy ảnh ngẫu nhiên từ Google')
async def ezz(interaction: discord.Interaction):
    await interaction.response.send_message('Đang tìm ảnh...', ephemeral=False)

    img_url = await fetch_image_from_url()
    if not img_url:
        await interaction.followup.send('Không tìm thấy ảnh. Thử lại sau.')
        return

    # Tải ảnh về
    async with aiohttp.ClientSession() as session:
        try:
            headers_dl = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            async with session.get(img_url, headers=headers_dl, timeout=25) as resp:
                if resp.status != 200:
                    await interaction.followup.send('Không tải được ảnh.')
                    return
                content = await resp.read()
                # Xác định định dạng
                ct = resp.headers.get('Content-Type', '')
                ext = 'jpg'
                if 'png' in ct:
                    ext = 'png'
                elif 'gif' in ct:
                    ext = 'gif'
                elif 'webp' in ct:
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
