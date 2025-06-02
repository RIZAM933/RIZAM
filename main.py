import discord
from discord.ext import commands
from datetime import datetime, timedelta
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from io import BytesIO
import pytesseract
import asyncio
import json
import os
import re

# ==== Настройки ====
TOKEN = os.getenv("DISCORD_TOKEN")
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TARGET_CHANNEL_ID = 1378337768958332968
ROLE_ID = 1378338801654693928
LOG_CHANNEL_ID = 1378338260547534908

DB_FILE = "verified_users.json"



# ==== Данные ====
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        verified_users = json.load(f)
else:
    verified_users = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ALLOWED_TAGS = [
    r"\[?~?GG~?\]?",
    r"\[?~?XxX~?\]?",
    r"Gladiators\s+of\s+God",
    r"GG",
]

def contains_tag(text):
    text = text.upper()
    for pattern in ALLOWED_TAGS:
        if re.search(pattern.upper(), text):
            return True
    return False

def extract_game_id(text):
    text = text.replace('1D', 'ID').replace('lD', 'ID').replace('ld', 'ID').replace('(ID', 'ID').replace('I D', 'ID')
    # Добавлены все возможные формы: ID, !D, io, Co, co, etc.
    match = re.search(r"(?:[!Iil1lоо0]{1}[dD]|io|co)[:：\s]*([0-9]{9})", text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(verified_users, f, ensure_ascii=False, indent=2)

async def log(guild, message):
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(message)

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != TARGET_CHANNEL_ID:
        return

    user_id = str(message.author.id)
    now = datetime.utcnow()

    # Проверка повтора до истечения 30 дней
    for gid, data in verified_users.items():
        if data["discord_id"] == user_id:
            expires = datetime.fromisoformat(data["expires_at"])
            if now < expires:
                remaining = expires - now
                days_left = remaining.days
                await message.reply(f"❌ Ты уже верифицирован. Повторная отправка через {days_left} дней.")
                return

    for attachment in message.attachments:
        if not attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        image_data = await attachment.read()
        image = Image.open(BytesIO(image_data)).convert("L")
        image = ImageOps.autocontrast(image)
        image = ImageEnhance.Contrast(image).enhance(4.0)
        for _ in range(2):
            image = image.filter(ImageFilter.SHARPEN)
        image = image.point(lambda x: 0 if x < 150 else 255, '1')

        text = pytesseract.image_to_string(image, lang="eng+rus", config='--psm 6')
        await log(message.guild, f"📄 OCR текст от {message.author.mention}:\n```\n{text}\n```")

        if not contains_tag(text):
            await message.reply("❌ Ты не состоишь в альянсе (тег не найден).")
            return

        game_id = extract_game_id(text)
        if not game_id:
            await message.reply("❌ ID не найден на скрине.")
            await log(message.guild, f"❗ {message.author.mention}: ID не найден")
            return

        existing = verified_users.get(game_id)
        if existing:
            if existing["discord_id"] != user_id:
                if not message.author.guild_permissions.administrator:
                    await message.author.timeout(timedelta(days=20), reason="Обман: чужой ID")
                    await log(message.guild, f"🚨 Обман от {message.author.mention} → чужой ID: `{game_id}`")
                    await message.reply("🚫 Попытка использовать чужой профиль — выданы санкции.")
                    return
            else:
                await message.reply("✅ Повторная верификация подтверждена.")
                return

        # ✅ Успешная новая регистрация
        role = message.guild.get_role(ROLE_ID)
        if role:
            await message.author.add_roles(role)
        await message.add_reaction("✅")
        await message.reply("✅ Верификация успешна! Роль выдана.")

        verified_users[game_id] = {
            "discord_id": user_id,
            "username": str(message.author),
            "verified_at": now.isoformat(),
            "expires_at": (now + timedelta(days=30)).isoformat()
        }
        save_db()

        async def remove_role_later():
            await asyncio.sleep(30 * 24 * 60 * 60)
            member = message.guild.get_member(message.author.id)
            if member and role in member.roles:
                await member.remove_roles(role)
                try:
                    await member.send("🔄 Срок верификации истёк. Пожалуйста, отправь новый скрин.")
                except discord.Forbidden:
                    pass

        asyncio.create_task(remove_role_later())

@bot.event
async def on_ready():
    print(f"✅ Бот запущен как {bot.user}")

bot.run(TOKEN)
