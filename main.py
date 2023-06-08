import asyncio


async def tcp_echo_client():
    reader, writer = await asyncio.open_connection(
        'minechat.dvmn.org', 5000)
    while True:
        chunk = await reader.readline()
        print(chunk.decode('utf-8'))


def main():
    asyncio.run(tcp_echo_client())


if __name__ == '__main__':
    main()
