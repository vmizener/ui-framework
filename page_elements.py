"""
Extension to pyATS page elements
"""
import re
import time

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
    ElementNotInteractableException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

__all__ = [
    "Button",
    "Checkbox",
    "ComboBox",
    "DropdownSelector",
    "NegativeElement",
    "PageElement",
    "PageElementGroup",
    "PositiveElement",
    "PositiveElementGroup",
    "RadioSelection",
    "RawPath",
    "TableSelection",
    "TabPager",
    "TextBox",
    "ToggledElement",
]

DEFAULT_TIMEOUT = 10
LOCATOR_MAPPING = {
    "class": By.CLASS_NAME,
    "class_name": By.CLASS_NAME,
    "css": By.CSS_SELECTOR,
    "css_selector": By.CSS_SELECTOR,
    "id": By.ID,
    "link": By.LINK_TEXT,
    "link_text": By.LINK_TEXT,
    "name": By.NAME,
    "partial_link": By.PARTIAL_LINK_TEXT,
    "partial_link_text": By.PARTIAL_LINK_TEXT,
    "tag": By.TAG_NAME,
    "tag_name": By.TAG_NAME,
    "xpath": By.XPATH,
}
LOCATOR_MAPPING_SET = set(LOCATOR_MAPPING.keys())

###############
# Exceptions
###############


class PageElementValueException(Exception):
    """
    Exception raised when a page element encounters an invalid argument or value
    """

    pass


class PageElementYamlException(Exception):
    """
    Exception raised when a page element encounters a YAML parse error
    """

    pass


class PageElementStateException(Exception):
    """
    Exception raised when a page element encounters a state error
    """

    pass


###############
# Helper Functions
###############


def is_element_clickable(instance, locator):
    if is_element_present(instance, locator):
        return instance.find_element(locator).is_enabled()
    else:
        return False


def is_element_present(instance, locator):
    try:
        instance.find_element(locator)
        return True
    except WebDriverException:
        return False


def is_element_visible(instance, locator):
    if is_element_present(instance, locator):
        return instance.find_element(locator).is_displayed()
    else:
        return False


###############
# Base Element
###############


class PageElement:
    key = "page_element"

    @staticmethod
    def pop_locator_kwargs(kwargs):
        locator_kwargs = {}
        for locator_kwarg in LOCATOR_MAPPING_SET:
            if locator_kwarg in kwargs:
                locator_kwargs[locator_kwarg] = kwargs.pop(locator_kwarg)
        return locator_kwargs

    @staticmethod
    def translate_arguments(passthrough=False, **kwargs):
        if passthrough:
            input_set = set(kwargs.keys())
            kwarg = LOCATOR_MAPPING_SET & input_set
            if len(kwarg) == 0:
                return
            if len(kwarg) > 1:
                msg = "A maximum of 1 locator is supported; got: {}".format(kwargs)
                raise ValueError(msg)
            kwarg = next(iter(kwarg))
            return LOCATOR_MAPPING[kwarg], kwargs.pop(kwarg)
        if len(kwargs) == 0:
            return
        if len(kwargs) > 1:
            msg = "A maximum of 1 locator is supported; got: {}".format(kwargs)
            raise ValueError(msg)
        locator_name, locator_value = next(iter(kwargs.items()))
        if locator_name not in LOCATOR_MAPPING_SET:
            raise ValueError("Unknown locator {}".format(locator_name))
        return LOCATOR_MAPPING[locator_name], locator_value

    def __init__(self, **kwargs):
        self.locator = PageElement.translate_arguments(**kwargs)

    def __get__(self, instance, owner):
        return instance.driver.find_element(*self.locator)

    def __set__(self, instance, value):
        raise NotImplementedError("PageElement `set` only defined through subclassing")

    def __set_name__(self, obj, name):
        self.el_handler_cls = obj
        self.el_name = name

    @property
    def pageobj(self):
        # Parent PageElementDescriptorHandler will set pageobj in class
        return self.el_handler_cls.pageobj

    @property
    def text(self):
        return self.locate().text

    @property
    def value(self):
        element = self.locate()
        self.scroll_into_view(element)
        return str(element.get_attribute("value"))

    def locate(self):
        if not self.locator:
            # Some elements do not have a standard locator
            # TODO: clearer exception message (really only tables and pagers don't have this)
            msg = 'Page element of type "{}" does not have standard locator'.format(
                self.__class__.key
            )
            raise PageElementValueException(msg)
        return self.pageobj.find_element(*self.locator)

    def timed_lookup(self, timeout):
        """
        Retrieve the requested element, but with a specified timeout instead of the global default.

        Useful for elements with unusual loading times.
        """
        default_timeout, self.pageobj.timeout = self.pageobj.timeout, timeout
        try:
            return getattr(self.pageobj.el, self.el_name)
        finally:
            self.pageobj.timeout = default_timeout

    def is_clickable(self):
        if self.is_present():
            return self.locate().is_enabled()
        return False

    def is_present(self):
        try:
            self.locate()
            return True
        except WebDriverException:
            return False

    def is_invisible(self):
        if self.is_present():
            return not self.locate().is_displayed()
        return False

    def is_visible(self):
        if self.is_present():
            return self.locate().is_displayed()
        return False

    def scroll_into_view(self, element=None):
        """
        Scroll the current viewport until the given element is centered within the viewport bounds.
        If element is not supplied, scrolls this element.

        :kwarg element selenium.remote.webelement.WebElement:  Element to scroll into view.
        """
        if element is None:
            element = self.locate()
        self.pageobj.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

    def force_click(self):
        """
        Directly submit a click event to this element, ignoring UI overlays.

        Note: This does not simulate user behavior and hence should be avoided for user test-cases.
        """
        self.pageobj.execute_script("arguments[0].click();", self.locate())

    def drag_onto(self, target_el_name, delay=0):
        """
        Drags this element onto the element tagged by the second.
        Will wait for the given delay before releasing the dragged element.

        :param target_el_name str:  Tag of the element to drag the first element onto
        :kwarg delay int:           Delay to wait before releasing, in seconds
        """
        el_to_move = self.locate()
        target_el = getattr(self.pageobj.el.obj, target_el_name).locate()
        ActionChains(self.pageobj).click_and_hold(el_to_move).move_to_element(target_el).perform()
        time.sleep(delay)
        ActionChains(self.pageobj).release(target_el).perform()

    def hover(self, *, click=False):
        """
        Hover the mouse over this element.
        Will also click the element if specified.

        :kwarg click bool:  Whether to click after hovering the mouse.
        """
        if click:
            ActionChains(self.pageobj).move_to_element(self.locate()).click().perform()
        else:
            ActionChains(self.pageobj).move_to_element(self.locate()).perform()

    def wait_until_clickable(self, timeout=None):
        return self.pageobj.el.wait.until.element_to_be_clickable(
            self.locator,
            timeout=timeout,
        )

    def wait_until_present(self, timeout=None):
        return self.pageobj.el.wait.until.presence_of_element_located(
            self.locator,
            timeout=timeout,
        )

    def wait_until_invisible(self, timeout=None):
        return self.pageobj.el.wait.until.invisibility_of_element_located(
            self.locator,
            timeout=timeout,
        )

    def wait_until_visible(self, timeout=None):
        return self.pageobj.el.wait.until.visibility_of_element_located(
            self.locator,
            timeout=timeout,
        )


