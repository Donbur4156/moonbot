from io import BytesIO

import aiohttp


async def download(link):
    async with aiohttp.ClientSession() as s, s.get(link) as response:
        _bytes: bytes = await response.content.read()

    return BytesIO(_bytes)
