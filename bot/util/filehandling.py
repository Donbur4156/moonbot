import logging
from io import BytesIO

import aiohttp


async def download(link):
    try:
        async with aiohttp.ClientSession() as s, s.get(link) as response:
            _bytes: bytes = await response.content.read()
    except aiohttp.InvalidURL as e:
        logging.getLogger("moon_logger").error(
            f"Link not valid: {link}"
        )
        return False

    return BytesIO(_bytes)
