import sys
import asyncio
import argparse
import logging
import json
from textwrap import dedent

import aiofiles
from environs import Env

logger = logging.getLogger(__name__)


async def authorise(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                    chat_user_token: str) -> bool:
    message = f'{chat_user_token}\r\n'
    logger.debug(f'user: {message}')
    writer.write(message.encode('utf-8'))
    await writer.drain()
    response_in_bytes = await reader.readline()
    response = response_in_bytes.decode("utf-8")
    logger.debug(f'sender: {response}')
    if json.loads(response):
        return True
    logger.warning(dedent(f'''
        Неизвестный токен: {chat_user_token}
        Проверьте его или зарегистрируйтесь заново.
        '''))
    return False


async def register(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    writer.write('\n'.encode('utf-8'))
    response_in_bytes = await reader.readline()
    response = response_in_bytes.decode("utf-8")
    logger.debug(f'sender: {response}')

    nickname = input('Введите ваш будущий никнейм: ')
    nickname = nickname.replace('\\n', '')
    logger.debug(f'user: {nickname}')
    writer.write(f'{nickname}\r\n'.encode('utf-8'))
    await writer.drain()
    response_in_bytes = await reader.readline()
    response = response_in_bytes.decode("utf-8")
    chat_user_token = json.loads(response).get("account_hash")

    async with aiofiles.open('.env', 'a') as file:
        line = f'\nCHAT_USER_TOKEN={chat_user_token}\n'
        await file.write(line)
    sys.stdout.write('Повторно запустите скрипт для отправки сообщений\n')


async def submit_message(reader: asyncio.StreamReader,
                         writer: asyncio.StreamWriter):
    sys.stdout.write('Для выхода из программы введите: выход\n\n')
    while True:
        message = input('Введите сообщение: ')
        logger.debug(f'user: {message}')
        message = message.replace('\\n', '')
        if message.lower().strip() == 'выход':
            break
        message = f'{message}\r\n\n'
        writer.write(message.encode('utf-8'))
        await writer.drain()


async def connect_to_chat(host: str, port: int, chat_user_token: str):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        response_in_bytes = await reader.readline()
        response = response_in_bytes.decode('utf-8')
        logger.debug(f'sender: {response}')
        if not chat_user_token:
            await register(reader, writer)
        else:
            permission = await authorise(reader, writer, chat_user_token)
            await submit_message(reader, writer) if permission else None
    finally:
        writer.close()
        await writer.wait_closed()


def main():
    env = Env()
    env.read_env()
    host_for_chat = env.str('HOST_FOR_CHAT', 'minechat.dvmn.org')
    port_for_chat = env.int('PORT_FOR_AUTH_CHAT', 5050)
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
        logger.error(err)


if __name__ == '__main__':
    main()
