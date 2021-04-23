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
from phil_bot.data_providers.notifs import get_active_notifs_count, get_active_notifs, mark_notif_sended, delete_notif_sended


loop = asyncio.get_event_loop()


# main logger
# logging.basicConfig(level=logging.DEBUG)
logging.getLogger('telethon').setLevel(level=logging.WARNING)

logger = logging.getLogger('phil_bot')
logger.setLevel(logging.ERROR)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))


async def main(client):
    try:
        logger.debug('run')
        max_whiles = 500
        cur_whiles = 0

        all_notifs_count = get_active_notifs_count()

        limit_m = 30; offset_m = 0

        while (offset_m == 0 or limit_m + offset_m < all_notifs_count):
            cur_whiles += 1
            if cur_whiles > max_whiles:
                return

            active_notifs = get_active_notifs(limit=limit_m, offset=offset_m)
            offset_m += limit_m
            logger.debug(len(active_notifs))

            for notif in active_notifs:

                user_id = int(notif['user_id'])
                user = await client.get_entity(user_id)

                message = notif['text']
                logger.info((type(user), user.id, message))

                await client.send_message(user, message, parse_mode='html')
                mark_notif_sended(user_id, notif['id'])

    except Exception as e:
        logger.debug(type(e), e)
        raise e

    pass


if __name__ == '__main__':
    bot = PhilBot(allow_commands=[], allow_handlers=[], allow_inline_handlers=[], label='bot-client-notificator', loop=loop)
    client = bot._bot

    try:
        with client:
            while True:
                client.loop.run_until_complete(main(client))
                time.sleep(30 + randint(0, 20))
                delete_notif_sended()

    except KeyboardInterrupt:
        print('exiting...')
        client.disconnect()
        sys.exit(0)
    except Exception as e:
        raise e
