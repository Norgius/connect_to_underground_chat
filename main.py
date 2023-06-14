import asyncio
import argparse
import sys
import os
from datetime import datetime

import aiofiles
from environs import Env

import gui

loop = asyncio.get_event_loop()

messages_queue = asyncio.Queue()
sending_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()


async def read_msgs(host, port, queue, path_to_folder):
    reader, writer = await asyncio.open_connection(host, port)
    message = 'Установлено соединение\n'
    try:
        while True:
            current_time = datetime.now().strftime('%d.%m.%y %I:%M')
            message = f'[{current_time}] {message}'
            queue.put_nowait(message)
            path_to_file = os.path.join(path_to_folder, 'conversation_history.txt')
            async with aiofiles.open(path_to_file, 'a', encoding='utf-8') as file:
                await file.write(message)
            sys.stdout.write(message)
            chunk = await reader.readline()
            message = chunk.decode('utf-8')
    finally:
        writer.close()
        await writer.wait_closed()


async def save_messages(path_to_folder, queue):
    path_to_file = os.path.join(path_to_folder, 'conversation_history.txt')
    async with aiofiles.open(path_to_file, 'r') as file:
        all_file = await file.readlines()
        for message in all_file:
            queue.put_nowait(message)


async def main():
    env = Env()
    env.read_env()
    host_for_chat = env.str('HOST_FOR_CHAT', 'minechat.dvmn.org')
    port_for_chat = env.int('PORT_FOR_CHAT', 5000)
    user_port_for_chat = env.int('PORT_FOR_AUTH_CHAT', 5050)
    path_to_chat_history = env.str('PATH_TO_CHAT_HISTORY', '')

    parser = argparse.ArgumentParser(
        description='Подключается к чату и прослушивает его',
    )
    parser.add_argument('--host', default='', type=str,
                        help='Хост чата')
    parser.add_argument('--port', default=0, type=int,
                        help='Порт чата')
    parser.add_argument('--user_port', default=0, type=int,
                        help='Порт для подключения пользователя')
    parser.add_argument('--history', default='', type=str,
                        help='Путь к каталогу, где будет храниться история чата')

    args = parser.parse_args()

    if all([args.host, args.port, args.user_port, args.history]):
        host_for_chat = args.host
        port_for_chat = args.port
        user_port_for_chat = args.user_port
        path_to_chat_history = args.history

    await asyncio.gather(
        save_messages(path_to_chat_history, messages_queue),
        read_msgs(host_for_chat, port_for_chat, messages_queue, path_to_chat_history),
        gui.draw(messages_queue, sending_queue, status_updates_queue)
    )


if __name__ == '__main__':
    loop.run_until_complete(main())
