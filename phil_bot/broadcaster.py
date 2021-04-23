import aiohttp
import asyncio
import logging
import os
import sys
import time

from random import randint
from telethon.tl.types import InputMediaPoll, Poll, PollAnswer

# fuck python3
MAIN_PACKAGE_DIR = os.path.abspath(os.path.join(os.path.split(str(__file__))[0], '..'))
PACKAGE_NAME = os.path.basename(MAIN_PACKAGE_DIR)
sys.path.append(MAIN_PACKAGE_DIR)


from phil_bot.main import PhilBot
from phil_bot.command_providers._utils import temporary_filename
from phil_bot.data_providers.subscribers import get_active_subscribers_count,\
    get_active_subscribers, has_mailing_subscriber_id, \
    get_active_mailings, get_active_mailings_count, add_mailing_subscriber


loop = asyncio.get_event_loop()


# main logger
# logging.basicConfig(level=logging.DEBUG)
logging.getLogger('telethon').setLevel(level=logging.WARNING)

logger = logging.getLogger('phil_bot')
logger.setLevel(logging.ERROR)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


async def get_filelike_from_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.content.read()


async def main(client):
    try:
        logger.debug('run')
        max_whiles = 500
        cur_whiles = 0

        mailings_count = get_active_mailings_count()
        subscribers_count = get_active_subscribers_count()

        limit_m = 30; offset_m = 0

        while (offset_m == 0 or limit_m + offset_m < mailings_count):
            cur_whiles += 1
            if cur_whiles > max_whiles:
                return

            active_mailings = get_active_mailings(limit=limit_m, offset=offset_m)
            offset_m += limit_m
            logger.debug(len(active_mailings))

            for mailing in active_mailings:

                limit_s = 30; offset_s = 0

                while (offset_s == 0 or limit_s + offset_s < subscribers_count):
                    cur_whiles += 1
                    if cur_whiles > max_whiles:
                        return

                    active_subscribers = get_active_subscribers(limit=limit_s, offset=offset_s, mailing_id=mailing['id'])
                    offset_s += limit_s
                    logger.debug(len(active_subscribers))

                    for subscriber in active_subscribers:

                        chat_id = int(subscriber['entity_id'])
                        chat = await client.get_entity(chat_id)

                        if chat:
                            has_mailing_subscriber = has_mailing_subscriber_id(mailing['id'], subscriber['id'])

                            if not has_mailing_subscriber:

                                chat_title = getattr(chat, 'title', None)
                                chat_title = chat_title if chat_title else getattr(chat, 'username', None)

                                only_for_chats = mailing['only_for_chats']
                                if not only_for_chats or not len(only_for_chats) or (str(chat_id) in only_for_chats) or (chat_title in only_for_chats):

                                    images_links = mailing['images_links']
                                    image_urls = images_links.splitlines(False) if images_links else []
                                    len_image_urls = len(image_urls)

                                    message = mailing['text']
                                    logger.info((type(chat), chat.id, message))

                                    if not len_image_urls:
                                        await client.send_message(chat, message, parse_mode='html')

                                    elif len_image_urls == 1:
                                        await client.send_message(chat, message, parse_mode='html', file=image_urls[0])

                                    else:
                                        if not mailing['is_pool']:
                                            files_ = []
                                            for url in image_urls:

                                                _, _, ext = url.rpartition('.')
                                                file_ = await get_filelike_from_url(url)

                                                with temporary_filename(suffix=f'.{ext}') as tmpfilename:

                                                    with open(tmpfilename, 'wb') as tmpfile:
                                                        tmpfile.write(file_)
                                                        tmpfile.seek(0)

                                                    file_u = await client.upload_file(tmpfilename)
                                                    files_.append(file_u)

                                            await client.send_message(chat, message, parse_mode='html', file=files_)
                                            del files_

                                        else:
                                            answers = []
                                            for i, el in enumerate(image_urls):
                                                answers.append(PollAnswer(el, str(i + 1).encode('utf-8')))

                                            await client.send_message(chat, ' ', file=InputMediaPoll(
                                                poll=Poll(
                                                    id=randint(1000, 8000) + 100000000 + chat.id,
                                                    question=message,
                                                    answers=answers
                                                )
                                            ))

                                    add_mailing_subscriber(mailing['id'], chat_id, name=subscriber['name'])

    except Exception as e:
        logger.debug(type(e), e)
        raise e

    pass


if __name__ == '__main__':
    bot = PhilBot(allow_commands=[], allow_handlers=[], allow_inline_handlers=[], label='bot-client-broadcaster', loop=loop)
    client = bot._bot

    try:
        with client:
            while True:
                client.loop.run_until_complete(main(client))
                time.sleep(30 + randint(0, 20))
    except KeyboardInterrupt:
        print('exiting...')
        client.disconnect()
        sys.exit(0)
    except Exception as e:
        raise e
