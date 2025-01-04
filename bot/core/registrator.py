import socks
from telethon import TelegramClient as TelethonClient

from better_proxy import Proxy
from bot.config import settings
from bot.core.agents import generate_random_user_agent
from bot.utils import logger
from bot.utils.file_manager import save_to_json


async def register_sessions() -> None:
    API_ID = settings.API_ID
    API_HASH = settings.API_HASH

    if not API_ID or not API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    session_name = input('\nEnter the session name (press Enter to exit): ')

    if not session_name:
        return None

    raw_proxy = input("Input the proxy in the format type://user:pass:ip:port (press Enter to use without proxy): ")
    session = await get_tg_client(session_name=session_name, proxy=raw_proxy)
    async with session:
        user_data = await session.get_me()

    user_agent = generate_random_user_agent(device_type='android', browser_type='chrome')
    save_to_json(f'sessions/accounts.json',
                 dict_={
                     "session_name": session_name,
                     "user_agent": user_agent,
                     "proxy": raw_proxy if raw_proxy else None
                 })
    logger.success(f'Session added successfully @{user_data.username} | {user_data.first_name} {user_data.last_name}')


async def get_tg_client(session_name: str, proxy: str | None) -> TelethonClient:
    if not session_name:
        raise FileNotFoundError(f"Not found session {session_name}")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    proxy = Proxy.from_str(proxy) if proxy else None
    tg_client = TelethonClient(
        f'sessions/{session_name}',
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        lang_code="en",
        system_lang_code="en-US",
        proxy=proxy_to_dict(proxy) if proxy else None,
    )
    return tg_client


def proxy_to_dict(proxy: Proxy) -> dict:
    proxy_type_map = {
        'http': socks.HTTP,
        'https': socks.HTTP,
        'socks5': socks.SOCKS5,
        'socks4': socks.SOCKS4,
    }

    proxy_dict = {
        'proxy_type': proxy_type_map.get(proxy.protocol, socks.HTTP),
        'addr': proxy.host,
        'port': proxy.port,
    }

    if proxy.login:
        proxy_dict['username'] = proxy.login
    if proxy.password:
        proxy_dict['password'] = proxy.password

    return proxy_dict
