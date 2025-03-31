
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import openai
from dotenv import load_dotenv

# Load env variables from custom file
load_dotenv("mood_bot.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setup logging
logging.basicConfig(level=logging.INFO)

# Init bot and dispatcher
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# Configure OpenAI with project ID
client = openai.OpenAI(
    api_key=OPENAI_API_KEY,
    project="proj_s6yqUdaRJg0KiMb3dEGZCrVM"
)

# Simple keyboard
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("🍽 Хочу в ресторан"))
main_kb.add(KeyboardButton("🎬 Пойду в кино"))
main_kb.add(KeyboardButton("🎭 Театр / выставка"))
main_kb.add(KeyboardButton("🤷‍♂️ Мне скучно"))

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Что хочешь сегодня сделать?", reply_markup=main_kb)

@dp.message_handler()
async def handle_text(message: types.Message):
    user_text = message.text.lower()

    if "ресторан" in user_text:
        await message.reply("Вот несколько ресторанов рядом с тобой... (в следующей версии)")
    elif "кино" in user_text:
        await message.reply("Сейчас в кино: «Дюна 2», «Оппенгеймер»... (в следующей версии)")
    elif "театр" in user_text or "выставка" in user_text:
        await message.reply("Афиша на сегодня: ... (в следующей версии)")
    else:
        try:
            # GPT-помощник: дружелюбный советник по досугу
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты дружелюбный помощник, советующий, как провести досуг в городе."},
                    {"role": "user", "content": user_text}
                ]
            )
            idea = response.choices[0].message.content
            await message.reply(idea)
        except Exception as e:
            await message.reply("Произошла ошибка при обращении к GPT 😕")
            logging.error(f"GPT error: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
