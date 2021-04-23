import asyncio
import json
import logging
import os
import tempfile

import aiohttp
import boto3

from phil_bot.command_providers._utils import get_iam_token, temporary_filename
from phil_bot.data_providers.user_settings import get_user_settings, set_user_settings


logger = logging.getLogger('phil_bot')


SETTINGS = {}
with open(os.path.normpath(os.path.join(os.path.split(str(__file__))[0], '..', 'secrets', 'ysk.json')), 'r') as f:
    SETTINGS.update(json.load(f))

FOLDER_ID = SETTINGS.get('FOLDER_ID', None)

STORAGE_API_ID = SETTINGS.get('STORAGE_API_ID', None)
STORAGE_API_SECRET_KEY = SETTINGS.get('STORAGE_API_SECRET_KEY', None)

AWS_STATIC_ACCESS_KEY = SETTINGS.get('AWS_STATIC_ACCESS_KEY', None)
AWS_STATIC_SECRET_KEY = SETTINGS.get('AWS_STATIC_SECRET_KEY', None)


EXPECT_INPUT_SEC = 30
EXPECT_INPUT_STRING = 'Я вас слушаю (Можно и более 30с)...'


EXPECT_INPUT_IS_VOICE = True


CHUNK_SIZE = 1024 * 1024


boto3_client = boto3.client(
    service_name='s3',
    endpoint_url='https://storage.yandexcloud.net',
    aws_access_key_id=AWS_STATIC_ACCESS_KEY,
    aws_secret_access_key=AWS_STATIC_SECRET_KEY,
)


async def arange(count):
    for i in range(count):
        yield(i)


async def send_long_audio(filelink):

    url = 'https://transcribe.api.cloud.yandex.net/speech/stt/v2/longRunningRecognize'
    headers = {
        'Authorization': 'Api-Key {}'.format(STORAGE_API_SECRET_KEY)
    }

    body = {

        "config": {
            "specification": {
                "languageCode": "ru-RU"
            }
        },
        "audio": {
            "uri": filelink
        }
    }

    async with aiohttp.ClientSession() as session:

        async with session.post(url,
                                headers=headers,
                                json=body,
                                ) as resp:

            data = await resp.read()
            jsn = json.loads(data.decode('utf-8'))
            return jsn


async def recognize_result(aisession, id_):

    url = f"https://operation.api.cloud.yandex.net/operations/{id_}"
    headers = {
        'Authorization': 'Api-Key {}'.format(STORAGE_API_SECRET_KEY)
    }

    async with aisession.get(url,
                             headers=headers,
                             ) as resp:

        data = await resp.read()
        jsn = json.loads(data.decode('utf-8'))
        return jsn


async def imverylisten(event, args=[], parser_callable=None, mess_input=''):

    user_id = event._sender_id
    user = event._sender
    username = user.username

    us = get_user_settings(user_id)

    allow_imverylisten = None if not us else us['params'].get('allow_imverylisten', None)
    allow_speechkit = None if not us else us['params'].get('allow_speechkit', None)
    allow_speechkit = allow_imverylisten or allow_speechkit

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
                filelink = ''

                with tempfile.NamedTemporaryFile(suffix='.ogg') as tmpfile:

                    async for chunk in client.iter_download(message_by_id.media):
                        tmpfile.write(chunk)

                    tmpfile.seek(0)

                    storagefname = f'{media_doc_id}.ogg'

                    response = boto3_client.upload_fileobj(tmpfile, 'phil-bot', storagefname)

                    filelink = f'https://storage.yandexcloud.net/phil-bot/{storagefname}'

                    result = await send_long_audio(filelink)

                    id_ = result.get('id')

                    if id_:

                        async with aiohttp.ClientSession() as aisession:

                            async for interval5s in arange(8):
                                await asyncio.sleep(5)

                                resjsn = await recognize_result(aisession, id_)

                                if resjsn['done']:

                                    for chunk in resjsn['response']['chunks']:
                                        response_text = '\n'.join([response_text, chunk['alternatives'][0]['text']])

                                    break

                    # Удалить если закончили
                    response = boto3_client.delete_objects(Bucket='phil-bot', Delete={'Objects': [{'Key': storagefname}, ]})

                if response_text:
                    await event.respond(response_text)

    except Exception as e:
        logger.debug(type(e), e)


if __name__ == '__main__':
    pass
