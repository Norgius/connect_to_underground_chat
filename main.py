import asyncio
import argparse
import sys
import os
import json
import time
import logging
from textwrap import dedent
from datetime import datetime
from tkinter import messagebox

import aiofiles
from anyio import create_task_group
from async_timeout import timeout

from environs import Env

import gui

logger = logging.getLogger(__name__)
watchdog_logger = logging.getLogger('watchdog_logger')

loop = asyncio.get_event_loop()

watchdog_queue = asyncio.Queue()
messages_queue = asyncio.Queue()
sending_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()


def set_logging(logger, name):
    py_handler = logging.FileHandler(f"{name}.log", mode='w')
    py_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
    logger.setLevel(logging.DEBUG)
    py_handler.setFormatter(py_formatter)
    logger.addHandler(py_handler)


class InvalidToken(Exception):
    pass


async def read_msgs(host, port, queue, path_to_folder):
    try:
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
        reader, writer = await asyncio.open_connection(host, port)
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
        message = 'Соединение установлено\n'
        while True:
            current_time = datetime.now().strftime('%d.%m.%y %I:%M')
            message = f'[{current_time}] {message}'
            queue.put_nowait(message)
            path_to_file = os.path.join(path_to_folder, 'conversation_history.txt')
            async with aiofiles.open(path_to_file, 'a', encoding='utf-8') as file:
                await file.write(message)
            # sys.stdout.write(message)
            chunk = await reader.readline()
            watchdog_queue.put_nowait('New message in chat')
            message = chunk.decode('utf-8')
    except asyncio.exceptions.TimeoutError:
        logger.error('Соединение на чтение сообщений оборвано')
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)
    finally:
        writer.close()
        await writer.wait_closed()


async def save_messages(path_to_folder, queue):
    path_to_file = os.path.join(path_to_folder, 'conversation_history.txt')
    async with aiofiles.open(path_to_file, 'r') as file:
        all_file = await file.readlines()
        for message in all_file:
            queue.put_nowait(message)


async def authorise(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                    chat_user_token: str):
    message = f'{chat_user_token}\r\n'
    logger.debug(f'user: {message}')
    writer.write(message.encode('utf-8'))
    await writer.drain()
    response_in_bytes = await reader.readline()
    watchdog_queue.put_nowait('Prompt before auth')
    response = response_in_bytes.decode("utf-8")
    logger.debug(f'sender: {response}')
    response_json = json.loads(response)
    if response_json:
        logger.info(f'Выполнена авторизация. Пользователь {response_json["nickname"]}')
        return response_json["nickname"]
    logger.warning(dedent(f'''
        Неизвестный токен: {chat_user_token}
        Проверьте его или зарегистрируйтесь заново.
        '''))
    raise InvalidToken(f'Неизвестный токен: {chat_user_token}')


async def submit_message(reader: asyncio.StreamReader,
                         writer: asyncio.StreamWriter, queue: asyncio.Queue):
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
    while True:
        message = await sending_queue.get()
        logger.debug(f'user: {message}')
        message = message.replace('\\n', '')
        message = f'{message}\n\n'
        writer.write(message.encode('utf-8'))
        await writer.drain()
        await reader.readline()
        watchdog_queue.put_nowait('Message sent')


async def connect_to_chat(host: str, port: int, chat_user_token: str, queue):
    try:
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
        reader, writer = await asyncio.open_connection(host, port)

        response_in_bytes = await reader.readline()
        response = response_in_bytes.decode('utf-8')
        logger.debug(f'sender: {response}')
        if not chat_user_token:
            pass
            # await register(reader, writer)
        else:
            nickname = await authorise(reader, writer, chat_user_token)
            event = gui.NicknameReceived(nickname)
            status_updates_queue.put_nowait(event)
            await submit_message(reader, writer, queue)
    except asyncio.exceptions.TimeoutError:
        logger.error('Соединение на отправку сообщений оборвано')
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)
    finally:
        writer.close()
        await writer.wait_closed()


async def watch_for_connection():
    while True:
        try:
            async with timeout(3):
                response = await watchdog_queue.get()
                message = f'[{int(time.time())}] Connection is alive. {response}\n'
                sys.stdout.write(message)
                watchdog_logger.info(message)
        except asyncio.exceptions.TimeoutError:
            message = f'[{int(time.time())}] 3s timeout is elapsed\n'
            sys.stdout.write(message)
            watchdog_logger.info(message)
            raise ConnectionError()


async def handle_connection(host_for_chat, user_port_for_chat, port_for_chat,
                            path_to_chat_history, chat_user_token,
                            sending_queue, reconnect_timer):
    while True:
        try:
            async with create_task_group() as tg:
                tg.start_soon(watch_for_connection)
                tg.start_soon(
                    connect_to_chat,
                    *(host_for_chat, user_port_for_chat, chat_user_token, sending_queue)
                )
                tg.start_soon(
                    read_msgs,
                    *(host_for_chat, port_for_chat, messages_queue, path_to_chat_history)
                )
        except BaseException:
            await asyncio.sleep(reconnect_timer)


async def main():
    env = Env()
    env.read_env()
    host_for_chat = env.str('HOST_FOR_CHAT', 'minechat.dvmn.org')
    port_for_chat = env.int('PORT_FOR_CHAT', 5000)
    user_port_for_chat = env.int('PORT_FOR_AUTH_CHAT', 5050)
    path_to_chat_history = env.str('PATH_TO_CHAT_HISTORY', '')
    chat_user_token = env.str('CHAT_USER_TOKEN', '')
    reconnect_timer = env.int('RECONNECT_TIMER', 15)

    set_logging(logger, 'main_logger')
    set_logging(watchdog_logger, 'watchdog_logger')

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
    try:
        await asyncio.gather(
            handle_connection(
                host_for_chat,
                user_port_for_chat,
                port_for_chat,
                path_to_chat_history,
                chat_user_token,
                sending_queue,
                reconnect_timer
            ),
            save_messages(path_to_chat_history, messages_queue),
            gui.draw(messages_queue, sending_queue, status_updates_queue),
            return_exceptions=False
        )
    except InvalidToken:
        messagebox.showinfo('Неверный токен', 'Проверьте токен, сервер его не узнал')


if __name__ == '__main__':
    loop.run_until_complete(main())
