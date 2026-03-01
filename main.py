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

# Настройки - лучше использовать переменные окружения на BotHost
BOT_TOKEN = "8642325152:AAGPvLD1iGAeMj5vsa0tSNoyT7Zj61y1Kyw"  # Замените на токен вашего бота
OPENROUTER_API_KEY = "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"  # Замените на ваш API ключ OpenRouter

# Правильные заголовки для OpenRouter
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://bothost.ru",  # Можно указать любой URL
    "X-Title": "Telegram AI Bot"
}

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния для FSM
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

# Функция для проверки API ключа
async def check_api_key():
    """Проверяет валидность API ключа OpenRouter"""
    test_headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers=test_headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"API ключ валиден. Данные: {data}")
                    return True, data
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка проверки API ключа: {response.status} - {error_text}")
                    return False, f"Ошибка {response.status}: {error_text}"
    except Exception as e:
        logger.error(f"Исключение при проверке API ключа: {e}")
        return False, str(e)

# Функция для получения списка доступных моделей
async def get_available_models():
    """Получает список доступных моделей от OpenRouter"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                else:
                    logger.error(f"Ошибка получения моделей: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Исключение при получении моделей: {e}")
        return []

# Улучшенная функция для запроса к OpenRouter API
async def query_openrouter(prompt: str) -> str:
    """Отправляет запрос к OpenRouter и возвращает ответ"""
    
    # Проверяем API ключ перед отправкой
    is_valid, key_info = await check_api_key()
    if not is_valid:
        return f"❌ Проблема с API ключом OpenRouter: {key_info}\n\nПроверьте правильность ключа в настройках бота."
    
    # Пробуем разные модели, если первая не сработает
    models_to_try = [
        "openai/gpt-3.5-turbo",
        "anthropic/claude-3-haiku",
        "meta-llama/llama-3-8b-instruct",
        "mistralai/mistral-7b-instruct",
        "google/gemini-pro"
    ]
    
    for model in models_to_try:
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        try:
            logger.info(f"Пробуем модель: {model}")
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OPENROUTER_API_URL,
                    headers=OPENROUTER_HEADERS,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result["choices"][0]["message"]["content"]
                        return f"**Ответ от {model}:**\n\n{answer}"
                    elif response.status == 401:
                        # Если проблема с авторизацией, дальше пробовать бесполезно
                        error_text = await response.text()
                        logger.error(f"Ошибка авторизации: {error_text}")
                        return f"❌ Ошибка авторизации OpenRouter. Проверьте API ключ.\n\nДетали: {error_text}"
                    else:
                        error_text = await response.text()
                        logger.warning(f"Модель {model} не сработала: {response.status} - {error_text}")
                        continue  # Пробуем следующую модель
                        
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут при использовании модели {model}")
            continue
        except Exception as e:
            logger.warning(f"Ошибка при использовании модели {model}: {e}")
            continue
    
    return "❌ Не удалось получить ответ от нейросети. Попробуйте позже или проверьте настройки OpenRouter."

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
        response,
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
        "/cancel - Отменить текущий запрос\n"
        "/check - Проверить статус API"
    )
    await message.answer(help_text, parse_mode="Markdown")

# Команда для проверки статуса API
@dp.message(Command("check"))
async def cmd_check(message: Message):
    status_msg = await message.answer("🔍 Проверяю подключение к OpenRouter...")
    
    # Проверяем API ключ
    is_valid, key_info = await check_api_key()
    
    if is_valid:
        # Получаем список доступных моделей
        models = await get_available_models()
        models_count = len(models)
        
        status_text = (
            "✅ **Статус OpenRouter:**\n\n"
            f"🔑 API ключ: **Работает**\n"
            f"📊 Доступно моделей: **{models_count}**\n"
            f"💰 Баланс: **{key_info.get('data', {}).get('credits', 'Неизвестно')}**\n\n"
            "Бот готов к работе!"
        )
        await status_msg.edit_text(status_text, parse_mode="Markdown")
    else:
        await status_msg.edit_text(
            f"❌ **Проблема с OpenRouter:**\n\n{key_info}\n\n"
            "Проверьте API ключ в настройках бота.",
            parse_mode="Markdown"
        )

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
    # Проверяем подключение при старте
    logger.info("Проверка подключения к OpenRouter...")
    is_valid, key_info = await check_api_key()
    if is_valid:
        logger.info("✅ Подключение к OpenRouter установлено")
        models = await get_available_models()
        logger.info(f"📊 Доступно моделей: {len(models)}")
    else:
        logger.error(f"❌ Ошибка подключения к OpenRouter: {key_info}")
        logger.warning("Бот запущен, но может не работать с OpenRouter")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())