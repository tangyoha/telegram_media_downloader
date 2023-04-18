import logging

from pyrogram import Client
from pyrogram import raw

from pyrogramhook.HookSession import HookSession

log = logging.getLogger(__name__)


class HookClient(Client):

    def __init__(
            self,
            name: str,
            **kwargs
    ):
        if kwargs.get("start_timeout"):
            self.START_TIME_OUT = kwargs.get("start_timeout")
            kwargs.pop("start_timeout")
        else:
            self.START_TIME_OUT = 60

        super().__init__(
            name,
            **kwargs
        )

    async def connect(
            self,
    ) -> bool:
        if self.is_connected:
            raise ConnectionError("Client is already connected")

        await self.load_session()

        self.session = HookSession(
            self, await self.storage.dc_id(),
            await self.storage.auth_key(), await self.storage.test_mode()
        )
        self.session.start_timeout(self.START_TIME_OUT)

        await self.session.start()

        self.is_connected = True

        return bool(await self.storage.user_id())

    async def start(self):
        is_authorized = await self.connect()

        try:
            if not is_authorized:
                await self.authorize()

            if not await self.storage.is_bot() and self.takeout:
                self.takeout_id = (await self.invoke(raw.functions.account.InitTakeoutSession())).id
                log.warning(f"Takeout session {self.takeout_id} initiated")

            await self.invoke(raw.functions.updates.GetState())
        except (Exception, KeyboardInterrupt):
            await self.disconnect()
            raise
        else:
            self.me = await self.get_me()
            await self.initialize()

            return self
