import logging

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiopygismeteo import Gismeteo, LocalityNotFound


bot = Bot(token="")  # <----- Import your telegram bot token here
gm = Gismeteo()

dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)


class States(StatesGroup):
    city_name = State()
    current_city_id = State()


@dp.message_handler(commands="start", state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await States.city_name.set()
    await message.answer("Введите название населённого пункта")


@dp.message_handler(state=States.city_name)
async def work_with_city(message: types.Message, state: FSMContext):

    async with state.proxy() as data:
        data["city_name"] = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Сейчас", "Сегодня")
    keyboard.add("Завтра", "Послезавтра")
    keyboard.add("Изменить населённый пункт")
    try:
        city_id = await gm.get_id_by_query(data["city_name"])
    except LocalityNotFound:
        await message.answer("Населённый пункт не найден, введите заново")
        return
    await States.next()
    await message.answer("Когда?", reply_markup=keyboard)


@dp.message_handler(text="Сейчас", state=States.current_city_id)
async def get_now(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["current_city_id"] = await gm.get_id_by_query(data["city_name"])
        current = await gm.current(data["current_city_id"])
    await message.answer(
        f"""
Дата: {current.date.local}
Текущая температура: {current.temperature.air.c}℃ | {current.temperature.air.f}℉
Скорость ветра: {current.wind.speed.km_h} Km/h | {current.wind.speed.mi_h} Mi/h
Состояние погоды: {current.description.full}
Атмосферное давление: {current.pressure.mm_hg_atm} мм.рт.ст.
Влажность: {current.humidity.percent}%
"""
    )


@dp.message_handler(text="Сегодня", state=States.current_city_id)
async def get_today(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["current_city_id"] = await gm.get_id_by_query(data["city_name"])
        step24 = await gm.step24(data["current_city_id"], days=3)
    await message.answer(
        f"""
Дата: {step24[0].date.local}
Температура: {step24[0].temperature.air.avg.c}℃ | {step24[0].temperature.air.avg.f}℉
Состояние погоды: {step24[0].description.full}
Атмосферное давление: {step24[0].pressure.mm_hg_atm.max} мм.рт.ст.
Влажность: {step24[0].humidity.percent.avg}%
        """
    )


@dp.message_handler(text="Завтра", state=States.current_city_id)
async def get_tomorrow(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["current_city_id"] = await gm.get_id_by_query(data["city_name"])
        step24 = await gm.step24(data["current_city_id"], days=3)
    await message.answer(
        f"""
Дата: {step24[1].date.local}
Температура: {step24[1].temperature.air.avg.c}℃ | {step24[1].temperature.air.avg.f}℉
Состояние погоды: {step24[1].description.full}
Атмосферное давление: {step24[1].pressure.mm_hg_atm.max} мм.рт.ст.
Влажность: {step24[1].humidity.percent.avg}%
        """
    )


@dp.message_handler(text="Послезавтра", state=States.current_city_id)
async def get_after_tomorrow(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["current_city_id"] = await gm.get_id_by_query(data["city_name"])
        step24 = await gm.step24(data["current_city_id"], days=3)
    await message.answer(
        f"""
Дата: {step24[2].date.local}
Температура: {step24[2].temperature.air.avg.c}℃ | {step24[2].temperature.air.avg.f}℉
Состояние погоды: {step24[2].description.full}
Атмосферное давление: {step24[2].pressure.mm_hg_atm.max} мм.рт.ст.
Влажность: {step24[2].humidity.percent.avg}%
        """
    )


@dp.message_handler(text="Изменить населённый пункт", state="*")
async def change_city(message: types.Message):
    await States.city_name.set()
    await message.answer(
        "Введите название населённого пункта", reply_markup=types.ReplyKeyboardRemove()
    )


async def on_shutdown(dp):
    await dp.storage.close()
    await dp.storage.wait_closed()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_shutdown=on_shutdown)
