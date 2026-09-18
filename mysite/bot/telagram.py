import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
import os
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv()

BOT_TOKEN = os.getenv("TOKEN_BOT")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
router = Router()


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Создать план задач", callback_data="menu:plan")],
            [InlineKeyboardButton(text="📝 Анализ встречи", callback_data="menu:meeting")],
        ]
    )


def skip_kb(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data=callback_data)]]
    )



class PlanStates(StatesGroup):
    goal = State()
    constraints = State()
    count_tasks = State()


class MeetingStates(StatesGroup):
    text = State()



async def api_post(path: str, json_data) -> dict | list:
    url = f"{API_BASE_URL}{path}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json_data, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise RuntimeError(f"API {path} -> {resp.status}: {text}")
            return await resp.json()



@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я помогу:\n"
        "• составить план задач по цели\n"
        "• разобрать текст встречи на задачи и проверить их полноту\n\n"
        "Выбери, что нужно:",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Выбери действие:", reply_markup=main_menu_kb())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_kb())



@router.callback_query(F.data == "menu:plan")
async def plan_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PlanStates.goal)
    await callback.message.edit_text("Опиши цель, для которой нужно составить план задач:")
    await callback.answer()


@router.message(PlanStates.goal)
async def plan_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await state.set_state(PlanStates.constraints)
    await message.answer(
        "Есть ограничения (сроки, бюджет, ресурсы)? Напиши текстом или нажми «Пропустить».",
        reply_markup=skip_kb("plan:skip_constraints"),
    )


@router.callback_query(F.data == "plan:skip_constraints", PlanStates.constraints)
async def plan_skip_constraints(callback: CallbackQuery, state: FSMContext):
    await state.update_data(constraints=None)
    await state.set_state(PlanStates.count_tasks)
    await callback.message.edit_text("Сколько задач сгенерировать? (укажи число, например 5)")
    await callback.answer()


@router.message(PlanStates.constraints)
async def plan_constraints(message: Message, state: FSMContext):
    await state.update_data(constraints=message.text)
    await state.set_state(PlanStates.count_tasks)
    await message.answer("Сколько задач сгенерировать? (укажи число, например 5)")


@router.message(PlanStates.count_tasks)
async def plan_count_tasks(message: Message, state: FSMContext):
    try:
        count_tasks = int(message.text.strip())
        if count_tasks <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Нужно положительное целое число. Попробуй ещё раз:")
        return

    data = await state.get_data()
    await message.answer("Генерирую план... ⏳")

    try:
        result = await api_post(
            "/todos/plan_create/",
            {
                "goal": data["goal"],
                "constraints": data.get("constraints"),
                "count_tasks": count_tasks,
            },
        )
    except Exception as e:
        logger.exception("plan_create failed")
        await message.answer(f"Не удалось получить план: {e}")
        await state.clear()
        return

    lines = [f"План готов ({result['tasks_count']} задач, статус: {result['plan_status']}):\n"]
    for task in result["tasks"]:
        lines.append(
            f"{task['task_number']}. {task['title']} "
            f"[приоритет: {task['priority']}, статус: {task['status']}]\n"
            f"   {task['details']}"
        )

    await message.answer("\n".join(lines))
    await state.clear()
    await message.answer("Что дальше?", reply_markup=main_menu_kb())



@router.callback_query(F.data == "menu:meeting")
async def meeting_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MeetingStates.text)
    await callback.message.edit_text("Пришли текст (расшифровку) встречи для анализа:")
    await callback.answer()


@router.message(MeetingStates.text)
async def meeting_text(message: Message, state: FSMContext):
    await message.answer("Анализирую встречу... ⏳")

    try:
        tasks = await api_post("/meetings/analyze/", {"text": message.text})
    except Exception as e:
        logger.exception("meeting analyze failed")
        await message.answer(f"Не удалось проанализировать встречу: {e}")
        await state.clear()
        return

    if not tasks:
        await message.answer("Задачи не найдены в тексте встречи.")
        await state.clear()
        await message.answer("Что дальше?", reply_markup=main_menu_kb())
        return

    try:
        check_result = await api_post("/meetings/check_tasks/", tasks)
    except Exception as e:
        logger.exception("check_tasks failed")
        await message.answer(f"Задачи получены, но проверка не удалась: {e}")
        check_result = None

    lines = ["Найденные задачи:\n"]
    for i, task in enumerate(tasks, start=1):
        assignee = task.get("assignee") or "—"
        deadline = task.get("deadline_text") or "—"
        title = task.get("title") or task.get("text") or "(без названия)"
        lines.append(f"{i}. {title}\n   Ответственный: {assignee} | Срок: {deadline}")

    await message.answer("\n".join(lines))

    if check_result:
        stats = check_result["stats"]
        summary = (
            f"\nИтого: {stats['total_tasks']} задач, "
            f"полных: {stats['complete_tasks']}, "
            f"без ответственного: {stats['without_assignee']}, "
            f"без срока: {stats['without_deadline']}"
        )
        clarify_lines = [
            summary,
            "",
            "Требуют уточнения:",
        ]
        any_missing = False
        for check in check_result["checks"]:
            if check["needs_clarification"]:
                any_missing = True
                clarify_lines.append(
                    f"  Задача {check['task_number']}: не хватает {', '.join(check['missing_fields'])}"
                )
        if not any_missing:
            clarify_lines.append("  Нет, все задачи заполнены полностью ✅")

        await message.answer("\n".join(clarify_lines))

    await state.clear()
    await message.answer("Что дальше?", reply_markup=main_menu_kb())



async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())