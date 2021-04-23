import logging
import re
import memcache

from telethon.tl.custom.button import Button

from phil_bot.data_providers.phil_search import search_entries, add_entry
from phil_bot.data_providers.user_settings import get_user_settings, set_user_settings

logger = logging.getLogger('phil_bot')


EXPECT_INPUT_SEC = 40
EXPECT_INPUT_STRING = '''
Пожалуйста введите сообщение для внесения в базу вопросов и ответов.
Формат сообщения:
**<name>** - заголовок сообщения (первая строка)
**<message>** - абстракт ответа (все промежуточные строки)
**<url>** - окончание сообщения, должна быть URL где найти ответ на вопрос

(выберите уточняющую категорию)
'''

EXPECT_INPUT_BUTTONS = [
    Button.inline('Абитуриент', b'teach_bot_abitur'),
]

mc = memcache.Client(['127.0.0.1:11211'], debug=0)


async def inline_callback(event, unid=None):
    cache_key = f'{event.chat_id}-{event._sender_id}--owl_info_cat_select'

    chat = event.chat
    client = event.client

    message_id = event.message_id
    sel_cat = ''

    if event.data == b'teach_bot_abitur':
        mc.set(cache_key, 'owl_info_abitur', 50)
        sel_cat = 'Абитуриент'
        await event.answer(f'Выбрано "{sel_cat}"')

    # message_by_id = await client.get_messages(chat, ids=message_id)
    message_ = EXPECT_INPUT_STRING.replace('(выберите уточняющую категорию)', f'(Выбрано: **{sel_cat}**)')
    await client.edit_message(chat, message_id, message_)  # , buttons=EXPECT_INPUT_BUTTONS


url_pattern = re.compile(r"^(ht|f)tp(s?)\:\/\/[0-9a-zA-Zа-яА-Я]([-.\w]*[0-9a-zA-Zа-яА-Я])*(:(0-9)*)*(\/?)([a-zA-Zа-яА-Я0-9\-\.\?\,\'\/\\\+&amp;%\$#_]*)?", flags=re.IGNORECASE)


def get_params(mess_input):
    lines = mess_input.strip().split('\n')
    name = message = url = None
    lenlines = len(lines)
    if lenlines >= 2:
        name = lines[0].replace('\n', '').replace('\r', '')

        message = '\n'.join(lines[1:-1])

        url = lines[-1].replace('\n', '').replace('\r', '')
        result = re.match(url_pattern, url)
        if not result:
            url = None

    return name, message, url


async def teach_bot(event, args=[], parser_callable=None, mess_input=''):

    cache_key = f'{event.chat_id}-{event._sender_id}--owl_info_cat_select'

    owl_info_cat_select = mc.get(cache_key) or 'owl_info_service'
    mc.delete(cache_key, noreply=True)

    user_id = event._sender_id
    user = event._sender
    username = user.username

    us = get_user_settings(user_id)

    allow_teach_bot = None if not us else us['params'].get('allow_teach_bot', None)

    if not allow_teach_bot:
        await event.respond('Извините, но вам не разрешено учить меня. Фил - приличный сов, он обучается только у проверенных преподавателей...')
        return True

    if not mess_input:
        await event.respond('Нечему учиться...')
        return True

    name, message, url = get_params(mess_input)
    if not name:
        await event.respond('Вы должны указать хотя бы вопрос или наименование темы ответа!')
        return True

    if not url:
        await event.respond('Вы не ввели URL, или он введен неверно. Для того чтобы ответить пользователям, нужно указать URL где будет больше информации по теме...')
        return True

    add_entry(owl_info_cat_select, name, {'url': url}, abstract=message)

    await event.respond('Совиная Справочная Служба рассмотрит ваше предложение по улучшению базы знаний...')
