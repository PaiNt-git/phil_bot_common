import asyncio
import json
import logging
import os

import aiohttp

from phil_bot.command_providers._utils import get_iam_token
from phil_bot.data_providers.user_settings import get_user_settings, set_user_settings


logger = logging.getLogger('phil_bot')


SETTINGS = {}
with open(os.path.normpath(os.path.join(os.path.split(str(__file__))[0], '..', 'secrets', 'ysk.json')), 'r') as f:
    SETTINGS.update(json.load(f))

FOLDER_ID = SETTINGS.get('FOLDER_ID', None)


EXPECT_INPUT_SEC = 30
EXPECT_INPUT_STRING = 'Я вас слушаю (не более 30с)...'


EXPECT_INPUT_IS_VOICE = True


CHUNK_SIZE = 1024 * 1024


async def aiterate(aiterator, map_function):
    async for d in aiterator:
        map_function(d)


async def file_chunks_sender_gen(flike):
    chunk = flike.read(CHUNK_SIZE)
    while chunk:
        yield chunk
        chunk = flike.read(CHUNK_SIZE)


async def get_text_chunks(data):
    IAM_TOKEN = get_iam_token()

    url = 'https://stt.api.cloud.yandex.net/speech/v1/stt:recognize'
    headers = {
        'Authorization': 'Bearer ' + IAM_TOKEN,
    }

    params = {
        'topic': 'general',
        'lang': 'ru-RU',
        'folderId': FOLDER_ID,
    }

    async with aiohttp.ClientSession() as session:

        async with session.post(url,
                                headers=headers,
                                params=params,
                                data=data,
                                chunked=False,
                                ) as resp:

            async for data, end_of_http_chunk in resp.content.iter_chunks():
                jsn = json.loads(data.decode('utf-8'))
                yield jsn


async def imlisten(event, args=[], parser_callable=None, mess_input=''):

    user_id = event._sender_id
    user = event._sender
    username = user.username

    us = get_user_settings(user_id)

    allow_imlisten = None if not us else us['params'].get('allow_imlisten', None)
    allow_speechkit = None if not us else us['params'].get('allow_speechkit', None)
    allow_speechkit = allow_imlisten or allow_speechkit

    if not allow_speechkit:
        await event.respond('Извините, но вам не разрешено использовать функции работы с речью...')
        return True

    try:
        if not mess_input:
            await event.respond('Нечего слушать...')
            return True

        bot_id = event.client._self_id
        client = event.client
        chat = event.chat

        mess_id = mess_input[0] if len(mess_input) else None
        if mess_id:
            message_by_id = await client.get_messages(chat, ids=mess_id)
            media_doc_id = mess_input[1] if len(mess_input) else None

            if message_by_id and hasattr(message_by_id, 'voice') \
                    and message_by_id.voice \
                    and message_by_id.voice.id == media_doc_id:

                response_text = ''

                file_chunks_iterable = client.iter_download(message_by_id.media)

                async for chunk_json in get_text_chunks(file_chunks_iterable):
                    response_text = ''.join([response_text, chunk_json['result']])

                await event.respond(response_text)

    except Exception as e:
        logger.debug(type(e), e)


if __name__ == '__main__':

    with open('audio_2020-11-17_11-07-58.ogg', "rb") as f:

        loop = asyncio.get_event_loop()
        loop.run_until_complete(aiterate(get_text_chunks(file_chunks_sender_gen(f)), lambda x: print(x['result'])))
