import logging
import os
import traceback
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook
from openai import OpenAI
from dotenv import load_dotenv

# Load env variables
load_dotenv("mood_bot.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Logging
logging.basicConfig(level=logging.INFO)

# Webhook settings
WEBHOOK_HOST = "https://mood-bot-frbb.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 5000))

# Init bot and dispatcher
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# Init OpenRouter client
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)
logging.info(f"🔑 OpenRouter key starts with: {OPENROUTER_API_KEY[:8]}...")

# Keyboard
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("🍽 Хочу в ресторан"))
main_kb.add(KeyboardButton("📍 Отправить геолокацию", request_location=True))
main_kb.add(KeyboardButton("🎬 Пойду в кино"))
main_kb.add(KeyboardButton("🎭 Театр / выставка"))
main_kb.add(KeyboardButton("🤷‍♂️ Мне скучно"))

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    logging.info("▶️ /start")
    await message.answer("Привет! Что хочешь сегодня сделать?", reply_markup=main_kb)

@dp.message_handler(content_types=types.ContentType.LOCATION)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    logging.info(f"📍 Геолокация получена: {lat}, {lon}")
    await message.reply("Ищу рестораны рядом... 🍽", reply_markup=main_kb)

    try:
        url = (
            f"https://nominatim.openstreetmap.org/search?"
            f"q=restaurant&format=json&limit=5&lat={lat}&lon={lon}"
        )
        headers = {"User-Agent": "MoodBot"}
        async with httpx.AsyncClient() as session:
            response = await session.get(url, headers=headers)
            data = response.json()

        logging.info("📡 Ответ от OpenStreetMap:")
        logging.info(data)

        if not data:
            await message.reply("Не удалось найти рестораны рядом 😕", reply_markup=main_kb)
            return

        for place in data:
            name = place.get("display_name", "Без названия")
            lat = place.get("lat")
            lon = place.get("lon")
            maps_url = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=18/{lat}/{lon}"
            text = f"🍴 <b>{name}</b>\n🗺 <a href='{maps_url}'>Открыть на карте</a>"
            await message.reply(text, parse_mode="HTML", reply_markup=main_kb)

    except Exception:
        await message.reply("Произошла ошибка при поиске ресторанов 😞", reply_markup=main_kb)
        logging.error("❌ Ошибка при работе с OSM:\n" + traceback.format_exc())

@dp.message_handler()
async def handle_text(message: types.Message):
    user_text = message.text.lower()
    logging.info(f"💬 Текст от пользователя: {user_text}")

    if "ресторан" in user_text:
        await message.reply("Отправь геолокацию кнопкой ниже 📍", reply_markup=main_kb)
    elif "кино" in user_text:
        await message.reply("Сейчас в кино: «Дюна 2», «Оппенгеймер»... (в следующей версии)", reply_markup=main_kb)
    elif "театр" in user_text or "выставка" in user_text:
        await message.reply("Афиша на сегодня: ... (в следующей версии)", reply_markup=main_kb)
    else:
        try:
            response = client.chat.completions.create(
                model="openchat/openchat-7b:free",
                messages=[
                    {"role": "system", "content": "Ты дружелюбный помощник, советующий, как провести досуг в городе."},
                    {"role": "user", "content": user_text}
                ]
            )
            idea = response.choices[0].message.content
            await message.reply(idea, reply_markup=main_kb)
        except Exception:
            await message.reply("Произошла ошибка при обращении к GPT 😕", reply_markup=main_kb)
            logging.error("GPT error:\n" + traceback.format_exc())

async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
