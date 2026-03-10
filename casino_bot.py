import asyncio
import json
import logging
import os
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
)

# ════════════════════════════════════════════
#  ⚙️  НАСТРОЙКИ — ЗАПОЛНИ ПЕРЕД ЗАПУСКОМ
# ════════════════════════════════════════════
BOT_TOKEN = "8753830850:AAG5eI7JlkLd6JGqNxM5aq_HNsrRqfG9D1s"   # @BotFather
ADMIN_ID  = 8535260202       # твой Telegram ID (@userinfobot)
# ════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

DB_FILE = "db.json"

# ─── база данных ────────────────────────────
def db_load() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "withdrawals": []}

def db_save(db: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def db_user(db: dict, uid: int, name: str = "") -> dict:
    key = str(uid)
    if key not in db["users"]:
        db["users"][key] = {
            "name": name or str(uid),
            "balance": 0,
            "total_won": 0,
            "total_spent": 0,
            "spins": 0,
        }
    if name:
        db["users"][key]["name"] = name
    return db["users"][key]

# ─── клавиатуры ─────────────────────────────
def kb_main() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎰 Крутить 🎰")],
            [KeyboardButton(text="💸 Лидеры 💸"),
             KeyboardButton(text="📕 Правила 📕")],
        ],
        resize_keyboard=True,
    )

def kb_spin_again() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎰 Крутить ещё раз!", callback_data="spin_again"),
    ]])

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Заявки на вывод", callback_data="adm_withdrawals")],
        [InlineKeyboardButton(text="📢 Рассылка",        callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="📊 Статистика",      callback_data="adm_stats")],
    ])

# ─── слот-машина ────────────────────────────
REELS  = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "7️⃣"]
PRIZES = {
    ("7️⃣","7️⃣","7️⃣"): ("ДЖЕКПОТ 777!", 2),
    ("💎","💎","💎"):    ("Три бриллианта!", 5),
    ("⭐","⭐","⭐"):    ("Три звезды!", 3),
    ("🍇","🍇","🍇"):    ("Три виноградины!", 2),
    ("🍊","🍊","🍊"):    ("Три апельсина!", 2),
    ("🍋","🍋","🍋"):    ("Три лимона!", 2),
    ("🍒","🍒","🍒"):    ("Три вишни!", 2),
}

def spin() -> tuple:
    return tuple(random.choice(REELS) for _ in range(3))

# ─── FSM состояния ──────────────────────────
class BetFSM(StatesGroup):
    waiting_bet = State()

class BroadcastFSM(StatesGroup):
    waiting_text = State()

# ════════════════════════════════════════════
router = Router()
# ════════════════════════════════════════════

# ─── /start ─────────────────────────────────
@router.message(Command("start"))
async def cmd_start(msg: Message):
    db = db_load()
    db_user(db, msg.from_user.id, msg.from_user.first_name)
    db_save(db)
    await msg.answer(
        "╔══════════════════════╗\n"
        "║   🎰  STARS CASINO   ║\n"
        "╚══════════════════════╝\n\n"
        "Добро пожаловать в самое азартное казино Telegram!\n\n"
        "⭐ Ставь звёзды — испытай удачу\n"
        "🏆 Попади в топ лидеров\n"
        "💸 Выводи выигрыш в любое время\n\n"
        "Выбери действие ниже 👇",
        reply_markup=kb_main(),
    )

# ─── Крутить ────────────────────────────────
@router.message(F.text == "🎰 Крутить 🎰")
async def btn_spin(msg: Message, state: FSMContext):
    await state.set_state(BetFSM.waiting_bet)
    await msg.answer(
        "🎰 <b>СЛОТ-МАШИНА</b>\n\n"
        "╔══════════════════╗\n"
        "║   ?  |  ?  |  ?  ║\n"
        "╚══════════════════╝\n\n"
        "💬 Сколько <b>звёзд ⭐</b> хотите поставить?\n"
        "<i>Минимальная ставка — 10 ⭐</i>",
        parse_mode="HTML",
    )

