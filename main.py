import sys
import asyncio
from datetime import datetime

import aiofiles


async def connect_to_chat():
    reader, writer = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)
    message = 'Установлено соединение\n'
    while True:
        current_time = datetime.now().strftime('%d.%m.%y %I:%M')
        message = f'[{current_time}] {message}'
        async with aiofiles.open('conversation_history.txt', 'a',
                                 encoding='utf-8') as file:
            await file.write(message)
        sys.stdout.write(message)
        chunk = await reader.readline()
        message = chunk.decode('utf-8')


def main():
    try:
        asyncio.run(connect_to_chat())
    except Exception as err:
        sys.stderr.write(err)


if __name__ == '__main__':
    main()
