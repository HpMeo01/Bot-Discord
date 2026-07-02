import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import random
import os
import asyncio
import json
import tempfile
import subprocess

# --- Cấu hình ---
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("Missing DISCORD_TOKEN")

BASE_URL = 'https://vi.xhwide.com/'
MAX_DURATION = 120  # 2 phút
QUALITY_PREFERENCE = 'medium'  # 'low', 'medium', 'high'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# --- Lấy metadata video bằng yt-dlp ---
async def get_video_metadata(url):
    cmd = [
        'yt-dlp',
        '--skip-download',
        '--dump-json',
        '--no-warnings',
        '--quiet',
        url
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate(timeout=30)
        if proc.returncode != 0:
            return None
        data = json.loads(stdout.decode('utf-8'))
        duration = data.get('duration', 0)
        formats = []
        for f in data.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                height = f.get('height', 0)
                if height:
                    formats.append({
                        'url': f['url'],
                        'height': height,
                        'width': f.get('width', 0),
                        'ext': f.get('ext', 'mp4'),
                        'filesize': f.get('filesize', 0)
                    })
        formats.sort(key=lambda x: x['height'])
        return {
            'duration': duration,
            'formats': formats
        }
    except Exception:
        return None

# --- Lấy danh sách link video ---
async def fetch_filtered_video_links():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BASE_URL, headers=headers, timeout=15) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        except Exception:
            return []

    soup = BeautifulSoup(html, 'html.parser')
    raw_links = set()
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if '/watch?v=' in href or '/video/' in href:
            if not href.startswith('http'):
                href = 'https://vi.xhwide.com' + href if href.startswith('/') else BASE_URL + href
            raw_links.add(href)

    valid_links = []
    for link in raw_links:
        meta = await get_video_metadata(link)
        if not meta:
            continue
        duration = meta.get('duration', 0)
        if duration == 0 or duration > MAX_DURATION:
            continue
        formats = meta.get('formats', [])
        selected_url = None
        if QUALITY_PREFERENCE == 'low':
            for f in formats:
                if f['height'] <= 480:
                    selected_url = f['url']
                    break
            if not selected_url and formats:
                selected_url = formats[0]['url']
        elif QUALITY_PREFERENCE == 'medium':
            candidates = [f for f in formats if 480 <= f['height'] <= 720]
            if candidates:
                candidates.sort(key=lambda x: abs(x['height'] - 480))
                selected_url = candidates[0]['url']
            elif formats:
                selected_url = formats[0]['url']
        else:  # high
            if formats:
                selected_url = formats[-1]['url']
        if selected_url:
            valid_links.append(selected_url)
    return valid_links

# --- Tải video ---
async def download_video(video_url, save_path):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': BASE_URL
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(video_url, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    return None
                content = await resp.read()
                with open(save_path, 'wb') as f:
                    f.write(content)
                return save_path
        except Exception:
            return None

# --- Lệnh /sex ---
@bot.command(name='sex')
async def sex_command(ctx):
    await ctx.send('Đang tìm video phù hợp (1-2 phút, chất lượng trung bình)...')

    video_urls = await fetch_filtered_video_links()
    if not video_urls:
        await ctx.send('Không tìm thấy video nào đáp ứng tiêu chí.')
        return

    chosen_url = random.choice(video_urls)

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
        tmp_path = tmp.name

    saved_path = await download_video(chosen_url, tmp_path)
    if not saved_path:
        await ctx.send('Tải video thất bại.')
        return

    try:
        with open(saved_path, 'rb') as f:
            await ctx.send(file=discord.File(f, 'video.mp4'))
    except Exception as e:
        await ctx.send(f'Lỗi gửi video: {e}')
    finally:
        if os.path.exists(saved_path):
            os.remove(saved_path)

bot.run(TOKEN)