@router.message(BetFSM.waiting_bet)
async def got_bet(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if not text.isdigit() or int(text) < 10:
        await msg.answer(
            "❌ <b>Некорректная ставка.</b>\nВведите число не менее 10:",
            parse_mode="HTML",
        )
        return

    bet = int(text)
    await state.clear()

    prices = [LabeledPrice(label=f"Ставка {bet} ⭐", amount=bet)]
    await msg.answer_invoice(
        title="🎰 Stars Casino",
        description=f"Ставка {bet} звёзд на слот-машину. Удачи! 🍀",
        payload=f"spin|{msg.from_user.id}|{bet}",
        currency="XTR",
        prices=prices,
        provider_token="",
    )

# ─── Pre-checkout ────────────────────────────
@router.pre_checkout_query()
async def precheckout(pcq: PreCheckoutQuery):
    await pcq.answer(ok=True)

# ─── Успешная оплата ─────────────────────────
@router.message(F.successful_payment)
async def paid(msg: Message, bot: Bot):
    payload = msg.successful_payment.invoice_payload
    _, uid_s, bet_s = payload.split("|")
    bet = int(bet_s)
    uid = msg.from_user.id

    db   = db_load()
    user = db_user(db, uid, msg.from_user.first_name)
    user["total_spent"] += bet
    user["spins"]       += 1

    anim = await msg.answer("🎰 Крутим барабаны...\n\n🔄  🔄  🔄")

    reels   = spin()
    display = f"{reels[0]}  {reels[1]}  {reels[2]}"

    if reels in PRIZES:
        label, mult = PRIZES[reels]
        won = bet * mult
        user["total_won"] += won
        user["balance"]   += won
        db_save(db)

        is_jackpot = reels == ("7️⃣","7️⃣","7️⃣")
        header = "🎊 ДЖЕКПОТ!" if is_jackpot else "🎉 ПОБЕДА!"

        result = (
            f"╔══════════════════╗\n"
            f"║  {display}   ║\n"
            f"╚══════════════════╝\n\n"
            f"{header}\n"
            f"🏆 <b>{label}</b>\n\n"
            f"💰 Ставка:    <b>{bet} ⭐</b>\n"
            f"✖️ Множитель: <b>x{mult}</b>\n"
            f"💵 Выигрыш:   <b>{won} ⭐</b>\n\n"
            f"💼 Баланс пополнен! /balance\n"
            f"💸 Вывод: /withdraw"
        )

        if is_jackpot:
            await bot.send_message(
                ADMIN_ID,
                f"🚨 <b>ДЖЕКПОТ 777!</b>\n\n"
                f"👤 {msg.from_user.first_name} (@{msg.from_user.username or '—'}) [ID: {uid}]\n"
                f"💰 Ставка: <b>{bet} ⭐</b>\n"
                f"🏆 Выигрыш: <b>{won} ⭐</b>\n"
                f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode="HTML",
            )
    else:
        db_save(db)
        result = (
            f"╔══════════════════╗\n"
            f"║  {display}   ║\n"
            f"╚══════════════════╝\n\n"
            f"😔 <b>Не повезло...</b>\n\n"
            f"💸 Ставка: <b>{bet} ⭐</b>\n\n"
            f"<i>Попробуй снова — удача близко! 🍀</i>"
        )

    await bot.edit_message_text(
        chat_id=uid,
        message_id=anim.message_id,
        text=result,
        parse_mode="HTML",
        reply_markup=kb_spin_again(),
    )

# ─── Кнопка «Крутить ещё» ────────────────────
@router.callback_query(F.data == "spin_again")
async def cb_spin_again(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(BetFSM.waiting_bet)
    await cb.message.answer(
        "🎰 Сколько <b>звёзд ⭐</b> ставим на этот раз?\n"
        "<i>Минимум — 10 ⭐</i>",
        parse_mode="HTML",
    )

# ─── Лидеры ──────────────────────────────────
@router.message(F.text == "💸 Лидеры 💸")
async def btn_leaders(msg: Message):
    db    = db_load()
    users = db["users"]
    if not users:
        await msg.answer("😴 Пока нет данных о лидерах.", reply_markup=kb_main())
        return

    top    = sorted(users.items(), key=lambda x: x[1]["total_won"], reverse=True)[:10]
    medals = ["🥇","🥈","🥉"] + ["🏅"]*7

    lines = [
        "╔══════════════════════╗",
        "║   💸  ТОП ЛИДЕРОВ   ║",
        "╚══════════════════════╝\n",
    ]
    for i, (_, u) in enumerate(top):
        name = u.get("name", "???")
        lines.append(f"{medals[i]} <b>{i+1}.</b> {name}  —  <b>{u['total_won']} ⭐</b>")

    lines.append("\n<i>Стань первым — крути слот! 🎰</i>")
    await msg.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb_main())

# ─── Правила ─────────────────────────────────
@router.message(F.text == "📕 Правила 📕")
async def btn_rules(msg: Message):
    text = (
        "╔══════════════════════╗\n"
        "║   📕  КАК ИГРАТЬ    ║\n"
        "╚══════════════════════╝\n\n"
        "1️⃣ Нажми <b>🎰 Крутить 🎰</b>\n"
        "2️⃣ Введи сумму ставки (мин. 10 ⭐)\n"
        "3️⃣ Оплати звёздами Telegram\n"
        "4️⃣ Смотри результат!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏆 <b>Таблица выплат:</b>\n\n"
        "7️⃣ 7️⃣ 7️⃣  →  x<b>2</b>  🔥 ДЖЕКПОТ\n"
        "💎 💎 💎  →  x<b>5</b>  💎 Бриллиант\n"
        "⭐ ⭐ ⭐  →  x<b>3</b>  ⭐ Звёзды\n"
        "🍇 🍇 🍇  →  x<b>2</b>\n"
        "🍊 🍊 🍊  →  x<b>2</b>\n"
        "🍋 🍋 🍋  →  x<b>2</b>\n"
        "🍒 🍒 🍒  →  x<b>2</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💸 <b>Вывод выигрыша:</b>\n"
        "Выигрыш зачисляется на баланс.\n"
        "Команда /withdraw — заявка на вывод.\n\n"
        "💼 <b>Баланс:</b>  /balance\n\n"
        "<i>Удачи! 🍀</i>"
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=kb_main())

# ─── /balance ────────────────────────────────
@router.message(Command("balance"))
async def cmd_balance(msg: Message):
    db = db_load()
    u  = db_user(db, msg.from_user.id, msg.from_user.first_name)
    await msg.answer(
        f"╔══════════════════════╗\n"
        f"║   💼  ВАШ БАЛАНС    ║\n"
        f"╚══════════════════════╝\n\n"
        f"⭐ Баланс:          <b>{u['balance']} ⭐</b>\n"
        f"🏆 Всего выиграно:  <b>{u['total_won']} ⭐</b>\n"
        f"💸 Всего потрачено: <b>{u['total_spent']} ⭐</b>\n"
        f"🎰 Прокруток:       <b>{u['spins']}</b>\n\n"
        f"<i>Вывод: /withdraw</i>",
        parse_mode="HTML",
    )

# ─── /withdraw ───────────────────────────────
@router.message(Command("withdraw"))
async def cmd_withdraw(msg: Message, bot: Bot):
    db = db_load()
    u  = db_user(db, msg.from_user.id, msg.from_user.first_name)

    if u["balance"] <= 0:
        await msg.answer(
            "❌ <b>Ваш баланс равен 0 ⭐</b>\n\nСначала выиграйте что-нибудь! 🎰",
            parse_mode="HTML",
        )
        return

    amount = u["balance"]
    wid    = len(db["withdrawals"]) + 1
    db["withdrawals"].append({
        "id":       wid,
        "user_id":  msg.from_user.id,
        "name":     msg.from_user.first_name,
        "username": msg.from_user.username or "",
        "amount":   amount,
        "status":   "pending",
        "date":     datetime.now().strftime("%d.%m.%Y %H:%M"),
    })
    u["balance"] = 0
    db_save(db)

    await msg.answer(
        f"✅ <b>Заявка #{wid} создана!</b>\n\n"
        f"💰 Сумма: <b>{amount} ⭐</b>\n"
        f"⏳ Статус: <b>На рассмотрении</b>\n\n"
        f"<i>Администратор обработает заявку в ближайшее время.</i>",
        parse_mode="HTML",
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"wapprove|{wid}|{msg.from_user.id}|{amount}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"wreject|{wid}|{msg.from_user.id}|{amount}"),
    ]])
    await bot.send_message(
        ADMIN_ID,
        f"💸 <b>Новая заявка на вывод #{wid}</b>\n\n"
        f"👤 {msg.from_user.first_name} (@{msg.from_user.username or '—'}) [ID: {msg.from_user.id}]\n"
        f"💰 Сумма: <b>{amount} ⭐</b>\n"
        f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode="HTML",
        reply_markup=kb,
    )

