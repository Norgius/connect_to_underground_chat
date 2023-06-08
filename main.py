import os
import sys
import asyncio
import argparse
from datetime import datetime

import aiofiles
from environs import Env

async def connect_to_chat(host: str, port: int, path_to_folder: str):
    reader, writer = await asyncio.open_connection(host, port)
    message = 'Установлено соединение\n'
    while True:
        current_time = datetime.now().strftime('%d.%m.%y %I:%M')
        message = f'[{current_time}] {message}'
        path_to_file = os.path.join(path_to_folder, 'conversation_history.txt')
        async with aiofiles.open(path_to_file, 'a', encoding='utf-8') as file:
            await file.write(message)
        sys.stdout.write(message)
        chunk = await reader.readline()
        message = chunk.decode('utf-8')


def main():
    env = Env()
    env.read_env()
    host_for_chat = env.str('HOST_FOR_CHAT', '')
    port_for_chat = env.int('PORT_FOR_CHAT', 0)
    path_to_chat_history = env.str('PATH_TO_CHAT_HISTORY', '')

    parser = argparse.ArgumentParser(
        description='Программа позволяет скачивать папки с фото архивом',
    )
    parser.add_argument('--host', default='', type=str,
                        help='Хост чата')
    parser.add_argument('--port', default=0, type=int,
                        help='Порт чата')
    parser.add_argument('--history', default='', type=str,
                        help='Путь к каталогу, где будет храниться история чата')
    args = parser.parse_args()
    if all([args.host, args.port, args.history]):
        host_for_chat = args.host
        port_for_chat = args.port
        path_to_chat_history = args.history
    try:
        asyncio.run(
            connect_to_chat(host_for_chat, port_for_chat, path_to_chat_history)
        )
    except Exception as err:
        sys.stderr.write(err)


if __name__ == '__main__':
    main()