class PageElementGroup(PageElement):
    key = "page_element_group"

    @staticmethod
    def _raise_unsupported_op_error():
        msg = "PageElementGroup objects do not support this operation"
        raise TypeError(msg)

    @property
    def text(self):
        return [el.text for el in self.locate()]

    @property
    def value(self):
        ret = []
        for element in self.locate():
            self.scroll_into_view(element)
            ret.append(str(element.get_attribute("value")))
        return ret

    def locate(self):
        if not self.locator:
            # Some elements do not have a standard locator
            # TODO: clearer exception message (really only tables and pagers don't have this)
            msg = 'Page element of type "{}" does not have standard locator'.format(
                self.__class__.key
            )
            raise PageElementValueException(msg)
        return self.pageobj.find_elements(*self.locator)

    def is_clickable(self):
        if self.is_present():
            return any([el.is_enabled() for el in self.locate()])
        return False

    def is_present(self):
        try:
            self.locate()
            return True
        except WebDriverException:
            return False

    def is_invisible(self):
        if self.is_present():
            return any([not el.is_displayed() for el in self.locate()])
        return False

    def is_visible(self):
        if self.is_present():
            return any([el.is_displayed() for el in self.locate()])
        return False

    def force_click(self):
        self._raise_unsupported_op_error()

    def wait_until_clickable(self, timeout=None, *, wait_all=False):
        if wait_all:

            def all_elements_to_be_clickable(driver):
                elements = driver.find_elements(self.locator)
                for element in elements:
                    if not element.is_enabled():
                        return False
                return elements

            condition = all_elements_to_be_clickable
        else:

            def any_elements_to_be_clickable(driver):
                elements = driver.find_elements(self.locator)
                return [element for element in elements if element.is_enabled()]

            condition = any_elements_to_be_clickable
        return self.pageobj.el.wait.until(condition, timeout=timeout)

    def wait_until_present(self, timeout=None):
        condition = EC.presence_of_all_elements_located(self.locator)
        return self.pageobj.el.wait.until(condition, timeout=timeout)

    def wait_until_invisible(self, timeout=None, *, wait_all=False):
        if wait_all:

            def all_elements_to_be_invisible(driver):
                elements = driver.find_elements(self.locator)
                for element in elements:
                    if element.is_displayed():
                        return False
                return elements

            condition = all_elements_to_be_invisible
        else:

            def any_elements_to_be_invisible(driver):
                elements = driver.find_elements(self.locator)
                return [element for element in elements if not element.is_displayed()]

            condition = any_elements_to_be_invisible
        return self.pageobj.el.wait.until(condition, timeout=timeout)

    def wait_until_visible(self, timeout=None, *, wait_all=False):
        if wait_all:
            condition = EC.visibility_of_all_elements_located(self.locator)
        else:
            condition = EC.visibility_of_any_elements_located(self.locator)
        return self.pageobj.el.wait.until(condition, timeout=timeout)


###############
# Page Elements
###############


class Button(PageElement):
    """
    Simple button object.
    Supports scrolling into vision and clickability checks.

    You can include the tag 'disabled' to provide an xpath to check for whether this button is disabled.

    Tags:
        xpath:      path to the element to click on
    Optional Tags:
        disabled:   path to the element to check for to see if this button is disabled
    """

    key = "button"

    def __init__(self, **kwargs):
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))
        self.disabled = None
        for key, val in kwargs.items():
            if key == "disabled":
                self.disabled = (By.XPATH, val)
            else:
                msg = 'Unknown button option "{}"'.format(key)
                raise PageElementYamlException(msg)

    def __get__(self, instance, owner):
        return self

    def __set__(self, instance, value):
        msg = "You cannot assign values to a Button object."
        raise PageElementStateException(msg)

    def __getattr__(self, name):
        button_element = self.wait_until_visible(timeout=self.pageobj.timeout)
        self.scroll_into_view(button_element)
        return getattr(button_element, name)

    def click(self, *, retry_attempts=2, retry_delay=2, attempt_force_on_fail=True):
        if self.disabled is not None:
            try:
                self.pageobj.find_element(*self.disabled)
                msg = "Could not click button: button is disabled."
                raise PageElementStateException(msg)
            except NoSuchElementException:
                pass
        self.pageobj.log.debug("Clicking button tagged: %s", self.el_name)
        while True:
            try:
                button_element = self.wait_until_visible(timeout=self.pageobj.timeout)
                self.scroll_into_view(button_element)
                button_element.click()
            except WebDriverException:
                self.pageobj.log.warning(
                    "Encountered exception when attempting to click button tagged: %s",
                    self.el_name,
                )
                retry_attempts -= 1
                if retry_attempts > 0:
                    self.pageobj.log.warning("Retrying after %s seconds", retry_delay)
                    time.sleep(retry_delay)
                elif attempt_force_on_fail:
                    self.pageobj.log.warning("Directly force-clicking element as last resort")
                    self.force_click()
                    break
                else:
                    raise
            else:
                break

    def navigate(self, *, check=None, check_spinner=True, sleep=0):
        if check and check_spinner:
            msg = "You must specify at most 1 check"
            raise TypeError(msg)
        self.pageobj.log.debug("Navigating off tag: %s", self.el_name)
        try:
            self.wait_until_visible()
            self.locate().click()
            time.sleep(0.5)
        except WebDriverException:
            msg = 'Encountered error attempting to click navigation element "{}"'.format(
                self.el_name
            )
            if check:
                msg += ", check: {}".format(check)
            self.pageobj.log.error(msg)
            raise
        if check is not None:
            msg = "Timeout navigating {}".format(self.el_name)
            self.pageobj.assert_timeout(getattr(self.pageobj.el, check), msg)
            time.sleep(0.5)  # Wait an additional half second for good measure
        elif check_spinner:
            self.pageobj.generic.wait_for_spinner()
        time.sleep(sleep)


