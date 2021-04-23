from phil_bot.data_providers.user_settings import get_user_settings, set_user_settings


async def start(event, args=[], parser_callable=None, mess_input=''):

    user_id = event._sender_id
    user = event._sender
    username = user.username

    set_user_settings(user_id, {}, username)

    await event.respond('''
Это Фил ТОГУ, как дела?

Это тестовая версия Telegram-бота ТОГУ, набор команд пока не определен...

    ''')
