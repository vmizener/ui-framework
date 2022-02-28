import logging
import os

from services.sol_exceptions import SolErrorException

from .globals import (
    SELE_DEFAULT_IMPLICIT_TIMEOUT,
)
from .groups.login import SolUiLogin
from .groups.title_generic import SolUiTitleGeneric
from .groups.switch import SolUiSwitch

MERAKI_UI_LOGIN_USER = "MERAKI_UI_USER_EMAIL"
MERAKI_UI_LOGIN_PASS = "MERAKI_UI_USER_PASS"


class SolUi:
    def __init__(
        self,
        driver_device,
        sol_serv,
        username=None,
        password=None,
        *,
        screenshot_location=".",
        timeout=SELE_DEFAULT_IMPLICIT_TIMEOUT,
    ):
        self.log = logging.getLogger(__name__)
        self.log.info("Instantiating Meraki SolUi")
        err_msgs = []
        if username is None:
            username = os.environ.get(MERAKI_UI_LOGIN_USER)
            if username is None:
                err_msg = f"Missing login username; input as parameter or export in env var '{MERAKI_UI_LOGIN_USER}'."
                self.log.critical(err_msg)
                err_msgs.append(err_msg)
        if password is None:
            password = os.environ.get(MERAKI_UI_LOGIN_PASS)
            if password is None:
                err_msg = f"Missing login password; input as parameter or export in env var '{MERAKI_UI_LOGIN_PASS}'."
                self.log.critical(err_msg)
                err_msgs.append(err_msg)
        if len(err_msgs) > 0:
            raise SolErrorException("\n".join(err_msgs))

        self.ss = sol_serv
        self.base_url = "https://n114.meraki.com/"
        self.screenshot_location = screenshot_location
        self.timeout = timeout
        self.browser = driver_device
        self.browser.connect(via="webdriver")

        self.generic = SolUiTitleGeneric(self)
        self.login = SolUiLogin(self)

        self.switch = SolUiSwitch(self)

        with self.login as page:
            page.login(username, password)