class Checkbox(PageElement):
    """
    Simple checkbox object that supports assignment and lookup.

    Also supports disjointed checkboxes.
    i.e. when a checkbox's clickable toggle element and internal state element are separate.
    Disjointed checkboxes must specify an additional 'toggle' xpath key for where to click to toggle.

    Tags:
        xpath:      path to checkbox element to read from (or assign to)
    Optional Tags:
        toggle:     path to the element to click on to toggle the checkbox (if not the checkbox itself).
    """

    key = "checkbox"

    def __init__(self, **kwargs):
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))
        self.toggle_el = None
        for key, val in kwargs.items():
            if key == "toggle":
                self.toggle_el = (By.XPATH, val)
            else:
                msg = 'Unknown checkbox option "{}"'.format(key)
                raise PageElementYamlException(msg)
        if self.toggle_el is None:
            self.toggle_el = self.locator

    def __get__(self, instance, owner):
        element = instance.find_element(self.locator)
        return element.is_selected()

    def __set__(self, instance, check):
        checkbox = instance.find_element(self.locator)
        checked = instance.find_element(self.locator).is_selected()
        if (checked and not check) or (not checked and check):
            instance.log.debug('Toggling checkbox from state "{}" to "{}"'.format(checked, check))
            # element = instance.wait.until.element_to_be_clickable(self.toggle_el, timeout=instance.timeout)
            # self.scroll_into_view(element)
            # element.click()
            self.scroll_into_view(checkbox)
            checkbox.click()


class ComboBox(PageElement):
    """
    Combination of a textbox and a dropdown context.

    Types the assigned value into the box, then selects the first element in the dropdown.
    Raises an error if no options appear, and a warning if more than one option appears (unless 'ignore_selections' is set).
    Unlike a textbox, a combobox always hits enter after typing in its contents.
    If the 'lookup_ctx' field isn't given, it will raise a warning and simply use whatever the autocomplete gives it.
    If 'multiselect_counter' isn't given, it will throw in 10 backspaces into the textfield after clearing for good measure.

    Tags:
        xpath:      path to the combobox element to read from and write text to.
    Optional Tags:
        lookup_ctx_xpath:       Path to search for dropdown options from (after typing).
        multiselect_counter:    Path to list existing selections, if this is a multi-selection combobox.
        click_escape_xpath:     Path to element to click to escape the pulldown (if the escape key doesn't work).
        ignore_selections:      Do not select dropdown options, only type.
        escape_delay:           Seconds to wait between entering a combobox value and checking to escape it (default: 0).
                                A negative value indicates no escape.
        populate_delay:         Seconds to wait between clicking the combobox and selecting its values (default: 2).
        hidden:     Whether this textbox is hidden (e.g. for file input textboxes).
    """

    key = "combobox"

    def __init__(self, **kwargs):
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))
        self.lookup_ctx = None
        self.multi_counter = None
        self.click_escape_locator = None
        self.ignore_selections = False
        self.escape_delay = 0
        self.populate_delay = 2
        self.hidden = False
        for key, val in kwargs.items():
            if key == "lookup_ctx_xpath":
                self.lookup_ctx = (By.XPATH, val)
            elif key == "multiselect_counter":
                self.multi_counter = (By.XPATH, val)
            elif key == "click_escape_xpath":
                self.click_escape_locator = (By.XPATH, val)
            elif key == "ignore_selections":
                self.ignore_selections = True
            elif key == "escape_delay":
                self.escape_delay = int(val)
            elif key == "populate_delay":
                self.populate_delay = int(val)
            elif key == "hidden":
                self.hidden = True
            else:
                msg = 'Unknown combobox option "{}"'.format(key)
                raise PageElementYamlException(msg)

    def __get__(self, instance, owner):
        if self.hidden:
            self.wait_until_present(timeout=instance.timeout)
        else:
            self.wait_until_clickable(timeout=instance.timeout)
        return self.value

    def __set__(self, instance, value):
        if self.hidden:
            combobox = self.wait_until_present(timeout=instance.timeout)
        else:
            combobox = self.wait_until_clickable(timeout=instance.timeout)
            combobox.clear()
        if self.multi_counter is not None:
            # If we have a way to check for existing entries, throw in the appropriate number of backspaces also
            cnt = len(instance.find_elements(self.multi_counter))
            combobox.send_keys(Keys.BACKSPACE * cnt)
        else:
            # Otherwise just throw in a an arbitrary number for good measure
            combobox.send_keys(Keys.BACKSPACE * 10)
        try:
            if isinstance(value, str):
                opts = [value]
            else:
                opts = iter(value)
        except TypeError:
            msg = "Combobox elements must be assigned either a string or an iterable of strings"
            instance.log.error(msg)
            raise
        for opt in opts:
            opt = str(opt)
            instance.log.debug('Setting combobox to value "{}"'.format(opt))
            fill_attempts = 3
            while fill_attempts > 0:
                try:
                    combobox.clear()  # Ensure textfield is empty at start of each iteration
                    combobox.send_keys(opt)
                except ElementNotInteractableException:
                    instance.log.warning(
                        'Encountered error while setting combobox to "{}"'.format(opt)
                    )
                    instance.log.warning("Retrying with ActionChains")
                    ActionChains(instance).move_to_element(combobox).click().pause(1).send_keys(
                        Keys.END
                    )
                    ActionChains(instance).move_to_element(combobox).click().pause(1).send_keys(
                        opt
                    ).perform()
                if self.lookup_ctx is None:
                    msg = 'Combobox @ "{}" defined without lookup context!  (Try using a textbox instead?)'.format(
                        self.locator[1]
                    )
                    instance.log.warning(msg)
                    combobox.send_keys("\n")
                    break
                time.sleep(self.populate_delay)
                try:
                    lookup_ctx_objects = instance.wait.until.visibility_of_any_elements_located(
                        self.lookup_ctx, timeout=instance.timeout
                    )
                except TimeoutException:
                    msg = 'Timeout waiting for combobox context to appear with input: "{}"'.format(
                        opt
                    )
                    instance.log.error(msg)
                    fill_attempts -= 1
                    if fill_attempts > 0:
                        time.sleep(2)
                        continue
                    raise
                try:
                    if self.ignore_selections:
                        # TODO: wolverine might not support this
                        instance.log.debug("Ignoring combobox selections")
                        combobox.send_keys("\n")
                        break
                    click_attempts = 3
                    while click_attempts > 0:
                        try:
                            # Try to click the top option
                            top_child_locator = (
                                By.XPATH,
                                "{}/*[1]".format(self.lookup_ctx[1]),
                            )
                            top_child_obj = instance.wait.until.element_to_be_clickable(
                                top_child_locator, timeout=instance.timeout
                            )
                            seen_value = top_child_obj.text
                            if re.search(
                                r"[Ll]oading\.\.\.", seen_value
                            ):  # TODO: identify other loading text?
                                instance.log.warning(
                                    'Waiting on combobox loader: "%s"',
                                    seen_value,
                                )
                                time.sleep(2)
                                click_attempts -= 1
                                continue
                            if seen_value != opt:
                                instance.log.warning(
                                    'Top child value is not an exact match: expected "{}", got "{}"'.format(
                                        opt, seen_value
                                    )
                                )
                            # TODO: find a generic way to verify if the top element is interactive (e.g. not a "No Children" message or something)
                            instance.log.debug('Selecting combobox option "%s"', seen_value)
                            top_child_obj.click()
                            break
                        except (
                            AttributeError,
                            NoSuchElementException,
                            StaleElementReferenceException,
                        ) as err:
                            instance.log.warning("Encountered error:\n%s", err)
                            instance.log.warning(
                                'Failed to select combobox "%s" top option "%s"',
                                self.el_name,
                                opt,
                            )
                            click_attempts -= 1
                            if click_attempts > 0:
                                instance.log.warning("Retrying")
                    else:
                        # Try typing it in instead
                        # TODO: new comboboxes in Wolverine might not support this?
                        msg = "Failed to click top element in combobox context, typing instead"
                        instance.log.warning(msg)
                        top_child_text = lookup_ctx_objects[0].text.split("\n")[0]
                        combobox.clear()
                        combobox.send_keys(top_child_text)
                        combobox.send_keys("\n")
                    break
                finally:
                    # Escape the dropdown if it's still visible for some reason
                    try:
                        if self.escape_delay > 0:
                            msg = "Waiting {} second(s) before escaping combobox".format(
                                self.escape_delay
                            )
                            instance.log.debug(msg)
                            time.sleep(self.escape_delay)
                        if self.escape_delay >= 0 and (
                            lookup_ctx_objects[0].is_displayed()
                            or lookup_ctx_objects[0].is_enabled()
                        ):
                            if self.click_escape_locator:
                                instance.log.debug("Clicking out of combobox")
                                click_escape_obj = instance.wait.until.element_to_be_clickable(
                                    self.click_escape_locator
                                )
                                click_escape_obj.click()
                            else:
                                instance.log.debug("Escaping out of combobox")
                                combobox.send_keys(Keys.ESCAPE)
                    except (
                        StaleElementReferenceException,
                        NoSuchElementException,
                    ):
                        pass
                break


