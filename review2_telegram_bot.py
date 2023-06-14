from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import logging
import os
from PIL import Image

class States(StatesGroup):
    STATE_0 = State()
    STATE_1 = State()
    STATE_2 = State()
    STATE_3 = State()
    STATE_4 = State()
    STATE_5 = State()


TG_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
TG_TOKEN = "1021175427:AAHexMUwuLN5dq-fl6yXTc1Uk5jhi2karbY" # my token, use your please

QUALITY = {
    1: '128x128',
    2: '256x256',
    3: '512x512',
    4: '1024x1024',
}

logging.basicConfig(format=u'%(filename)+13s [ LINE:%(lineno)-4s] %(levelname)-8s [%(asctime)s] %(message)s',
                    level=logging.DEBUG)

bot = Bot(token=TG_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

dp.middleware.setup(LoggingMiddleware())



@dp.message_handler(commands=['start'])
async def start_buttons_handler(message: types.Message):
    inline_buttons0 = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Начать', callback_data='CALLBACK_BEGIN'),
            ],
        ],
    )
    # Делаем стартовую кнопку
    await message.reply(
        text='Нажми на кнопку:',
        reply_markup=inline_buttons0,
    )
    # Меняем состояние
    await States.STATE_1.set()


@dp.callback_query_handler(state=States.STATE_1, text_contains='CALLBACK_BEGIN')
async def start_handler(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    # Запрашиваем контент-фото
    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text='Пришлите фото, которое нужно стилизовать.',
    )
    # Меняем состояние
    await States.next()
    

@dp.message_handler(state=States.STATE_2, content_types=['photo'])
async def content_handler(message: types.Message):
    # Получаем контент-фото
    try:
        await message.photo[-1].download('file_0.jpg')
    except Exception as e:
        await message.reply('Попробуйте отправить ещё раз, что-то пошло не так.\n' + 'Ошибка: ' + e, reply=False)
        return

    # Запрашиваем стайл-фото
    await message.reply(
        text='Пришлите фото, стиль которого необходимо взять.',
        reply=False,
    )
    # Меняем состояние
    await States.next()
    

@dp.message_handler(state=States.STATE_3, content_types=['photo'])
async def style_handler(message: types.Message):
    # Получаем стайл-фото
    try:
        await message.photo[-1].download('file_1.jpg')
    except Exception as e:
        await message.reply('Попробуйте отправить ещё раз, что-то пошло не так.\n' + 'Ошибка: ' + e, reply=False)
        return
    inline_buttons1 = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=value, callback_data=('quality_choice_button' + str(key))) for key, value in QUALITY.items()],
        ],
    )
    # Запрашиваем качество
    await message.reply(
        text='Выберите качество изображения, которое хотите получить. (ВНИМАНИЕ: чем больше качество, тем дольше '
             'будет процесс обработки)',
        reply_markup=inline_buttons1,
        reply=False,
    )
    # Меняем состояние
    await States.next()


@dp.callback_query_handler(state=States.STATE_4, text_contains='quality_choice_button')
async def output_handler(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    setting = int(callback_query.data[-1])
    chat_id = callback_query.from_user.id
    if setting not in QUALITY:
        await bot.send_message(
            chat_id=chat_id,
            text='Что-то пошло не так, обратитесь к администратору бота'
        )
        return
    if setting == 1:
        await bot.send_message(chat_id=chat_id, text='Пожалуйста, подождите. (~2 минуты)')
    elif setting == 2:
        await bot.send_message(chat_id=chat_id, text='Пожалуйста, подождите. (~5 минут)')
    elif setting == 3:
        await bot.send_message(chat_id=chat_id, text='Пожалуйста, подождите. (~20 минут)')
    elif setting == 4:
        await bot.send_message(chat_id=chat_id, text='Пожалуйста, подождите. (~60 минут)')
    
    #style_transfer.style_transfer('file_0.jpg', 'file_1.jpg', imsize=64 * 2 ** setting, num_steps=300, start_with_white_noise=False)
    print('------style transfered------')
    
    #photo = open('file_2.jpg', 'rb')
    photo = open('file_0.jpg', 'rb')
    await bot.send_photo(chat_id=chat_id, photo=photo, caption='Готово!')
    # Меняем состояние
    await States.next()


@dp.message_handler(state=States.STATE_5)
async def goodbye_handler(message: types.Message):
    await message.reply(
        'До свидания!',
    )
    # Меняем состояние на начальное
    await States.next()

@dp.message_handler()
async def echo_handler(message: types.Message):
    await message.reply(
        'Нажмите /start для начала работы!',
        reply=False,
    )



async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_shutdown=shutdown)
