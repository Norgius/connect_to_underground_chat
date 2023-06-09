import os
import sys
import asyncio
import argparse
from datetime import datetime
import time

import aiofiles
from environs import Env


async def connect_to_chat(host: str, port: int, chat_user_token: str):
    reader, writer = await asyncio.open_connection(host, port)
    message = 'Установлено соединение\n'
    try:
        server_message = await reader.read(1024)
        server_message = server_message.decode('utf-8')
        if server_message.startswith('Hello '):
            writer.write(f'{chat_user_token}\r\n'.encode('utf-8'))
            await writer.drain()

        writer.write('3-я попытка\r\n\n'.encode('utf-8'))
        await writer.drain()
        time.sleep(2)

    finally:
        writer.close()
        await writer.wait_closed()


def main():
    env = Env()
    env.read_env()
    host_for_chat = env.str('HOST_FOR_CHAT', '')
    port_for_chat = env.int('PORT_FOR_AUTH_CHAT', 0)
    chat_user_token = env.str('CHAT_USER_TOKEN')

    parser = argparse.ArgumentParser(
        description='Подключается к чату, как пользователь',
    )
    parser.add_argument('--host', default='', type=str,
                        help='Хост чата')
    parser.add_argument('--port', default=0, type=int,
                        help='Порт для подключения пользователя')
    args = parser.parse_args()
    if all([args.host, args.port]):
        host_for_chat = args.host
        port_for_chat = args.port

    try:
        asyncio.run(connect_to_chat(
            host_for_chat,
            port_for_chat,
            chat_user_token
            )
        )
    except Exception as err:
        sys.stderr.write(err)


if __name__ == '__main__':
    main()