class DropdownSelector(PageElement):
    """
    Describes a dropdown context.

    Define the xpath to the open the dropdown, then define the paths to each of the selectable elements.
    e.g. from YAML:

    my_dropdown_context:
        xpath: //path/to/dropdown/context/button
        option1: //path/to/dropdown/option/1
        option2: //path/to/dropdown/option/2
        etc.

    Selection of a dropdown option is then assigning this descriptor to the option name.

    e.g. self.my_dropdown_context = 'option1'

    In addition, you may instead define a lookup context for dynamically looking up options with a special entry "xpath_lookup_ctx".
    If this element is defined, assignment treats the value as a regular expression to select options from the div given by xpath_lookup_ctx.
    This behavior is in addition to manually defined options above; those will be checked first if they are defined.

    e.g. from YAML:

    my_dropdown_context:
        xpath: //path/to/dropdown/context/button
        fixed_option: //path/to/fixed/option
        lookup_ctx_xpath: //path/to/lookup/context
        lookup_ctx_regex_format: title="{}"

    Selection is then a regular expression string.

    e.g. for an option with html "<li class='option'><a title="option 1">My Option</a></li>":
    self.my_dropdown_context = 'option 1'

    Note this only checks the immediate children of xpath_lookup_ctx.

    Tags:
        xpath:  path to the dropdown context button
    Optional Tags:
        *:                          Name of the dropdown option to click on, mapping to its xpath
        lookup_ctx_xpath:           Path to look for dropdown options in ()
        lookup_ctx_regex_format:    Regex pattern to match dropdown options' outer HTML to (with arg formatted in)
        populate_delay:             Seconds to wait between clicking the dropdown and selecting its values.
    """

    key = "dropdown"

    def __init__(self, **kwargs):
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))
        self.lookup_ctx = None
        self.lookup_re_fmt = None
        self.options = {}
        self.populate_delay = 0
        for key, val in kwargs.items():
            if key == "lookup_ctx_xpath":
                self.lookup_ctx = (By.XPATH, val)
            elif key == "lookup_ctx_regex_format":
                self.lookup_re_fmt = val
            elif key == "populate_delay":
                self.populate_delay = int(val)
            else:
                self.options[key] = (By.XPATH, val)
        if self.locator is None:
            raise PageElementYamlException("Dropdown contexts must define an xpath.")
        if (self.lookup_ctx or self.lookup_re_fmt) and not (
            self.lookup_ctx and self.lookup_re_fmt
        ):
            raise PageElementYamlException(
                "Pattern-based dropdown context must define both a lookup context and a regex format."
            )

    def __get__(self, instance, owner):
        # TODO: return current dropdown value as a string?
        raise NotImplementedError("someday")

    def __set__(self, instance, value):
        value = str(value)
        instance.log.debug('Setting dropdown to value "{}"'.format(value))
        attempts = 3  # TODO: don't hardcode
        while attempts > 0:
            try:
                if not is_element_visible(instance, (By.XPATH, self.lookup_ctx)):
                    element = self.wait_until_visible(timeout=instance.timeout)
                    self.scroll_into_view(element)
                    element.click()
                time.sleep(self.populate_delay)
                if value in self.options:
                    element = instance.wait.until.visibility_of_element_located(
                        self.options[value], timeout=instance.timeout
                    )
                    self.scroll_into_view(element)
                    element.click()
                elif self.lookup_ctx is None:
                    raise PageElementValueException(
                        'Ilegal dropdown option "{}".  Choose from {}.'.format(
                            value, list(self.options.keys())
                        )
                    )
                else:
                    instance.wait.until.presence_of_element_located(
                        self.lookup_ctx, timeout=instance.timeout
                    )
                    ctx = instance.find_elements(self.lookup_ctx)
                    match = None
                    for webelement in ctx:
                        pattern, html = self.lookup_re_fmt.format(
                            re.escape(value)
                        ), webelement.get_attribute("outerHTML")
                        if re.search(pattern, html):
                            instance.log.debug(
                                'Matched dropdown option using pattern "{}" to HTML option "{}"'.format(
                                    pattern, html
                                )
                            )
                            if match is not None:
                                msg = "Multiple matches for dropdown element found (listed below). Try using a more specific regular expression.\n{}\n{}"
                                msg = msg.format(
                                    match.get_attribute("outerHTML"),
                                    webelement.get_attribute("outerHTML"),
                                )
                                raise PageElementStateException(msg)
                            match = webelement
                    if not match:
                        msg = 'No matches found for dropdown element "{}" with regex "{}" in ctx "{}".  Try using a less specific regex.'.format(
                            value,
                            self.lookup_re_fmt.format(value),
                            webelement.get_attribute("outerHTML"),
                        )
                        raise PageElementStateException(msg)
                    self.scroll_into_view(element)
                    match.click()
                return
            except (TimeoutException, WebDriverException):
                attempts -= 1
                if attempts > 0:
                    instance.log.warning(
                        'Failed to assign dropdown "%s" value "%s"; retrying',
                        self.el_name,
                        value,
                    )
                    time.sleep(2)
                else:
                    raise


