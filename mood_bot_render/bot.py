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
FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY")

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

user_last_query = {}

# Keyboard
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

async def search_foursquare_places(lat, lon, query, message):
    try:
        headers = {
            "Authorization": FOURSQUARE_API_KEY,
            "Accept": "application/json"
        }
        params = {
            "ll": f"{lat},{lon}",
            "query": query,
            "limit": 5,
            "sort": "RELEVANCE",
            "radius": 3000  # ← Расширенный радиус поиска (в метрах)
        }
        url = "https://api.foursquare.com/v3/places/search"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            data = response.json()

        if "results" not in data or not data["results"]:
            await message.reply("Ничего не найдено поблизости 😕", reply_markup=main_kb)
            return

        for place in data["results"]:
            name = place.get("name", "Без названия")
            location = place.get("location", {})
            address = location.get("formatted_address", "Адрес неизвестен")
            lat = location.get("lat")
            lon = location.get("lng")
            maps_url = f"https://maps.google.com/?q={lat},{lon}"
            rating = place.get("rating", "—")
            text = f"📍 <b>{name}</b>\n📍 {address}\n⭐ Рейтинг: {rating}\n<a href='{maps_url}'>Открыть на карте</a>"
            await message.reply(text, parse_mode="HTML", reply_markup=main_kb)

        await message.reply("🔁 Хочешь поискать ещё? Выбери категорию ниже 👇", reply_markup=main_kb)

    except Exception:
        await message.reply("Произошла ошибка при поиске 😞", reply_markup=main_kb)
        logging.error("Foursquare Error:\n" + traceback.format_exc())

@dp.message_handler(content_types=types.ContentType.LOCATION)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    user_id = message.from_user.id
    query = user_last_query.get(user_id, "restaurant")
    await message.reply(f"🔎 Ищу поблизости: {query}", reply_markup=main_kb)
    await search_foursquare_places(lat, lon, query, message)

@dp.message_handler()
async def handle_text(message: types.Message):
    text = message.text.lower()
    user_id = message.from_user.id

    if "ресторан" in text:
        user_last_query[user_id] = "restaurant"
        await message.reply("Отправь геолокацию или напиши адрес — и я найду лучшие рестораны рядом 📍", reply_markup=main_kb)
    elif "кино" in text:
        user_last_query[user_id] = "cinema"
        await message.reply("Отправь геолокацию или напиши адрес — и я найду кино рядом 🎬", reply_markup=main_kb)
    elif "театр" in text:
        user_last_query[user_id] = "theatre"
        await message.reply("Отправь геолокацию или напиши адрес — и я найду театр рядом 🎭", reply_markup=main_kb)
    elif "музей" in text:
        user_last_query[user_id] = "museum"
        await message.reply("Отправь геолокацию или напиши адрес — и я найду музей рядом 🖼", reply_markup=main_kb)
    elif "скучно" in text:
        await message.reply("Выбери что-нибудь из меню и проведи время с удовольствием!", reply_markup=main_kb)
    else:
        query = user_last_query.get(user_id)
        if not query:
            await message.reply("Сначала выбери категорию досуга из меню выше ☝️", reply_markup=main_kb)
            return

        try:
            headers = {"User-Agent": "MoodBot"}
            url = f"https://nominatim.openstreetmap.org/search?q={text}&format=json&limit=1"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers)
                results = resp.json()

            if not results:
                await message.reply("Не удалось найти такое место. Попробуй другой адрес 🗺", reply_markup=main_kb)
                return

            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            await message.reply(f"📍 Нашёл: {results[0]['display_name']}\n🔎 Ищу поблизости: {query}", reply_markup=main_kb)
            await search_foursquare_places(lat, lon, query, message)

        except Exception:
            await message.reply("Ошибка при определении местоположения 😞", reply_markup=main_kb)
            logging.error("GeoText Error:\n" + traceback.format_exc())

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
