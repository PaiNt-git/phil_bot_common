import logging
import memcache

from phil_bot.data_providers.phil_search import search_entries, add_entry
from phil_bot.data_providers.user_settings import get_user_settings, set_user_settings

logger = logging.getLogger('phil_bot')

MESSAGE_PATTERN = '\w+'
STOP_PROPAGATE = False

mc = memcache.Client(['127.0.0.1:11211'], debug=0)


async def b_0_teaching_from_reply(event):
    try:
        chat = event.chat
        chat_id = event.chat_id

        chatsett = get_user_settings(chat_id)

        allow_passive_bot_teaching = None if not chatsett else chatsett['params'].get('allow_passive_bot_teaching', None)

        if allow_passive_bot_teaching:

            message = event.message

            if message.is_reply:

                user_id = event._sender_id
                user = event._sender
                username = user.username

                us = get_user_settings(user_id)
                allow_teach_bot = None if not us else us['params'].get('allow_teach_bot', None)

                if allow_teach_bot:
                    answer_mess = message.message
                    reply = await event.get_reply_message()
                    question_mess = reply.message

                    if question_mess and answer_mess:

                        add_entry('owl_info_service', question_mess, {'url': '@phil_togu_bot'}, abstract=answer_mess)

                        await event.respond(f'Я запомнил этот ответ на вопрос..')

    except Exception as e:
        logger.debug((type(e), e))