class NegativeElement(PageElement):
    """
    Describes an element that is expected to disappear, be deleted, or become hidden.
    If there are multiple element matches, will wait for each element to do so.

    Generally used with loaders and deleted elements.  It is recommended to use these elements in conjunction with assert-like checks.

    Tags:
        xpath:  path to the negative element
    """

    key = "negative_element"

    def __get__(self, instance, owner):
        start = time.time()
        while time.time() - start < instance.timeout:
            elements = instance.find_elements(self.locator)
            for element in elements:
                try:
                    if not element.is_displayed():
                        continue
                    instance.wait.until_not.visibility_of(
                        element,
                        timeout=min(
                            instance.timeout,
                            instance.timeout - time.time() + start,
                        ),
                    )
                    # instance.wait.until_not.visibility_of(element, timeout=1000)
                    # Repeat element lookup
                    break
                except TimeoutException:
                    return False
                except StaleElementReferenceException:
                    # We consider stale elements as having disappeared
                    continue
            else:
                break
        else:
            return False
        return True

    def __set__(self, instance, value):
        msg = "You cannot assign values to a NegativeElement instanceect (use it only to check if an element exists)."
        raise TypeError(msg)


class PositiveElementGroup(PageElementGroup):
    """
    Describes a group of elements that are expected to appear.
    """

    key = "positive_element_group"

    def __get__(self, instance, owner):
        try:
            instance.wait.until.visibility_of_any_elements_located(
                self.locator, timeout=instance.timeout
            )
        except TimeoutException:
            return False
        return True

    def __set__(self, instance, value):
        msg = "You cannot assign values to a PositiveElementGroup instances (use it only to check if an element exists)."
        raise TypeError(msg)


class PositiveElement(PageElement):
    """
    Describes an element that is expected to appear.
    If there are multiple element matches, will wait for each element to do so.

    Opposite behavior of a NegativeElement.
    Generally used when navigating windows or creating elements.  It is recommended to use these elements in conjunction with assert-like checks.

    Tags:
        xpath:  path to the positive element
    """

    key = "positive_element"

    def __get__(self, instance, owner):
        try:
            instance.wait.until.visibility_of_element_located(
                self.locator, timeout=instance.timeout
            )
        except TimeoutException:
            return False
        return True

    def __set__(self, instance, value):
        msg = "You cannot assign values to a PositiveElement instances (use it only to check if an element exists)."
        raise TypeError(msg)


class RadioSelection(PageElement):
    """
    Describes a radio selection context.

    Similar to a dropdown selection, does not take an xpath (only fixed options).
    See the docstring for DropdownSelector for more info on YAML context and selection.
    Regex lookup is not supported for radio selection.

    Optional Tags:
        *:  name of the radio option to click on, mapping to the xpath of where to click for it
    """

    key = "radio_selection"

    def __init__(self, **kwargs):
        # Locator will refer to selected option, or first option listed in yaml if none selected yet
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))

        self.options = {}
        for key, val in kwargs.items():
            self.options[key] = (By.XPATH, val)
            if self.locator is None:
                self.locator = self.options[key]

    def __get__(self, instance, owner):
        # TODO: get current radio option as a string?
        raise NotImplementedError("someday")

    def __set__(self, instance, value):
        if value not in self.options:
            raise PageElementValueException(
                'Ilegal radio option "{}".  Choose from {}.'.format(
                    value, list(self.options.keys())
                )
            )
        self.locator = self.options[value]
        element = instance.wait.until.element_to_be_clickable(
            self.locator, timeout=instance.timeout
        )
        self.scroll_into_view(element)
        element.click()


class RawPath(PageElement):
    """
    Describes a raw locator element, ignoring framework constructions.
    """

    key = "raw_path"

    def __init__(self, **kwargs):
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))
        if kwargs:
            msg = 'RawPath elements do not have extra options: "{}"'.format(list(kwargs.keys()))
            raise PageElementYamlException(msg)

    def __get__(self, instance, owner):
        return self.locator[1]

    def __set__(self, instance, value):
        msg = "You cannot assign values to a RawPath instanceect."
        raise TypeError(msg)


