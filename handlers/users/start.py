from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.utils.deep_linking import decode_payload

from data.texts import texts
from filters import IsPrivate
from keyboards.inline.buttons import plans_button, group_button, group_name_button
from loader import dp
from middlewares import i18n
from utils.db_api.database import Groups, Users

_ = i18n.lazy_gettext

groups = Groups()
users = Users()


# ── helpers ──────────────────────────────────────────────────────────────────

async def _ensure_user(user_id: int, chat_id: int, full_name: str) -> None:
    """Создаёт запись пользователя, если её ещё нет."""
    existing = await users.get_user(user_id=user_id, chat_id=chat_id)
    if existing is None:
        await users.set_base_info(
            user_id=user_id,
            chat_id=chat_id,
            name=full_name,
        )


async def _build_plan_text(user_id: int, chat_id: int) -> tuple[str, bool]:
    """
    Возвращает (текст выбора плана, флаг free_plan).
    Не мутирует оригинальный texts-словарь.
    """
    free_plan: bool = await users.use_free_plan(
        user_id=user_id,
        chat_id=chat_id,
    )
    parts = [texts["choose_plan"]]
    if free_plan:
        parts.append("🚀 Bepul - botdan test sifatida foydalanib ko'ring")
    return "\n\n".join(parts), free_plan


# ── handlers ─────────────────────────────────────────────────────────────────

@dp.message_handler(IsPrivate(), CommandStart(), state="*")
async def bot_start(message: types.Message, state: FSMContext) -> None:
    args = message.get_args()
    await message.answer(_(texts["welcome"]))

    if not args:
        all_groups = await groups.get_groups()          # await — обязательно
        await message.answer(
            texts["choose_group"],
            reply_markup=await group_button(all_groups),
        )
        return

    chat_id: int = int(decode_payload(args))            # явный int
    group_name: str | None = await groups.get_group_name(chat_id)

    if group_name is None:
        await message.reply(texts["group_not_found"])
        return

    async with state.proxy() as data:
        data["chat_id"] = chat_id

    await _ensure_user(
        user_id=message.from_user.id,
        chat_id=chat_id,
        full_name=message.from_user.full_name,
    )

    plan_text, free_plan = await _build_plan_text(
        user_id=message.from_user.id,
        chat_id=chat_id,
    )
    await message.answer(plan_text, reply_markup=await plans_button(free_plan))


@dp.callback_query_handler(group_name_button.filter())
async def group_name_callback(
    call: types.CallbackQuery,
    callback_data: dict,
    state: FSMContext,
) -> None:
    chat_id: int = int(callback_data["chat_id"])        # явный int

    async with state.proxy() as data:
        data["chat_id"] = chat_id

    await _ensure_user(
        user_id=call.from_user.id,
        chat_id=chat_id,
        full_name=call.from_user.full_name,
    )

    plan_text, free_plan = await _build_plan_text(
        user_id=call.from_user.id,
        chat_id=chat_id,
    )
    await call.message.edit_text(
        plan_text,
        reply_markup=await plans_button(free_plan),
    )
    await call.answer()                                 # закрываем spinner у кнопки
