import asyncio
import json
import logging
import os
import tempfile

import aiohttp

from phil_bot.command_providers._utils import get_iam_token
from phil_bot.data_providers.user_settings import get_user_settings, set_user_settings

logger = logging.getLogger('phil_bot')


SETTINGS = {}
with open(os.path.normpath(os.path.join(os.path.split(str(__file__))[0], '..', 'secrets', 'ysk.json')), 'r') as f:
    SETTINGS.update(json.load(f))

FOLDER_ID = SETTINGS.get('FOLDER_ID', None)


EXPECT_INPUT_SEC = 20
EXPECT_INPUT_STRING = 'Напишите что сказать...'


async def aiterate(aiterator, map_function):
    async for d in aiterator:
        map_function(d)


async def get_file_chunks(text):
    IAM_TOKEN = get_iam_token()

    url = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
    headers = {
        'Authorization': 'Bearer ' + IAM_TOKEN,
    }

    data = {
        'text': text,
        'lang': 'ru-RU',
        'voice': 'ermil',
        'emotion': 'evil',
        'folderId': FOLDER_ID
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url,
                                headers=headers,
                                data=data,
                                chunked=True,
                                ) as resp:

            async for data, end_of_http_chunk in resp.content.iter_chunks():
                yield data


async def imaparrot(event, args=[], parser_callable=None, mess_input=''):

    user_id = event._sender_id
    user = event._sender
    username = user.username

    us = get_user_settings(user_id)

    allow_imaparrot = None if not us else us['params'].get('allow_imaparrot', None)
    allow_speechkit = None if not us else us['params'].get('allow_speechkit', None)
    allow_speechkit = allow_imaparrot or allow_speechkit

    if not allow_speechkit:
        await event.respond('Извините, но вам не разрешено использовать функции работы с речью...')
        return True

    try:
        if not mess_input:
            await event.respond('Нечего сказать...')
            return True

        bot_id = event.client._self_id
        client = event.client
        chat = event.chat

        with tempfile.NamedTemporaryFile(suffix='.ogg') as tmpfile:

            async for chunk in get_file_chunks(mess_input):

                tmpfile.write(chunk)

            tmpfile.seek(0)

            await event.client.send_file(event.chat, tmpfile, voice_note=True)

    except Exception as e:
        logger.debug(type(e), e)


if __name__ == '__main__':

    with open('results.ogg', "wb") as f:

        def write_file(chunk):
            f.write(chunk)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(aiterate(get_file_chunks('Тест для проверки'), write_file))
