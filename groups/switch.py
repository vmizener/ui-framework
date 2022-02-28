from services.ui.base_page import BasePage

from .switch_subgroups.switches import SolUiSwitchGroupSwitches


class SolUiSwitch(BasePage):
    def __init__(self, *kwargs):
        super().__init__(*kwargs)
        self.switches = SolUiSwitchGroupSwitches(self.services)
