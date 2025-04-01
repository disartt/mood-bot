import logging
import os
import traceback
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook
from dotenv import load_dotenv

# Load env variables
load_dotenv("mood_bot.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

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

# Хранилище последнего типа запроса
user_last_query = {}

# Кнопки
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(
    KeyboardButton("🍽 Ресторан"),
    KeyboardButton("🎬 Кино")
)
main_kb.add(
    KeyboardButton("🎭 Театр"),
    KeyboardButton("🖼 Музей")
)
main_kb.add(
    KeyboardButton("🤷‍♂️ Мне скучно"),
    KeyboardButton("📍 Отправить геолокацию", request_location=True)
)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Что хочешь сегодня сделать?", reply_markup=main_kb)

@dp.message_handler(content_types=types.ContentType.LOCATION)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    user_id = message.from_user.id

    query_type = user_last_query.get(user_id, "restaurant")
    await message.reply(f"Ищу поблизости: {query_type}…", reply_markup=main_kb)

    try:
        delta = 0.01
        left = lon - delta
        top = lat + delta
        right = lon + delta
        bottom = lat - delta

        url = (
            f"https://nominatim.openstreetmap.org/search?"
            f"q={query_type}&format=json&limit=5&"
            f"viewbox={left},{top},{right},{bottom}&bounded=1"
        )
        headers = {"User-Agent": "MoodBot"}
        async with httpx.AsyncClient() as session:
            response = await session.get(url, headers=headers)
            data = response.json()

        if not data:
            await message.reply("Ничего не найдено поблизости 😕", reply_markup=main_kb)
            return

        for place in data:
            name = place.get("display_name", "Без названия")
            place_lat = place.get("lat")
            place_lon = place.get("lon")
            maps_url = f"https://www.openstreetmap.org/?mlat={place_lat}&mlon={place_lon}#map=18/{place_lat}/{place_lon}"
            text = f"📍 <b>{name}</b>\n<a href='{maps_url}'>Открыть на карте</a>"
            await message.reply(text, parse_mode="HTML", reply_markup=main_kb)

    except Exception:
        await message.reply("Произошла ошибка при поиске 😞", reply_markup=main_kb)
        logging.error("Ошибка:\n" + traceback.format_exc())

@dp.message_handler()
async def handle_text(message: types.Message):
    text = message.text.lower()
    user_id = message.from_user.id

    if "ресторан" in text:
        user_last_query[user_id] = "restaurant"
        await message.reply("Отправь геолокацию, и я найду рестораны рядом 📍", reply_markup=main_kb)
    elif "кино" in text:
        user_last_query[user_id] = "cinema"
        await message.reply("Отправь геолокацию, и я найду кино рядом 📍", reply_markup=main_kb)
    elif "театр" in text:
        user_last_query[user_id] = "theatre"
        await message.reply("Отправь геолокацию, и я найду театры поблизости 🎭", reply_markup=main_kb)
    elif "музей" in text:
        user_last_query[user_id] = "museum"
        await message.reply("Отправь геолокацию, и я найду музеи поблизости 🖼", reply_markup=main_kb)
    elif "скучно" in text:
        await message.reply("Попробуй выбрать что-нибудь интересное из меню!", reply_markup=main_kb)
    else:
        await message.reply("Выбери вариант из меню или отправь геолокацию.", reply_markup=main_kb)

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