class TableSelection(PageElement):
    """
    Describes a dynamic table context.

    Functions like an instanceect with page elements as properties, corresponding to rows of a table.
    You need to define a label xpath, input xpath, and toggle xpath describing rows of the table.
    If the xpaths generate multiple matches, it will associate matches in the order they appear.
    Throws an exception if the amount of matches for each type aren't equal.

    Tags:
        label_xpath:        Corresponds to the dictionary keys for each table row, matching the 'text' attribute of each match
    Optional Tags:
        input_xpath:        Corresponds to the checkbox HTML element for each checkbox element (for state lookup)
        toggle_xpath:       Corresponds to the click location to toggle each checkbox element

        info_xpath_<key>:   Adds an entry into each row corresponding to the matched element, accessible by <key>

        option_rel_xpath_<key>:     Adds an entry into each row corresponding to a relative element to the label_xpath element, accessible by <key>
                                    Returns `None` if the element does not exist

        label_parse:        Regex to parse label text by and use as row key (default: use entire label)
        negative_element:   Identifies an element which indicates the table is empty (default: will wait for lookup timeout)
        scroll_el:          Identifies a scroller element for the table (only necessary for dynamic tables) (default: use window scroll)
        anonymous:          Causes the table selection to ignore labels as lookup keys, assigning them instead by parsed order
                            Labels are still used for row detection, and are saved as normal (default: False)
    """

    key = "table_selection"

    class TableSelectionObj:
        """
        Object we can instantiate with descriptors and toss safely
        """

        def __getattribute__(self, name):
            value = super().__getattribute__(name)
            if hasattr(value, "__get__"):
                value = value.__get__(self, self.__class__)
            return value

        def __setattr__(self, name, value):
            try:
                obj = super().__getattribute__(name)
            except AttributeError:
                pass
            else:
                if hasattr(obj, "__set__"):
                    return obj.__set__(self, value)
            if not isinstance(value, TableSelection.TableRow):
                err_msg = "TableSelectionObj only accepts TableRow as attribute"
                raise TypeError(err_msg)
            return super().__setattr__(name, value)

        def __contains__(self, item):
            return item in vars(self)

        def __getitem__(self, key):
            return list(self)[key]

        def __setitem__(self, key, value):
            return self.__setattr__(list(self)[key].label, value)

        def __iter__(self):
            # Returns generator of table rows in idx order
            return iter(sorted(vars(self).values(), key=lambda el: el.idx))

        def __len__(self):
            return len(vars(self))

    class TableRow:
        """
        Represents a row in a table
        """

        def __init__(
            self,
            parent_table,
            ctx,
            idx,
            label,
            label_group_locator,
            info_locator_map,
            option_rel_locator_map,
            *,
            scroll_info=None,
            selection_info=None
        ):
            self.parent_table = parent_table
            self.ctx = ctx
            self.idx = idx
            self.label_group_locator = label_group_locator
            self.info_locator_map = info_locator_map
            self.option_rel_locator_map = option_rel_locator_map
            self.label = label

            self.input_locator = None
            self.toggle_locator = None
            self.scroller_locator = None
            self.scroll_right = None
            if scroll_info:
                self.scroller_locator, self.scroll_right = scroll_info
            if selection_info:
                self.input_locator, self.toggle_locator = selection_info

        def __set__(self, instance, check):
            checked = self.is_selected
            if (checked and not check) or (not checked and check):
                self.find_element(self.toggle_locator).click()

        def __getattr__(self, name):
            if name in self.info_locator_map:
                return self.find_element(self.info_locator_map[name])
            elif name in self.option_rel_locator_map:
                label_el = self.find_element(self.label_group_locator)
                try:
                    return label_el.find_element(*self.option_rel_locator_map[name])
                except NoSuchElementException:
                    self.ctx.log.warning(
                        'Couldn\'t find optional column entry "{}"in row'.format(name)
                    )
                    return None
            return super().__getattribute__(name)

        @property
        def is_selected(self):
            if not self.input_locator:
                raise PageElementValueException("Table does not allow row selection")
            return self.find_element(self.input_locator).is_selected()

        def find_element(self, locator):
            try:
                table_els = TableSelection.find_table_elements(
                    self.ctx,
                    locator,
                    scroller_locator=self.scroller_locator,
                    scroll_right=self.scroll_right,
                )
                el = table_els[self.idx]
            except IndexError:
                msg = (
                    "Row elements are misalligned - check construction on locator:\n\t{}\n".format(
                        locator
                    )
                )
                msg += "Table construction:\n\t{}\n".format(table_els)
                msg += "Element index:\n\t{}".format(self.idx)
                raise PageElementStateException(msg)
            else:
                self.parent_table.scroll_into_view(el)
                return el

    def __init__(self, **kwargs):
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))
        self.label_group_locator = None
        self.input_group_locator = None
        self.toggle_group_locator = None

        self.info_group_locators = {}
        self.option_rel_group_locators = {}
        self.scroller_locator = None
        self.scroll_right = False

        self.label_parse = None
        self.negative_locator = None
        self.anonymous = False

        for key, val in kwargs.items():
            locator = (By.XPATH, val)
            if key == "label_xpath":
                self.label_group_locator = locator
            elif key == "input_xpath":
                self.input_group_locator = locator
            elif key == "toggle_xpath":
                self.toggle_group_locator = locator
            elif key.startswith("info_xpath_"):
                prefix_len = len("info_xpath_")
                info_label = key[prefix_len:]
                if not (len(info_label) > 0 and info_label not in self.info_group_locators):
                    raise PageElementYamlException(
                        "Invalid info xpath element in TableSelection: {}".format(key)
                    )
                self.info_group_locators[info_label] = locator
            elif key.startswith("option_rel_xpath_"):
                prefix_len = len("option_rel_xpath_")
                option_label = key[prefix_len:]
                if not (
                    len(option_label) > 0 and option_label not in self.option_rel_group_locators
                ):
                    raise PageElementYamlException(
                        "Invalid option relative xpath element in TableSelection: {}".format(key)
                    )
                self.option_rel_group_locators[option_label] = locator
            elif key == "label_parse":
                self.label_parse = val
            elif key == "negative_element":
                # TODO: actually use this
                self.negative_locator = locator
            elif key.startswith("scroll_el"):
                self.scroller_locator = locator
                if "right" in key:
                    self.scroll_right = True
            elif key == "anonymous":
                self.anonymous = True
            else:
                msg = 'Unknown table selection option: "{}"'.format(key)
                raise PageElementYamlException(msg)
        if not self.label_group_locator:
            raise PageElementYamlException("Label xpath is required for table selections")
        if not (
            (self.input_group_locator and self.toggle_group_locator)
            or (not self.input_group_locator and not self.toggle_group_locator)
        ):
            raise PageElementYamlException(
                "Input and toggle xpaths must either both be provided or neither"
            )

    def __get__(self, instance, owner):
        instance.log.debug(
            "Constructing {}TableSelection".format("anonymous " if self.anonymous else "")
        )
        table = TableSelection.TableSelectionObj()
        labels = TableSelection.find_table_elements(
            instance,
            self.label_group_locator,
            scroller_locator=self.scroller_locator,
            scroll_right=self.scroll_right,
        )
        for idx, label_el in enumerate(labels):
            self.scroll_into_view(label_el)
            label = label_el.text
            if self.label_parse is not None:
                try:
                    label = re.search(self.label_parse, label_el.text).groups()[0]
                except IndexError:
                    self.log.warning("Failed to parse label! Using original string")
                    self.log.warning('Original: "{}"'.format(label_el.text))
                    self.log.warning('Parse pattern: "{}"'.format(self.label_parse))
                    label = label_el.text
            else:
                label = label_el.text
            table_row = TableSelection.TableRow(
                self,
                instance,
                idx,
                label,
                self.label_group_locator,
                self.info_group_locators,
                self.option_rel_group_locators,
                scroll_info=(self.scroller_locator, self.scroll_right),
                selection_info=(
                    self.input_group_locator,
                    self.toggle_group_locator,
                ),
            )
            duplicate_row = False
            if label in table:
                duplicate_row = True
            else:
                try:
                    if self.anonymous:
                        anonymous_row_key = "<TableRow {}: {}>".format(idx, label)
                        setattr(table, anonymous_row_key, table_row)
                    else:
                        setattr(table, label, table_row)
                except PageElementValueException:
                    # We'll get a value exception for setting an existing label if it's there already
                    duplicate_row = True
            if duplicate_row:
                msg = "Encountered non-unique row label: {}".format(label)
                instance.log.error(msg)
                raise PageElementStateException(msg)
            else:
                msg = "TableRow {}: {}".format(idx, label)
                instance.log.debug(msg)
        return table

    @staticmethod
    def find_table_elements(
        ctx, el_locator, *, scroller_locator=None, scroll_right=False, max_scroll_attempts=10
    ):
        if scroller_locator is None:
            try:
                ctx.wait.until.presence_of_all_elements_located(el_locator, timeout=ctx.timeout)
            except TimeoutException:
                ctx.log.warning("Failed to find table elements, assuming empty table")
                els = []
            else:
                els = ctx.find_elements(el_locator)
        else:
            # TODO: scroller handling may not be needed anymore?
            try:
                scroller = ctx.wait.until.element_to_be_clickable(
                    scroller_locator, timeout=ctx.timeout
                )
            except TimeoutException:
                raise PageElementStateException(
                    "Failed to locate scroller element: {}".format(scroller_locator)
                )
            scroller.click()
            ActionChains(ctx).send_keys(Keys.HOME).perform()
            attempt = 0
            ctx.log.debug("Finding table elements associated with locator: {}".format(el_locator))
            while attempt < max_scroll_attempts:
                ctx.log.debug("Attempt {}/{}".format(attempt, max_scroll_attempts))
                els = ctx.find_elements(el_locator)
                if len(els) > 0:
                    break
                actions = ActionChains(ctx)
                if scroll_right:
                    actions.send_keys(Keys.RIGHT)
                else:
                    actions.send_keys(Keys.DOWN)
                actions.perform()
                attempt += 1
            else:
                msg = "Failed to scroll element into view in {} attempts".format(
                    max_scroll_attempts
                )
                raise PageElementStateException(msg)
        return els


