import asyncio
import random
import sys
from datetime import datetime
from time import time

import cloudscraper
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from bot.config import settings

from bot.utils import logger
from bot.exceptions import InvalidSession
from .agents import get_sec_ch_ua
from .headers import headers

from random import randint

from ..utils.api_checker import is_valid_endpoints
from ..utils.file_manager import save_to_json
from ..utils.tg_manager.TGSession import TGSession


def get_random_api_id():
    return f":::{str(random.random())}"

class Tapper:
    def __init__(self, tg_session: TGSession):
        self.tg_session = tg_session
        self.session_name = tg_session.session_name
        self.auth_token = None
        self.boosts = None

    async def login(self, http_client: cloudscraper.CloudScraper, tg_web_data: str, retry=0):
        try:
            payload = {"env": 'app'}
            config_resp = http_client.post('https://api.tonverse.app/config', data=payload)
            config_resp.raise_for_status()
            config = config_resp.json()
            bot_id = config['response']['telegram_bot_id']
            lang_resp = http_client.post('https://api.tonverse.app/data/lang', data={})
            lang_resp.raise_for_status()
            boost_resp = http_client.post('https://api.tonverse.app/data/boost', data={})
            boost_resp.raise_for_status()
            boost_data = boost_resp.json()
            self.boosts = boost_data['response'].get('items', [])
            if self.auth_token is None:
                payload = {
                    'bot_id': bot_id,
                    'data': tg_web_data
                }
                login_resp = http_client.post('https://api.tonverse.app/auth/telegram', data=payload)
                login_resp.raise_for_status()
                login_data = login_resp.json()
                auth_token = login_data['response'].get('session', None)
                if auth_token is not None:
                    self.auth_token = auth_token
                    payload = {self.session_name: auth_token}
                    save_to_json(settings.TOKENS_PATH, payload)
                    logger.info(f'{self.session_name} | '
                                f'Auth token successfully saved in <lc>{settings.TOKENS_PATH}</lc>')

        except Exception as error:
            if retry < 3:
                logger.warning(f"{self.session_name} | Can't logging | Retry attempt: {retry}")
                await asyncio.sleep(delay=randint(5, 10))
                await self.login(http_client, tg_web_data=tg_web_data, retry=retry + 1)

            logger.error(f"{self.session_name} | Unknown error when logging: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_proxy(self, http_client: cloudscraper.CloudScraper, proxy: str) -> None:
        try:
            response = http_client.get(url='https://ipinfo.io/ip', timeout=20)
            ip = response.text
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def get_user_info(self, http_client: cloudscraper.CloudScraper):
        try:
            payload = {
                'session': self.auth_token,
                'id': "undefined"
            }
            response = http_client.post('https://api.tonverse.app/user/info', data=payload)
            response.raise_for_status()
            response_json = response.json()
            return response_json.get('response')

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while getting user info | Error: {e}")
            await asyncio.sleep(delay=3)

    async def create_galaxy(self, http_client: cloudscraper.CloudScraper):
        try:
            start_param = self.tg_session.start_param.replace("galaxy-", "") if self.tg_session.start_param else None
            payload = {
                'session': self.auth_token,
                'stars': 100,
                'referral': start_param
            }
            response = http_client.post('https://api.tonverse.app/galaxy/begin', data=payload)
            response.raise_for_status()
            response_json = response.json()
            return response_json['response'].get('success') == 1

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while creating galaxy | Error: {e}")
            await asyncio.sleep(delay=3)

    async def get_galaxy_info(self, http_client: cloudscraper.CloudScraper, galaxy_id: str | None = None):
        try:
            payload = {'session': self.auth_token}
            if galaxy_id is not None:
                payload['id'] = galaxy_id
            response = http_client.post('https://api.tonverse.app/galaxy/get', data=payload)
            response.raise_for_status()
            response_json = response.json()
            return response_json.get('response')

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while getting galaxy info | Error: {e}")
            await asyncio.sleep(delay=3)

    async def collect_dust(self, http_client: cloudscraper.CloudScraper):
        try:
            payload = {'session': self.auth_token}
            response = http_client.post('https://api.tonverse.app/galaxy/collect', data=payload)
            response.raise_for_status()
            response_json = response.json()
            return response_json.get('response')

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while collecting dust | Error: {e}")
            await asyncio.sleep(delay=3)

    async def processing_boosts(self, http_client: cloudscraper.CloudScraper):
        try:
            boosts = await self.get_boosts(http_client)
            for boost in boosts:
                if boost['count'] > 0:
                    boost_data = [b for b in self.boosts if b['boost_id'] == boost['boost_id']][0]
                    result = await self.activate_boost(http_client, boost['boost_id'])
                    if result:
                        logger.success(f"{self.session_name} | Boost <lc>{boost_data['name']}</lc> activated!")
                    else:
                        logger.warning(f"{self.session_name} | Can't activate boost <lc>{boost_data['name']}</lc>")

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while processing boosts | Error: {e}")
            await asyncio.sleep(delay=3)

    async def activate_boost(self, http_client: cloudscraper.CloudScraper, boost_id: int):
        try:
            payload = {
                'session': self.auth_token,
                'boost_id': boost_id
            }
            response = http_client.post('https://api.tonverse.app/boost/activate', data=payload)
            response.raise_for_status()
            response_json = response.json()
            return response_json['response'].get('success') == 1
        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while activating boost | Error: {e}")
            await asyncio.sleep(delay=3)

    async def get_boosts(self, http_client: cloudscraper.CloudScraper):
        try:
            payload = {'session': self.auth_token}
            response = http_client.post('https://api.tonverse.app/user/boosts', data=payload)
            response.raise_for_status()
            response_json = response.json()
            return response_json['response'].get('items', [])
        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while getting boosts | Error: {e}")
            await asyncio.sleep(delay=3)

    async def create_stars(self, http_client: cloudscraper.CloudScraper, galaxy_id: str, stars_count: int):
        try:
            payload = {
                'session': self.auth_token,
                'galaxy_id': galaxy_id,
                'stars': stars_count
            }
            response = http_client.post('https://api.tonverse.app/stars/create', data=payload)
            response.raise_for_status()
            response_json = response.json()
            resp_data = response_json['response']
            if resp_data.get('invoice', None):
                logger.info(f'{self.session_name} | Not enough dust to create stars')
                return False
            return response_json['response'].get('success') == 1

        except Exception as e:
            logger.error(f"{self.session_name} | Unknown error while creating stars | Error: {e}")
            await asyncio.sleep(delay=3)

    async def run(self, user_agent: str, auth_token: str | None, proxy: str | None) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        self.auth_token = auth_token
        headers["User-Agent"] = user_agent
        headers['Sec-Ch-Ua'] = get_sec_ch_ua(user_agent)

        http_client = CloudflareScraper(headers=headers, connector=proxy_conn, trust_env=True,
                                        auto_decompress=False)
        scraper = cloudscraper.create_scraper()
        if proxy:
            proxies = {
                'http': proxy,
                'https': proxy,
                'socks5': proxy
            }
            scraper.proxies.update(proxies)
            await self.check_proxy(http_client=scraper, proxy=proxy)

        token_live_time = randint(3500, 3600)
        scraper.headers = http_client.headers.copy()
        while True:
            try:
                if settings.NIGHT_SLEEP:
                    current_time = datetime.now()
                    start_time = randint(settings.NIGHT_SLEEP_START_TIME[0], settings.NIGHT_SLEEP_START_TIME[1])
                    end_time = randint(settings.NIGHT_SLEEP_END_TIME[0], settings.NIGHT_SLEEP_END_TIME[1])
                    if start_time <= current_time.hour <= end_time:
                        sleep_time = randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
                        logger.info(
                            f"{self.session_name} | NIGHT_SLEEP activated, bot will sleep <y>{round(sleep_time / 60, 1)}</y> min")
                        await asyncio.sleep(sleep_time)
                        continue

                sleep_time = randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
                if time() - access_token_created_time >= token_live_time:
                    if not is_valid_endpoints():
                        logger.warning("Detected api change! Stopped the bot for safety | "
                                       "Contact me for update: <lc>https://t.me/DesQwertys</lc>")
                        sys.exit()
                    else:
                        logger.info(f"{self.session_name} | Antidetect: endpoints successfully checked")

                    tg_web_data = await self.tg_session.get_tg_web_data()
                    if tg_web_data is None:
                        continue

                    await self.login(http_client=scraper, tg_web_data=tg_web_data)
                    if self.auth_token is None:
                        token_live_time = 0
                        logger.warning(f'{self.session_name} | Failed to login | '
                                       f'Next try after <y>{round(sleep_time / 60, 1)}</y> min')
                        await asyncio.sleep(sleep_time)
                        continue

                    access_token_created_time = time()
                    token_live_time = 3600

                user_info = await self.get_user_info(http_client=scraper)
                if user_info.get('galaxy', 0) == 0:
                    await asyncio.sleep(delay=randint(5, 15))
                    if await self.create_galaxy(http_client=scraper):
                        logger.info(f'{self.session_name} | Galaxy created successfully')

                galaxy_info = await self.get_galaxy_info(http_client=scraper)
                galaxy_name = galaxy_info['title']
                galaxy_id = galaxy_info['id']
                stars = galaxy_info['stars']
                stars_max = galaxy_info['stars_max']
                dust_max = user_info['dust_max']
                dust = user_info['dust']
                logger.info(f"{self.session_name} "
                            f"| Current Galaxy: <fg #fffc32>{galaxy_name}</fg #fffc32> "
                            f"| Stars: <e>{stars}/{stars_max}</e> "
                            f"| Dust: <lc>{dust}/{dust_max}</lc>")

                if settings.AUTO_MINING:
                    await asyncio.sleep(delay=randint(5, 15))
                    dust_progress = user_info['dust_progress']
                    if dust_progress > 0.5:
                        result = await self.collect_dust(http_client=scraper)
                        if result:
                            logger.success(f"{self.session_name} | Dust collected | Reward: <lc>{result['dust']}</lc>")
                            await self.get_user_info(http_client=scraper)

                if settings.AUTO_UPGRADE:
                    const = 1.45
                    available_stars = int((dust / (stars * const)) * 100)
                    if available_stars > settings.MIN_STARS:
                        await asyncio.sleep(delay=randint(5, 15))
                        result = await self.create_stars(http_client=scraper, galaxy_id=galaxy_id,
                                                         stars_count=available_stars)
                        if result:
                            logger.success(f"{self.session_name} | Stars created "
                                           f"| Spend: <lc>{dust}</lc> Dust",
                                           f"| Got: <e>+{available_stars}</e> Stars")
                            await asyncio.sleep(delay=randint(1, 2))
                            await self.get_galaxy_info(http_client=scraper, galaxy_id=galaxy_id)
                            await self.get_user_info(http_client=scraper)

                if settings.USE_BOOSTS and user_info.get('boosts_active', False):
                    await self.processing_boosts(http_client=scraper)

                logger.info(f"{self.session_name} | Sleep <y>{round(sleep_time / 60, 1)}</y> min")
                await asyncio.sleep(delay=sleep_time)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))

            except KeyboardInterrupt:
                logger.warning("<r>Bot stopped by user...</r>")
            finally:
                if scraper is not None:
                    await http_client.close()
                    scraper.close()


async def run_tapper(tg_session: TGSession, user_agent: str, auth_token: str | None, proxy: str | None):
    try:
        await Tapper(tg_session=tg_session).run(user_agent=user_agent, auth_token=auth_token, proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_session.session_name} | Invalid Session")
