import sys
import asyncio
import argparse
import logging
import json
from textwrap import dedent

import aiofiles
from environs import Env

logger = logging.getLogger(__name__)


async def log_in():
    pass


async def register():
    pass


async def connect_to_chat(host: str, port: int, chat_user_token: str):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        response_in_bytes = await reader.readline()
        response = response_in_bytes.decode('utf-8')
        logger.debug(f'sender: {response}')
        if not chat_user_token:
            message = '\n'
            logger.debug(f'user: {message}')
            writer.write(message.encode('utf-8'))
            response_in_bytes = await reader.readline()
            response = response_in_bytes.decode("utf-8")
            logger.debug(f'sender: {response}')
            print(response)
            nickname = input('Введите ваш будущий никнейм: ')
            logger.debug(f'user: {nickname}')
            writer.write(f'{nickname}\r\n'.encode('utf-8'))
            response_in_bytes = await reader.readline()
            response = response_in_bytes.decode("utf-8")
            response = json.loads(response)
            async with aiofiles.open('.env', 'a') as file:
                line = f'CHAT_USER_TOKEN={response.get("account_hash")}\n'
                await file.write(line)
            sys.stdout.write('Повторно запустите скрипт для отправки сообщений')
            exit(0)

        message = f'{chat_user_token}\r\n'
        logger.debug(f'user: {message}')
        writer.write(message.encode('utf-8'))
        await writer.drain()
        response_in_bytes = await reader.readline()
        response = response_in_bytes.decode("utf-8")
        logger.debug(f'sender: {response}')
        if response == '\n':
            logger.warning(dedent(f'''
            Неизвестный токен: {chat_user_token}
            Проверьте его или зарегистрируйте заново.
            '''))
        else:
            message = input('Введите сообщение: ')
            # message = sys.stdin.readline()
            message = f'{message}\r\n\n'
            logger.debug(f'user: {message}')
            writer.write(message.encode('utf-8'))
            await writer.drain()

    finally:
        writer.close()
        await writer.wait_closed()


def main():
    env = Env()
    env.read_env()
    host_for_chat = env.str('HOST_FOR_CHAT', '')
    port_for_chat = env.int('PORT_FOR_AUTH_CHAT', 0)
    chat_user_token = env.str('CHAT_USER_TOKEN', '')
    logging.basicConfig(
        filename='connecting_to_chat.log',
        filemode='w',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG
    )
    logger.setLevel(logging.DEBUG)
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