class TabPager(PageElement):
    """
    Describes an element that pages between different tabs (usually by number).

    E.g. a selection of buttons like "[Previous] [1] [2] [...] [10] [Next]"
    Jump to page 8 by assignment: self.el.<my_tabpager> = 8
    Get will return the current page: self.el.<my_tabpager> (returns "8")

    Alternatively, you can explicitly click the "previous" or "next" buttons by assigning "previous" or "next" respectively.
    E.g. self.el.<my_tabpager> = 'previous'

    If "page_group_xpath" is provided, the pager will jump to a specified tab if it finds it in the group, when prompted.
    Otherwise, it will jump to the closest parsed tab in the group to target tab before reiterating.
    If there is no closest, it will use the previous and next buttons.

    If "page_xpath_<key>" is provided, the pager will jump to the specified tab when prompted.
    Will throw an exception if it cannot be found.

    Tags:
        active_xpath:           Path to the element indicating the current tab
        prev_xpath:             Path to the "previous tab" button
        next_xpath:             Path to the "next tab" button
    Optional Tags:
        prev_disabled_xpath:    Path to the element indicating "previous tab" button is disabled
        next_disabled_xpath:    Path to the element indicating "next tab" button is disabled
        page_group_xpath:       Group locator for jumping to specified dynamic tabs (must have integer labels)
        page_xpath_<key>:       Path to a specific tab button
        tab_wait:               Time to wait between tab button clicks, in seconds (default: 2)
    """

    key = "pager"

    def __init__(self, **kwargs):
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))
        self.active_locator = None
        self.prev_locator = None
        self.prev_disabled_locator = None
        self.next_locator = None
        self.next_disabled_locator = None
        self.page_group_locator = None
        self.page_locators = {}
        self.tab_wait = 2
        self._last_obj_ctx = None
        for key, val in kwargs.items():
            locator = (By.XPATH, val)
            if key == "active_xpath":
                self.active_locator = locator
            elif key == "prev_xpath":
                self.prev_locator = locator
            elif key == "prev_disabled_xpath":
                self.prev_disabled_locator = locator
            elif key == "next_xpath":
                self.next_locator = locator
            elif key == "next_disabled_xpath":
                self.next_disabled_locator = locator
            elif key == "page_group_xpath":
                self.page_group_locator = locator
            elif key.startswith("page_xpath_"):
                prefix_len = len("page_xpath_")
                page_label = key[prefix_len:]
                if not (len(page_label) > 0 and page_label not in self.page_locators):
                    raise PageElementYamlException(
                        "Invalid page xpath element in TabPager: {}".format(key)
                    )
                self.page_locators[page_label] = locator
            elif key == "tab_wait":
                self.tab_wait = float(val)
            else:
                msg = 'Unknown tab pager option: "{}".format(key)'
                raise PageElementYamlException(msg)
        if not self.active_locator:
            raise PageElementYamlException("Active xpath is required for tab pagers")
        if not self.prev_locator:
            raise PageElementYamlException("Prev xpath is required for tab pagers")
        if not self.next_locator:
            raise PageElementYamlException("Next xpath is required for tab pagers")

    def __set__(self, instance, value):
        self._last_obj_ctx = instance
        instance.log.debug('Setting tab pager to value "{}"'.format(value))
        if value in self.page_locators:
            locator = self.page_locators["value"]
            instance.log.debug("Tab pager has fixed locator defined")
            element = instance.wait.until.element_to_be_clickable(
                locator, timeout=instance.timeout
            )
            self.scroll_into_view(element)
            element.click()
            return
        elif value in ["previous", "next"]:
            prevtabval = instance.wait.until.presence_of_element_located(
                self.active_locator, timeout=instance.timeout
            ).text
            if value == "previous":
                instance.log.debug('Tab pager clicking "previous" button')
                target_button = self.prev_button
            else:
                instance.log.debug('Tab pager clicking "next" button')
                target_button = self.next_button
            target_button.click()
            time.sleep(self.tab_wait)
            newtabval = instance.wait.until.presence_of_element_located(
                self.active_locator, timeout=instance.timeout
            ).text
            if newtabval == prevtabval:
                msg = "Tab did not change despite clicking button!  (Tab state: {})".format(
                    newtabval
                )
                instance.log.warning(msg)
                raise PageElementStateException(msg)
            return
        try:
            tgtintval = int(value)
        except ValueError:
            msg = (
                'Non-integer tab assignments require specifying the "page_xpath_<key>" YAML field'
            )
            raise PageElementYamlException(msg)
        lastintval = None
        while True:
            try:
                element = instance.wait.until.presence_of_element_located(
                    self.active_locator, timeout=instance.timeout
                )
                curintval = int(element.text)
            except ValueError:
                msg = "Integer tab assignment requires all tabs to be integer"
                raise PageElementValueException(msg)
            if curintval == tgtintval:
                instance.log.debug('Tab pager is in target state: "{}"'.format(tgtintval))
                return
            if curintval == lastintval:
                instance.log.warning("No tab change occurred!  Breaking early")
                return
            target_button = None
            if self.page_group_locator:
                page_tab_elements = instance.wait.until.presence_of_all_elements_located(
                    self.page_group_locator, timeout=instance.timeout
                )
                page_tab_val_map = []
                for element in page_tab_elements:
                    try:
                        page_tab_intval = int(element.text)
                    except ValueError:
                        msg = 'All text values of "page_group_locator" elements must be integers'
                        raise PageElementValueException(msg)
                    val_offset = abs(tgtintval - page_tab_intval)
                    page_tab_val_map.append((val_offset, element))
                instance.log.debug(
                    'Tab pager jumping to page valued "{}" (current: "{}"; target: "{}")'.format(
                        tgtintval, curintval, value
                    )
                )
                target_button = sorted(page_tab_val_map, key=lambda x: x[0])[0][1]
                self.scroll_into_view(target_button)
            elif curintval > tgtintval:
                instance.log.debug(
                    'Tab pager clicking "previous" button (current: "{}"; target: "{}")'.format(
                        curintval, value
                    )
                )
                target_button = self.prev_button
            else:
                instance.log.debug(
                    'Tab pager clicking "next" button (current: "{}"; target: "{}")'.format(
                        curintval, value
                    )
                )
                target_button = self.next_button
            lastintval = curintval
            target_button.click()
            time.sleep(self.tab_wait)

    def __get__(self, instance, owner):
        self._last_obj_ctx = instance
        return instance.wait.until.presence_of_element_located(
            self.active_locator, timeout=instance.timeout
        ).text

    @property
    def prev_button(self):
        obj = self._last_obj_ctx
        if self.prev_disabled_locator:
            try:
                obj.find_element(self.prev_disabled_locator)
                msg = '"Previous" button is disabled.'
                raise PageElementStateException(msg)
            except NoSuchElementException:
                obj.log.debug('Failed to locate "prev_disabled_locator"')
        target_button = obj.wait.until.element_to_be_clickable(
            self.prev_locator, timeout=obj.timeout
        )
        self.scroll_into_view(target_button)
        return target_button

    @property
    def next_button(self):
        obj = self._last_obj_ctx
        if self.next_disabled_locator:
            try:
                obj.find_element(self.next_disabled_locator)
                msg = '"Next" button is disabled.'
                raise PageElementStateException(msg)
            except NoSuchElementException:
                obj.log.debug('Failed to locate "next_disabled_locator"')
        target_button = obj.wait.until.element_to_be_clickable(
            self.next_locator, timeout=obj.timeout
        )
        self.scroll_into_view(target_button)
        return target_button


