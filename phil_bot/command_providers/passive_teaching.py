import logging

from telethon.tl.custom.button import Button

from phil_bot.data_providers.user_settings import get_user_settings, set_user_settings


logger = logging.getLogger('phil_bot')


async def inline_callback(event, unid=None):

    user_id = event._sender_id
    user = event._sender
    username = user.username

    us = get_user_settings(user_id)

    allow_teach_bot = None if not us else us['params'].get('allow_teach_bot', None)

    if not allow_teach_bot:
        await event.respond('Извините, но вам не разрешено учить меня. Фил - приличный сов, он обучается только у проверенных преподавателей...')
        return True

    name = event.chat.title if hasattr(event.chat, 'title') else event.chat.username
    chat_id = event.chat.id

    if event.data == b'passive_teaching_yes':

        update_params = {
            'allow_passive_bot_teaching': True,
        }
        r = set_user_settings(event.chat_id, update_params, name)

        await event.edit(f'Разрешение для "{name}" на обучение бота теперь активно..')

    elif event.data == b'passive_teaching_no':

        update_params = {
            'allow_passive_bot_teaching': False,
        }
        r = set_user_settings(event.chat_id, update_params, name)

        await event.edit(f'Разрешение для "{name}" на обучение бота отозвано..')


async def passive_teaching(event, args=[], parser_callable=None, mess_input=''):

    user_id = event._sender_id
    user = event._sender
    username = user.username

    us = get_user_settings(user_id)

    allow_teach_bot = None if not us else us['params'].get('allow_teach_bot', None)

    if not allow_teach_bot:
        await event.respond('Извините, но вам не разрешено учить меня. Фил - приличный сов, он обучается только у проверенных преподавателей...')
        return True

    message = '''
    Разрешить обучение бота из этого канала?
    '''

    buttons = [

        Button.inline('Разрешить', b'passive_teaching_yes'),
        Button.inline('Запретить', b'passive_teaching_no'),

    ]

    await event.respond(message, buttons=buttons)
