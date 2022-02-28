from services.ui.base_page import BasePage
from services.ui.page_el_handler import PageElementDescriptorHandler
from services.ui.page_elements import Button


class SolUiTitleGeneric(BasePage):
    """
    This class contains code for interacting with title-screen or generic elements (e.g. the navigation hamburger menu).

    Methods in this class are readily accessible from any other page through the special `self.generic` alias.
    """

    class PageElements(PageElementDescriptorHandler):
        nav_menu_switch = Button(xpath='//div[@class="TabMenu"]//li[@data-testid="switch-menu"]')
        nav_menu_switch_opt_switches = Button(
            xpath='//div[@class="subMenu"]//li[@class="subMenuItem"][@data-testid="switches-option"]//a'
        )

    def open(self):
        """
        Override superclass open() to avoid page redirection (this class doesn't have a specific page URL)
        """
        pass

    def navigate_to(self, section):
        # SWITCH
        if section == "switch>switches":
            self.el.obj.nav_menu_switch.hover()
            self.el.nav_menu_switch_opt_switches.click()
        else:
            msg = f'Unknown navigation section "{section}"'
            self.log.error(msg)
            raise ValueError(msg)