# ─── /admin ──────────────────────────────────
@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ У вас нет доступа.")
        return
    await msg.answer(
        "╔══════════════════════╗\n"
        "║   🔑  АДМИН ПАНЕЛЬ  ║\n"
        "╚══════════════════════╝\n\n"
        "Выберите раздел:",
        reply_markup=kb_admin(),
    )

@router.callback_query(F.data == "adm_withdrawals")
async def adm_withdrawals(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("❌ Нет доступа.")
    await cb.answer()

    db      = db_load()
    pending = [w for w in db["withdrawals"] if w["status"] == "pending"]

    if not pending:
        return await cb.message.edit_text(
            "✅ <b>Нет активных заявок на вывод.</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="« Назад", callback_data="adm_back")
            ]]),
        )

    lines = ["📋 <b>Заявки на вывод (в ожидании):</b>\n"]
    btns  = []
    for w in pending:
        lines.append(f"#{w['id']} {w['name']} — <b>{w['amount']} ⭐</b> ({w['date']})")
        btns.append([
            InlineKeyboardButton(text=f"✅ #{w['id']}", callback_data=f"wapprove|{w['id']}|{w['user_id']}|{w['amount']}"),
            InlineKeyboardButton(text=f"❌ #{w['id']}", callback_data=f"wreject|{w['id']}|{w['user_id']}|{w['amount']}"),
        ])
    btns.append([InlineKeyboardButton(text="« Назад", callback_data="adm_back")])

    await cb.message.edit_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
    )

