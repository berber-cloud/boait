import os
import asyncio
import logging
import socket  # <-- ДОБАВЬ ЭТУ СТРОКУ
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токены
TG_TOKEN = os.getenv("TG_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Настройка сессии для обхода ошибок DNS
connector = aiohttp.TCPConnector(family=socket.AF_INET) # Теперь socket будет виден
session = AiohttpSession(connector=connector)

bot = Bot(token=TG_TOKEN, session=session)
dp = Dispatcher()

# ... дальше весь остальной код (состояния, хендлеры и т.д.)


# Состояния FSM
class BotStates(StatesGroup):
    waiting_for_prompt = State()

# Функция запроса к OpenRouter
async def get_openrouter_response(user_text):
    url = "https://openrouter.ai"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://huggingface.co", # Для OpenRouter
    }
    data = {
        "model": "arcee-ai/trinity-large-preview:free", 
        "messages": [
            {"role": "system", "content": "Ты профессиональный программист. Пиши чистый код с комментариями. Используй Markdown для оформления."},
            {"role": "user", "content": user_text}
        ]
    }
    
    async with aiohttp.ClientSession() as aioseession:
        try:
            async with aioseession.post(url, headers=headers, json=data, timeout=90) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    text_err = await response.text()
                    return f"Ошибка OpenRouter (Код: {response.status}): {text_err[:100]}"
        except Exception as e:
            return f"Ошибка при запросе к нейросети: {str(e)}"

# Клавиатура
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="🚀 Написать запрос ИИ", callback_data="start_ai")
    )
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Я твой ИИ-помощник по коду.\n\n"
        "Нажми кнопку ниже, чтобы я начал генерировать код для тебя:",
        reply_markup=get_main_menu()
    )

@dp.callback_query(F.data == "start_ai")
async def ask_for_prompt(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_prompt)
    await callback.message.edit_text(
        "🤖 Режим ИИ включен.\nОпиши задачу: что нужно закодить?",
        reply_markup=None
    )
    await callback.answer()

@dp.message(BotStates.waiting_for_prompt)
async def handle_ai_request(message: types.Message, state: FSMContext):
    # Индикатор "печатает" в ТГ
    await bot.send_chat_action(message.chat.id, "typing")
    status_msg = await message.answer("⏳ Нейросеть думает... подождите немного.")
    
    answer = await get_openrouter_response(message.text)
    
    await status_msg.delete()
    
    # Разбивка длинных сообщений (лимит ТГ 4096 символов)
    if len(answer) > 4096:
        for x in range(0, len(answer), 4096):
            await message.answer(answer[x:x+4096], parse_mode="Markdown")
    else:
        await message.answer(answer, parse_mode="Markdown")
    
    await message.answer("Готово! Есть еще задачи?", reply_markup=get_main_menu())
    await state.clear()

async def main():
    logger.info("Запуск бота...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
