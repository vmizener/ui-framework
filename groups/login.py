from services.ui.base_page import BasePage
from services.ui.page_el_handler import PageElementDescriptorHandler
from services.ui.page_elements import Button, TextBox


class SolUiLogin(BasePage):
    class PageElements(PageElementDescriptorHandler):
        login_user_email_textbox = TextBox(xpath='//*[@id="email"]')
        login_next_button = Button(xpath='//*[@id="next-btn"]')
        login_personal_account_button = Button(xpath='//*[@id="cisco-personal-login-btn"]')
        login_password_textbox = TextBox(xpath='//*[@id="password"]')
        login_login_button = Button(xpath='//*[@id="login-btn"]')

    def login(self, username, password):
        self.el.login_user_email_textbox = username
        self.el.login_next_button.click()
        self.el.login_personal_account_button.click()
        self.el.login_password_textbox = password
        self.el.login_login_button.click()
