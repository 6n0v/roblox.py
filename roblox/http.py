"""
MIT License

Copyright (c) 2026 6n0v

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import asyncio
import sys
from types import TracebackType
from typing import TYPE_CHECKING, Any, Literal

import aiohttp

from . import __version__  # type: ignore
from .errors import (
    Forbidden,
    GamepassAlreadyOwned,
    GamepassAlreadyRevoked,
    InternalServerError,
    NoConnectionFound,
    NotEnoughFunds,
    NotFound,
    PendingTransactionAlreadyExists,
    Unauthorized,
    UnknownStatus,
)
from .gamepass import Gamepass, PartialGamepass
from .user import PartialUser, User

if TYPE_CHECKING:
    from . import abc

__all__ = ('Connection',)


class Route:
    __slots__ = ('method', 'module', 'path')

    def __init__(self, method: str, module: str, path: tuple[str, ...]):
        self.method: str = method

        self.module: str = module
        self.path: tuple[str, ...] = path

    def __str__(self):
        return self.url

    @property
    def base(self) -> str:
        # don't include a trailing slash here to avoid double '//' when joining paths
        return f'https://{self.module}.roblox.com'

    @property
    def url(self) -> str:
        return self.base + '/' + '/'.join(self.path)


class Http:
    def __init__(self, *, authorization: str | None = None):
        self.authorization = authorization
        self.session: aiohttp.ClientSession | None = None
        self.loop: asyncio.AbstractEventLoop | None = None

    def __str__(self) -> str:
        return (
            f'Arawe (https://github.com/6n0v/arawe {__version__}) Python/{sys.version_info[0]} aiohttp/{aiohttp.__version__}'
        )

    async def close(self):
        if self.session == None:
            raise NoConnectionFound()

        if self.loop == None:
            raise RuntimeError()

        if self.loop is not asyncio.get_running_loop():
            raise RuntimeError('This client was connected on a different event loop.')

        await self.session.close()

        if sys.platform == 'win32':
            # Zero-length sleep isn't enough on Windows Proactor loop — the
            # underlying transport needs a real tick to finish its close callbacks.
            # https://github.com/aio-libs/aiohttp/issues/4324
            await asyncio.sleep(0.25)

    async def connect(self):
        self.loop = asyncio.get_running_loop()

        connector = aiohttp.TCPConnector()

        self.session = aiohttp.ClientSession(connector=connector)

        if self.authorization:
            self.session.headers.update({'Cookie': f'.ROBLOSECURITY={self.authorization}'})
        self.session.headers.update({'User-Agent': self.__str__()})

    async def request(self, route: Route, *, data: dict | list | None = None) -> tuple[Any, int]:
        if self.session is None:
            await self.connect()

        if self.loop is not asyncio.get_running_loop():
            raise RuntimeError('This client was connected on a different event loop.')

        if self.session is None:
            raise NoConnectionFound()

        for attempt in range(5):
            async with self.session.request(
                method=route.method,
                json=data,
                url=route.url,
            ) as response:
                if response.status >= 500:
                    raise InternalServerError()

                if response.status == 401:
                    raise Unauthorized()

                elif response.status == 403:
                    csrf_token = response.headers.get('x-csrf-token')
                    if csrf_token is not None and attempt == 0:
                        self.session.headers.add('X-CSRF-TOKEN', csrf_token)
                        continue

                    payload: dict[
                        Literal['errors'], list[dict[Literal['code', 'message'], str | int]]
                    ] = await response.json()
                    error = payload['errors'][0]

                    raise Forbidden(str(error['message']))

                elif response.status == 404:
                    raise NotFound()

                if not (200 <= response.status < 300):
                    raise UnknownStatus(response.status)

                if response.content_type != 'application/json':
                    return await response.text(), response.status

                return await response.json(), response.status

        raise UnknownStatus(response.status)


class Connection:
    def __init__(self, *, authorization: str | None = None):
        self.http = Http(authorization=authorization)
        self.version: str = 'v1'

    async def __aenter__(self):
        await self.http.connect()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        await self.close()

    async def close(self):
        await self.http.close()

    async def get_user_by_name(self, name: str) -> abc.PartialUser:
        payload, _ = await self.http.request(
            Route(
                'POST',
                'users',
                (
                    self.version,
                    'usernames',
                    'users',
                ),
            ),
            data={'usernames': [name], 'excludeBannedUsers': True},
        )

        if not payload.get('data'):
            raise NotFound()

        return PartialUser(payload.get('data')[0])

    async def get_user_by_id(self, id: int) -> abc.User:
        payload, _ = await self.http.request(
            Route(
                'GET',
                'users',
                (self.version, 'users', str(id)),
            ),
        )

        return User(self, payload)

    async def get_gamepass_by_id(self, id: int) -> abc.Gamepass:
        payload, _ = await self.http.request(
            Route(
                'GET',
                'apis',
                ('game-passes', self.version, 'game-passes', str(id), 'product-info'),
            ),
        )

        return Gamepass(self, payload)

    async def get_user_gamepass_ownership(self, user_id: int, gamepass_id: int) -> bool:
        payload, _ = await self.http.request(
            Route(
                'GET',
                'inventory',
                (self.version, 'users', str(user_id), 'items', 'GamePass', str(gamepass_id)),
            ),
        )

        return bool(payload.get('data'))

    async def get_user_gamepasses(self, id: int) -> list[abc.PartialGamepass]:
        payload, _ = await self.http.request(
            Route('GET', 'apis', ('game-passes', self.version, 'users', str(id), 'game-passes'))
        )

        gamepasses: list[abc.PartialGamepass] = []
        for gamepass in payload.get('gamePasses'):
            gamepasses.append(PartialGamepass(self, gamepass))

        return gamepasses

    async def get_authenticated_user(self) -> abc.PartialUser:
        payload, _ = await self.http.request(Route('GET', 'users', (self.version, 'users', 'authenticated')))

        self._authenticated_user = PartialUser(payload)

        return PartialUser(payload)

    async def purchase_gamepass(self, product_id: int, expected_price: int, expected_seller_id: int) -> None:
        payload, _ = await self.http.request(
            Route(
                'POST',
                'apis',
                ('game-passes', self.version, 'game-passes', str(product_id), 'purchase'),
            ),
            data={
                'expectedCurrency': 1,
                'expectedPrice': expected_price,
                'expectedSellerId': expected_seller_id,
            },
        )

        if payload.get('reason') == 'AlreadyOwned':
            raise GamepassAlreadyOwned()

        short_fall_price = payload.get('shortfallPrice')

        if short_fall_price is not None and short_fall_price > 0:
            raise NotEnoughFunds()

        if payload.get('reason') == 'PendingTransactionAlreadyExists':
            raise PendingTransactionAlreadyExists()

    async def revoke_gamepass_ownership(self, id: int, expected_price: int, expected_seller_id: int) -> None:
        payload, _ = await self.http.request(
            Route('POST', 'apis', ('game-passes', self.version, 'game-passes', str(id) + ':revokeownership')),
            data={
                'expectedCurrency': 1,
                'expectedPrice': expected_price,
                'expectedSellerId': expected_seller_id,
            },
        )

        if not isinstance(payload, str) and payload.get('errorCode') == 'PassAlreadyRevoked':
            raise GamepassAlreadyRevoked()
