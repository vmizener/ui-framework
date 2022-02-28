from services.ui.base_page import BasePage
from services.ui.page_el_handler import PageElementDescriptorHandler
from services.ui.page_elements import PositiveElement


class SolUiSwitchGroupSwitches(BasePage):
    class PageElements(PageElementDescriptorHandler):
        node_summary_count_offline_element = PositiveElement(
            xpath='//div[@class="NodeSummaryRollup"]//div[@data-testid="offline-big-number"]//div[@class="BigNumber__value"]'
        )
        node_summary_count_alerting_element = PositiveElement(
            xpath='//div[@class="NodeSummaryRollup"]//div[@data-testid="alerting-big-number"]//div[@class="BigNumber__value"]'
        )
        node_summary_count_online_element = PositiveElement(
            xpath='//div[@class="NodeSummaryRollup"]//div[@data-testid="online-big-number"]//div[@class="BigNumber__value"]'
        )
        node_summary_count_dormant_element = PositiveElement(
            xpath='//div[@class="NodeSummaryRollup"]//div[@data-testid="dormant-big-number"]//div[@class="BigNumber__value"]'
        )

    def open(self):
        super().open()
        self.generic.navigate_to("switch>switches")

    def get_switch_status_count(self):
        return {
            "offline": int(self.el.obj.node_summary_count_offline_element.text),
            "alerting": int(self.el.obj.node_summary_count_alerting_element.text),
            "online": int(self.el.obj.node_summary_count_online_element.text),
            "dormant": int(self.el.obj.node_summary_count_dormant_element.text),
        }
