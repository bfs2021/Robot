from aiogram import types
from aiogram.dispatcher.filters import Command

from keyboards.inline.buttons import report_btn, report_button
from loader import bot, dp
from utils.db_api.database import Groups, Payments

payments = Payments()
groups = Groups()

# ── helpers ──────────────────────────────────────────────────────────────────

async def _build_report(user_id: int, period: str) -> str:
    """
    Собирает текст отчёта для указанного периода.

    :param user_id: Telegram user_id владельца групп.
    :param period:  'monthly' | 'yearly'
    :raises ValueError: если period неизвестен.
    """
    if period == "monthly":
        header = "🗓Sizning <b>oylik</b> hisobotlaringiz."
        get_amount = payments.get_monthly_amount
    elif period == "yearly":
        header = "🗓Sizning <b>yillik</b> hisobotlaringiz."
        get_amount = payments.get_yearly_amount
    else:
        raise ValueError(f"Unknown period: {period!r}")

    chat_ids: list[int] = await groups.get_all_chat_ids(user_id)  # await

    if not chat_ids:
        return f"<b>{header}</b>\n\nℹ️ Hech qanday guruh topilmadi."

    lines: list[str] = [f"<b>{header}</b>\n"]

    for chat_id in chat_ids:
        try:
            chat = await bot.get_chat(chat_id)
            chat_title = chat.title or "—"
        except Exception:
            # Бот мог быть кикнут или группа удалена
            chat_title = f"[ID: {chat_id}]"

        amount: int = await get_amount(chat_id)
        lines.append(
            f"<b>🤖 Bot:</b> {chat_title}\n"
            f"<b>💰 Summa:</b> {amount:,} so'm"
        )

    return "\n\n".join(lines)


# ── handlers ─────────────────────────────────────────────────────────────────

@dp.message_handler(Command("report"), state="*")
async def reporter(msg: types.Message) -> None:
    await msg.answer(
        text=(
            "🖥 Hisobotlarni ko'rish uchun bosing.\n"
            "⏰ <b>Oylik</b> — Sizning oy davomida qilgan umumiy foydangiz\n"
            "🗓 <b>Yillik</b> — Sizning yil davomida qilgan umumiy foydangiz"
        ),
        reply_markup=await report_btn(),
        parse_mode="HTML",                          # явный parse_mode
    )


@dp.callback_query_handler(report_button.filter(plan="monthly"))
async def report_monthly(call: types.CallbackQuery) -> None:  # уникальное имя
    await call.answer()                                        # сразу закрываем spinner
    text = await _build_report(
        user_id=call.from_user.id,
        period="monthly",
    )
    await call.message.answer(text, parse_mode="HTML")


@dp.callback_query_handler(report_button.filter(plan="yearly"))
async def report_yearly(call: types.CallbackQuery) -> None:   # уникальное имя
    await call.answer()
    text = await _build_report(
        user_id=call.from_user.id,
        period="yearly",
    )
    await call.message.answer(text, parse_mode="HTML")
