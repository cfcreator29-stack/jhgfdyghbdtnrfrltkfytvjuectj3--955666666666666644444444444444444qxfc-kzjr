"""
🎰 Casino Slot Bot
==================
Бот следит за стикерами автомата 🎰 в группе.
Если выпало 777 — поздравляет победителя и пишет админу.

Установка:
    pip install aiogram==3.* python-dotenv

Запуск:
    python casino_bot.py
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReactionTypeEmoji
from aiogram.filters import Filter
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

# ─────────────────────────────────────────
#  ⚙️  НАСТРОЙКИ — замените на свои значения
# ─────────────────────────────────────────

BOT_TOKEN   = "8753830850:AAG5eI7JlkLd6JGqNxM5aq_HNsrRqfG9D1s"          # токен от @BotFather
GROUP_ID    = -1003874655092             # ID вашей группы (отрицательное число)
ADMIN_ID    = 8535260202                  # Telegram ID администратора

PRIZE_STARS = 100                        # сколько звёзд выигрывает победитель

# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
#  Фильтр: сообщение пришло только из нашей группы
# ──────────────────────────────────────────────────────────
class OnlyOurGroup(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.id == GROUP_ID


# ──────────────────────────────────────────────────────────
#  Создаём бота и диспетчер
# ──────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher()


# ──────────────────────────────────────────────────────────
#  Обработчик сообщений с кубиком-слотом 🎰
#  dice.emoji == "🎰"  и  dice.value == 64  →  777
#  (Telegram кодирует 777 как значение 64 для эмодзи 🎰)
# ──────────────────────────────────────────────────────────
@dp.message(OnlyOurGroup(), F.dice.emoji == "🎰")
async def handle_slot(message: Message) -> None:
    value      = message.dice.value          # число от 1 до 64
    user       = message.from_user
    user_name  = user.full_name
    user_link  = f'<a href="tg://user?id={user.id}">{user_name}</a>'

    log.info(
        "Слот от %s (id=%s) в чате %s → значение %s",
        user_name, user.id, message.chat.id, value
    )

    # 777 в Telegram = значение 64 для эмодзи 🎰
    if value == 64:
        # 1. Ставим реакцию 🎉 на сообщение победителя
        try:
            await bot.set_message_reaction(
                chat_id    = message.chat.id,
                message_id = message.message_id,
                reaction   = [ReactionTypeEmoji(emoji="🎉")],
                is_big     = True
            )
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            log.warning("Не удалось поставить реакцию: %s", e)

        # 2. Поздравляем в группе (ответом на сообщение)
        congrats_text = (
            f"🎰 <b>ДЖЕКПОТ!</b> 🎰\n\n"
            f"🥳 Поздравляем, {user_link}!\n"
            f"Вы выбили <b>777</b> и выиграли "
            f"<b>{PRIZE_STARS} ⭐ звёзд</b>!\n\n"
            f"Они поступят в тичении 15 минут."
        )
        await message.reply(congrats_text, parse_mode="HTML")

        # 3. Уведомляем администратора в личку
        chat_title = message.chat.title or str(message.chat.id)
        msg_link   = (
            f"https://t.me/c/{str(message.chat.id).replace('-100', '')}"
            f"/{message.message_id}"
        )

        admin_text = (
            f"🚨 <b>Новый победитель в «{chat_title}»!</b>\n\n"
            f"👤 Игрок: {user_link}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"🎰 Результат: <b>777 (ДЖЕКПОТ)</b>\n"
            f"🏆 Приз: <b>{PRIZE_STARS} ⭐ звёзд</b>\n"
            f"🔗 <a href='{msg_link}'>Перейти к сообщению</a>"
        )
        try:
            await bot.send_message(
                chat_id    = ADMIN_ID,
                text       = admin_text,
                parse_mode = "HTML"
            )
            log.info("Уведомление отправлено администратору (id=%s)", ADMIN_ID)
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            log.error(
                "Не удалось написать администратору (id=%s): %s\n"
                "Убедитесь, что администратор начал диалог с ботом.",
                ADMIN_ID, e
            )

    else:
        log.info("Не 777 (значение=%s) — пропускаем.", value)


# ──────────────────────────────────────────────────────────
#  Запуск
# ──────────────────────────────────────────────────────────
async def main() -> None:
    log.info("Бот запущен. Ожидаю слоты 🎰 в группе %s …", GROUP_ID)
    await dp.start_polling(bot, allowed_updates=["message"])


if __name__ == "__main__":
    asyncio.run(main())
