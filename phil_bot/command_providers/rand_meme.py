import asyncio

import aiohttp


async def aprint(corut):
    print(await corut)


async def get_meme():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://meme-api.herokuapp.com/gimme') as resp:
            r = await resp.json()
            return r


async def rand_meme(event, args=[], parser_callable=None, mess_input=''):

    resp = await get_meme()
    result = resp.get('url')

    await event.respond(result)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(aprint(get_meme()))
