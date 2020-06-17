# coding=utf-8
from logging import getLogger

from telegram import Bot
from telegram import Update
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext import Updater
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler
from telegram.ext import CallbackContext
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters
from telegram.utils.request import Request
from my_project.style_transfer import style_transfer


TG_TOKEN = "1021175427:AAHexMUwuLN5dq-fl6yXTc1Uk5jhi2karbY"
logger = getLogger(__name__)
CONTENT, STYLE, OUTPUT = range(3) #states
f1, f2 = 0, 0 #images
imsize = 128
QUALITY = {
    1: '128x128',
    2: '256x256',
    3: '512x512',
    4: '1024x1024',
}
CALLBACK_BEGIN = 'x1'


def log_error(f):

    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print(f'Ошибка: {e}')
            raise e

    return inner

@log_error
def start_buttons_handler(update: Update, context: CallbackContext):
    inline_buttons0 = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='Начать', callback_data='CALLBACK_BEGIN'),
            ],
        ],
    )
    update.effective_message.reply_text(
        text='Нажми на кнопку:',
        reply_markup=inline_buttons0,
    )

@log_error
def start_handler(update: Update, context: CallbackContext):
    init = update.callback_query.data
    chat_id = update.callback_query.message.chat.id

    if init != 'CALLBACK_BEGIN':
        logger.debug('bad init: %s', init)
        update.callback_query.bot.send_message(
            chat_id=chat_id,
            text='Что-то пошло не так, обратитесь к администратору бота',
        )
        return ConversationHandler.END

    update.callback_query.answer()
    # Запросить контент-фото
    update.callback_query.bot.send_message(
        chat_id=chat_id,
        text='Пришлите фото, которое нужно стилизовать.',
    )
    return CONTENT

@log_error
def content_handler(update: Update, context: CallbackContext):
    # Получить контент-фото
    try:
        image = update.message.photo[-1].file_id
        context.bot.get_file(image).download('file_0.jpg')
    except Exception as e:
        update.effective_message.reply_text('Попробуйте отправить ещё раз, что-то пошло не так.\n' + 'Ошибка: ' + e)
        return CONTENT

    # Запросить стайл-фото
    update.message.reply_text(
        text='Пришлите фото, стиль которого необходимо взять.',
    )
    return STYLE

@log_error
def style_handler(update: Update, context: CallbackContext):
    # Получить стайл-фото
    try:
        image = update.message.photo[-1].file_id
        context.bot.get_file(image).download('file_1.jpg')
    except Exception as e:
        context.bot.send_message('Попробуйте отправить ещё раз, что-то пошло не так.\n' + 'Ошибка: ' + e)
        return STYLE
    inline_buttons1 = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=value, callback_data=key) for key, value in QUALITY.items()],
        ],
    )
    update.effective_message.reply_text(
        text='Выберите качество изображения, которое хотите получить. (ВНИМАНИЕ: чем больше качество, тем дольше '
             'будет процесс обработки)',
        reply_markup=inline_buttons1,
    )

    return OUTPUT


@log_error
def output_handler(update: Update, context: CallbackContext):
    setting = int(update.callback_query.data)
    chat_id = update.effective_message.chat_id
    if setting not in QUALITY:
        update.effective_message.reply_text('Что-то пошло не так, обратитесь к администратору бота')
        return OUTPUT
    if setting==1:
        context.bot.send_message(chat_id=chat_id, text='Пожалуйста, подождите. (~2 минуты)')
    elif setting==2:
        context.bot.send_message(chat_id=chat_id, text='Пожалуйста, подождите. (~5 минут)')
    elif setting==3:
        context.bot.send_message(chat_id=chat_id, text='Пожалуйста, подождите. (~20 минут)')
    elif setting==4:
        context.bot.send_message(chat_id=chat_id, text='Пожалуйста, подождите. (~60 минут)')
    style_transfer('file_0.jpg', 'file_1.jpg', imsize=64*2**setting, num_steps=300, start_with_white_noise=False)
    photo = open('file_2.jpg', 'rb')
    context.bot.send_photo(chat_id=chat_id, photo=photo)
    context.bot.send_message(chat_id=chat_id, text='Готово!')
    return ConversationHandler.END


@log_error
def cancel_handler(update: Update,  context: CallbackContext):
    """ Отменить весь процесс диалога.
    """
    update.message.reply_text('Отмена. Для начала с нуля нажмите /start')
    return ConversationHandler.END

@log_error
def echo_handler(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Нажмите /start для начала работы!',
    )

# REQUEST_KWARGS={
#     'proxy_url': 'socks5://178.128.203.1:1080/',
#     # Optional, if you need authentication:
#     'urllib3_proxy_kwargs': {
#          'assert_hostname': 'True',
#          'cert_reqs': 'CERT_NONE',
#          'username': 'student',
#          'password': 'TH8FwlMMwWvbJF8FYcq0',
#     }
# }

@log_error
def main():
    logger.info('Started Style-transfer-bot')

    req = Request(
        connect_timeout=10,
        read_timeout=0.5,
    )
    bot = Bot(
        token=TG_TOKEN,
        request=req,
        base_url="https://telegg.ru/orig/bot",
        base_file_url="https://telegg.ru/orig/file/bot",
    )
    updater = Updater(
        bot=bot,
        use_context=True,
    )
    logger.info(f'Bot info: {bot.get_me()}')


    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_handler, pass_user_data=True),
        ],
        states={
            CONTENT: [
                MessageHandler(Filters.all, content_handler, pass_user_data=True),
            ],
            STYLE: [
                MessageHandler(Filters.all, style_handler, pass_user_data=True),
            ],
            OUTPUT: [
                CallbackQueryHandler(output_handler, pass_user_data=True),
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_handler),
        ],
    )
    updater.dispatcher.add_handler(conv_handler)
    updater.dispatcher.add_handler(CommandHandler('start', start_buttons_handler))
    updater.dispatcher.add_handler(MessageHandler(Filters.all, echo_handler))


    updater.start_polling()
    updater.idle()
    logger.info('Stopped Style-transfer-bot')



if __name__ == '__main__':
    main()