class TextBox(PageElement):
    """
    Describes a simple textbox.

    Tag:
        xpath:      Path to the textbox element
    Optional Tag:
        hidden:     Whether this textbox is hidden (e.g. for file input textboxes)
    """

    key = "textbox"

    def __init__(self, **kwargs):
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))
        self.hidden = False
        for key, val in kwargs.items():
            if key == "hidden":
                self.hidden = True
            else:
                msg = 'Unknown textbox option "{}"'.format(key)
                raise PageElementYamlException(msg)

    def __set__(self, instance, value):
        try:
            if self.hidden:
                textbox = self.wait_until_present(timeout=instance.timeout)
            else:
                textbox = self.wait_until_clickable(timeout=instance.timeout)
            existing_text = self.value
            if len(existing_text) > 0:
                instance.log.debug('Clearing existing value "%s"', existing_text)
                try:
                    # Textfields with 'value' don't like clear(), so we'll send backspaces instead
                    textbox.send_keys(Keys.END)
                    textbox.send_keys(*[Keys.BACKSPACE] * len(existing_text))
                except Exception:
                    # TODO: don't catch generic exception
                    # Just use clear() otherwise
                    textbox.clear()
            if len(str(value)) > 0:
                textbox.send_keys(str(value))
            instance.log.debug('Set textbox "%s" to value "%s"', self.el_name, value)
        except (ElementNotInteractableException, TimeoutException):
            instance.log.warning('Encountered error while setting textbox "%s"', self.el_name)
            instance.log.warning("Retrying with ActionChains")
            textbox = self.wait_until_present(timeout=instance.timeout)
            existing_text = self.value
            if len(existing_text) > 0:
                instance.log.debug('Clearing existing value "%s"', existing_text)
                ActionChains(instance).move_to_element(textbox).click().pause(1).send_keys(
                    Keys.END
                ).send_keys(*[Keys.BACKSPACE] * len(existing_text)).perform()
            ActionChains(instance).move_to_element(textbox).click().pause(1).send_keys(
                value
            ).perform()
            instance.log.debug('Set textbox "%s" to value "%s"', self.el_name, value)

    def __get__(self, instance, owner):
        if self.hidden:
            self.wait_until_present(timeout=instance.timeout)
        else:
            self.wait_until_clickable(timeout=instance.timeout)
        return self.value


class ToggledElement(PageElement):
    """
    Describes an element which changes state on click (like a checkbox), but doesn't record or maintain that state.

    Use is like a checkbox but requires either a positive or negative element to detect the element's state.
    Corresponding xpath keys are 'negative_element_xpath' and 'positive_element_xpath'.

    Tags:
        xpath:                  path to the element to click on
    Required 1 of the Following Tags:
        negative_element_xpath: path to the negative element to read as the element state
        positive_element_xpath: path to the positive element to read as the element state
    Optional Tag:
        alt_toggle_xpath:       path to the element to click on for the assignment to False case (if different)
    """

    key = "toggled_element"

    def __init__(self, **kwargs):
        super().__init__(**PageElement.pop_locator_kwargs(kwargs))
        self.alt_toggle = None
        self.check_loc = None
        self.check_type = None
        for key, val in kwargs.items():
            if key == "alt_toggle_xpath":
                self.alt_toggle = (By.XPATH, val)
            elif key == "negative_element_xpath":
                if self.check_type is not None:
                    raise PageElementYamlException(
                        "ToggledElement takes exactly one check condition"
                    )
                self.check_loc = (By.XPATH, val)
                self.check_type = "negative"
            elif key == "positive_element_xpath":
                if self.check_type is not None:
                    raise PageElementYamlException(
                        "ToggledElement takes exactly one check condition"
                    )
                self.check_loc = (By.XPATH, val)
                self.check_type = "positive"
            else:
                msg = 'Unknown toggled_element option "{}"'.format(key)
                raise PageElementYamlException(msg)
        if self.check_loc is None:
            raise PageElementYamlException("ToggledElement must supply a check condition")

    def __get__(self, instance, owner):
        return self._get_toggled_state(instance)

    def __set__(self, instance, value):
        state = self._get_toggled_state(instance)
        if state != value:
            instance.log.debug("Toggling toggleable element")
            if self.alt_toggle and not value:
                locator = self.alt_toggle
            else:
                locator = self.locator
            element = instance.wait.until.element_to_be_clickable(
                locator, timeout=instance.timeout
            )
            self.scroll_into_view(element)
            element.click()

    def _get_toggled_state(self, instance):
        try:
            visible = instance.find_element(self.check_loc).is_displayed()
            if self.check_type == "positive":
                return True if visible else False
            else:
                return False if visible else True
        except NoSuchElementException:
            return False if self.check_type == "positive" else True
