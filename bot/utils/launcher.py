import asyncio
import argparse
import random
from random import randint
from typing import Any
from better_proxy import Proxy

from bot.config import settings
from bot.utils import logger
from bot.core.tapper import run_tapper
from bot.core.registrator import register_sessions
from bot.utils.accounts import Accounts
from bot.core.TgManager.tg_manager import SessionManager

from bot.utils.file_manager import load_from_json, get_support_key

start_text = """

████████╗██╗░░░██╗███████╗██████╗░░██████╗███████╗██████╗░░█████╗░████████╗
╚══██╔══╝██║░░░██║██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗╚══██╔══╝
░░░██║░░░╚██╗░██╔╝█████╗░░██████╔╝╚█████╗░█████╗░░██████╦╝██║░░██║░░░██║░░░
░░░██║░░░░╚████╔╝░██╔══╝░░██╔══██╗░╚═══██╗██╔══╝░░██╔══██╗██║░░██║░░░██║░░░
░░░██║░░░░░╚██╔╝░░███████╗██║░░██║██████╔╝███████╗██████╦╝╚█████╔╝░░░██║░░░
░░░╚═╝░░░░░░╚═╝░░░╚══════╝╚═╝░░╚═╝╚═════╝░╚══════╝╚═════╝░░╚════╝░░░░╚═╝░░░
                                                                 by Desamod                                                              
Select an action:

    1. Run bot
    2. Create session
"""


def get_proxy(raw_proxy: str) -> Proxy:
    return Proxy.from_str(proxy=raw_proxy).as_url if raw_proxy else None


async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", type=int, help="Action to perform")
    parser.add_argument("-k", "--support_key", type=str, help="Skip support key")
    action = parser.parse_args().action
    skip_support_key = parser.parse_args().support_key

    if not action:
        print(start_text)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in ["1", "2"]:
                logger.warning("Action must be 1 or 2")
            else:
                action = int(action)
                break

    if action == 2:
        await register_sessions()
    elif action == 1:
        support_key = get_support_key()
        if support_key is None:
            skip_support_key = skip_support_key if skip_support_key else ''
            if 'y' not in skip_support_key.lower():
                logger.warning("Support key is not set, you can get it by writing to me: https://t.me/desforge_cryptwo"
                               "\n Continue without a support key? (y/n)")
                answer = input("> ")
                if 'n' in answer.lower():
                    logger.info('Bot is shutting down')
                    return
        accounts = await Accounts().get_accounts()
        await run_tasks(accounts=accounts, support_key=support_key)


async def run_tasks(accounts: [Any, Any, list], support_key: str) -> None:
    tasks = []
    manager = SessionManager(api_id=settings.API_ID,
                             api_hash=settings.API_HASH,
                             peer='tverse',
                             short_name=None,
                             start_param=settings.REF_ID,
                             check_first_run=True,
                             support_key=support_key)

    random.random()
    auth_tokens = load_from_json(settings.TOKENS_PATH)
    for account in accounts:
        session_name, user_agent, raw_proxy = account.values()
        tg_session = await manager.get_tg_session(session_name=session_name, proxy=raw_proxy)
        proxy = get_proxy(raw_proxy=raw_proxy)
        auth_token = [token.get(session_name, None) for token in auth_tokens if session_name in token.keys()]
        auth_token = auth_token[0] if len(auth_token) > 0 else None
        tasks.append(asyncio.create_task(run_tapper(tg_session=tg_session, user_agent=user_agent,
                                                    auth_token=auth_token, proxy=proxy)))
        await asyncio.sleep(delay=randint(settings.START_DELAY[0], settings.START_DELAY[1]))

    await asyncio.gather(*tasks)