@router.callback_query(F.data.startswith("wapprove|"))
async def adm_approve(cb: CallbackQuery, bot: Bot):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("❌")
    _, wid_s, uid_s, amt_s = cb.data.split("|")
    wid, uid, amt = int(wid_s), int(uid_s), int(amt_s)

    db = db_load()
    for w in db["withdrawals"]:
        if w["id"] == wid:
            w["status"] = "approved"
    db_save(db)

    await cb.message.edit_text(
        f"✅ <b>Заявка #{wid} одобрена!</b>\n\n"
        f"Отправьте <b>{amt} ⭐</b> пользователю (ID: <code>{uid}</code>) вручную.",
        parse_mode="HTML",
    )
    await bot.send_message(
        uid,
        f"🎉 <b>Заявка #{wid} одобрена!</b>\n\n"
        f"💰 Сумма <b>{amt} ⭐</b> будет отправлена в ближайшее время.\n\n"
        f"<i>Спасибо за игру! 🎰</i>",
        parse_mode="HTML",
    )

@router.callback_query(F.data.startswith("wreject|"))
async def adm_reject(cb: CallbackQuery, bot: Bot):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("❌")
    _, wid_s, uid_s, amt_s = cb.data.split("|")
    wid, uid, amt = int(wid_s), int(uid_s), int(amt_s)

    db = db_load()
    for w in db["withdrawals"]:
        if w["id"] == wid:
            w["status"] = "rejected"
    user = db_user(db, uid)
    user["balance"] += amt
    db_save(db)

    await cb.message.edit_text(
        f"❌ <b>Заявка #{wid} отклонена.</b>\n\n"
        f"Баланс пользователя восстановлен (+{amt} ⭐).",
        parse_mode="HTML",
    )
    await bot.send_message(
        uid,
        f"❌ <b>Заявка #{wid} отклонена.</b>\n\n"
        f"💼 Ваш баланс восстановлен: <b>+{amt} ⭐</b>\n\n"
        f"<i>По вопросам обращайтесь к администратору.</i>",
        parse_mode="HTML",
    )

@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_ask(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("❌")
    await cb.answer()
    await state.set_state(BroadcastFSM.waiting_text)
    await cb.message.edit_text(
        "📢 <b>Рассылка</b>\n\nВведите текст сообщения для всех пользователей:",
        parse_mode="HTML",
    )

@router.message(BroadcastFSM.waiting_text)
async def adm_broadcast_send(msg: Message, state: FSMContext, bot: Bot):
    if msg.from_user.id != ADMIN_ID:
        return
    await state.clear()
    db   = db_load()
    text = f"📢 <b>Сообщение от администратора:</b>\n\n{msg.text}"
    ok, fail = 0, 0
    for uid_s in db["users"]:
        try:
            await bot.send_message(int(uid_s), text, parse_mode="HTML")
            ok += 1
        except Exception:
            fail += 1
    await msg.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: <b>{ok}</b>\n"
        f"❌ Ошибок:    <b>{fail}</b>",
        parse_mode="HTML",
        reply_markup=kb_admin(),
    )

@router.callback_query(F.data == "adm_stats")
async def adm_stats(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("❌")
    await cb.answer()
    db            = db_load()
    users         = db["users"]
    total_spins   = sum(u["spins"]       for u in users.values())
    total_spent   = sum(u["total_spent"] for u in users.values())
    total_won     = sum(u["total_won"]   for u in users.values())
    pending_count = len([w for w in db["withdrawals"] if w["status"] == "pending"])

    await cb.message.edit_text(
        f"╔══════════════════════╗\n"
        f"║   📊  СТАТИСТИКА    ║\n"
        f"╚══════════════════════╝\n\n"
        f"👤 Пользователей:    <b>{len(users)}</b>\n"
        f"🎰 Всего прокруток:  <b>{total_spins}</b>\n"
        f"💸 Потрачено звёзд:  <b>{total_spent} ⭐</b>\n"
        f"🏆 Выиграно звёзд:   <b>{total_won} ⭐</b>\n"
        f"📋 Заявок на вывод:  <b>{pending_count}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="« Назад", callback_data="adm_back")
        ]]),
    )

@router.callback_query(F.data == "adm_back")
async def adm_back(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "╔══════════════════════╗\n"
        "║   🔑  АДМИН ПАНЕЛЬ  ║\n"
        "╚══════════════════════╝\n\n"
        "Выберите раздел:",
        reply_markup=kb_admin(),
    )

# ════════════════════════════════════════════
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
