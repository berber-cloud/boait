import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
import os

# Настройки
BOT_TOKEN = "8642325152:AAGPvLD1iGAeMj5vsa0tSNoyT7Zj61y1Kyw"  # Замените на токен вашего бота
OPENROUTER_API_KEY = "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"  # Замените на ваш API ключ OpenRouter
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
SITE_URL = "https://bothost.ru"  # Замените на URL вашего сайта если есть
APP_NAME = "MyAIBot"  # Название вашего приложения

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния для FSM (Finite State Machine)
class Form(StatesGroup):
    waiting_for_prompt = State()

# Клавиатура с главной кнопкой
def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="🤖 Задать вопрос нейросети",
        callback_data="ask_ai"
    ))
    return builder.as_markup()

# Приветственное сообщение
@dp.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        "👋 Привет! Я бот для общения с нейросетями через OpenRouter.\n\n"
        "Я могу помочь тебе с любыми вопросами - от простых до сложных.\n"
        "Просто нажми на кнопку ниже и напиши свой запрос!"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

# Обработчик нажатия на кнопку
@dp.callback_query(F.data == "ask_ai")
async def process_ask_ai(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✍️ Отправьте ваш запрос в следующем сообщении:",
        reply_markup=None
    )
    await state.set_state(Form.waiting_for_prompt)
    await callback.answer()

# Функция для запроса к OpenRouter API
async def query_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": SITE_URL,
        "X-Title": APP_NAME,
    }
    
    # Выберите модель (можно изменить на другую)
    data = {
        "model": "openai/gpt-3.5-turbo",  # Бесплатная модель
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    return f"❌ Ошибка API: {response.status}\n{error_text}"
    except asyncio.TimeoutError:
        return "❌ Превышено время ожидания ответа от нейросети"
    except Exception as e:
        return f"❌ Произошла ошибка: {str(e)}"

# Обработчик запроса пользователя
@dp.message(Form.waiting_for_prompt)
async def process_prompt(message: Message, state: FSMContext):
    prompt = message.text
    
    # Отправляем уведомление о начале обработки
    processing_msg = await message.answer("⏳ Нейросеть думает...")
    
    # Получаем ответ от нейросети
    response = await query_openrouter(prompt)
    
    # Удаляем уведомление о обработке
    await processing_msg.delete()
    
    # Отправляем ответ
    await message.answer(
        f"🤖 **Ответ нейросети:**\n\n{response}",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    
    # Завершаем состояние
    await state.clear()

# Обработчик сообщений вне состояния
@dp.message()
async def handle_other_messages(message: Message):
    await message.answer(
        "Нажмите на кнопку, чтобы задать вопрос нейросети:",
        reply_markup=get_main_keyboard()
    )

# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🔍 **Как пользоваться ботом:**\n\n"
        "1. Нажмите на кнопку «Задать вопрос нейросети»\n"
        "2. Отправьте свой запрос\n"
        "3. Дождитесь ответа\n\n"
        "📝 **Доступные команды:**\n"
        "/start - Запустить бота\n"
        "/help - Показать эту справку\n"
        "/cancel - Отменить текущий запрос"
    )
    await message.answer(help_text, parse_mode="Markdown")

# Обработчик команды /cancel
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного запроса для отмены")
        return
    
    await state.clear()
    await message.answer(
        "✅ Текущий запрос отменен. Можете начать новый!",
        reply_markup=get_main_keyboard()
    )

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())