from pyrogram.session import Session


class HookSession(Session):

    def start_timeout(self: Session, start_timeout: int):
        self.START_TIMEOUT = start_timeout

    pass
