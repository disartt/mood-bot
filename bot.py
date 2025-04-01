import logging
import os
import traceback
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv("mood_bot.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

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
    logging.info("Received /start")
    await message.answer("Привет! Что хочешь сегодня сделать?", reply_markup=main_kb)

@dp.message_handler(content_types=types.ContentType.LOCATION)
async def handle_location(message: types.Message):
    lat = message.location.latitude
    lon = message.location.longitude
    logging.info(f"📍 Получена геолокация: {lat}, {lon}")
    await message.reply("Ищу рестораны рядом... 🍽", reply_markup=main_kb)

    try:
        url = (
            f"https://search-maps.yandex.ru/v1/?apikey={YANDEX_API_KEY}"
            f"&text=ресторан&type=biz&lang=ru_RU&ll={lon},{lat}&spn=0.01,0.01&results=5"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

        if not data.get("features"):
            await message.reply("Не удалось найти рестораны рядом 😕", reply_markup=main_kb)
            return

        for place in data["features"]:
            props = place["properties"]
            name = props["CompanyMetaData"]["name"]
            address = props["CompanyMetaData"].get("address", "Адрес неизвестен")
            url = props["CompanyMetaData"].get("url", "")
            msg = f"🍴 <b>{name}</b>\n📍 {address}"
            if url:
                msg += f"\n🌐 <a href='{url}'>Сайт</a>"
            await message.reply(msg, parse_mode="HTML", reply_markup=main_kb)

    except Exception:
        await message.reply("Произошла ошибка при поиске ресторанов 😞", reply_markup=main_kb)
        logging.error("Yandex API error:\n" + traceback.format_exc())

@dp.message_handler()
async def handle_text(message: types.Message):
    user_text = message.text.lower()
    logging.info(f"📝 Получено сообщение: {user_text}")

    if "ресторан" in user_text:
        logging.info("🍽 Запрос: ресторан")
        await message.reply("Отправь геолокацию кнопкой ниже 📍", reply_markup=main_kb)
    elif "кино" in user_text:
        logging.info("🎬 Запрос: кино")
        await message.reply("Сейчас в кино: «Дюна 2», «Оппенгеймер»... (в следующей версии)", reply_markup=main_kb)
    elif "театр" in user_text or "выставка" in user_text:
        logging.info("🎭 Запрос: театр/выставка")
        await message.reply("Афиша на сегодня: ... (в следующей версии)", reply_markup=main_kb)
    else:
        try:
            logging.info("🤖 GPT-запрос")
            response = client.chat.completions.create(
                model="openchat/openchat-7b:free",
                messages=[
                    {"role": "system", "content": "Ты дружелюбный помощник, советующий, как провести досуг в городе. Отвечай кратко и понятно, не более 4 пунктов."},
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
