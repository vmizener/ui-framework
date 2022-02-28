import inspect
import logging
import pathlib
import time

from urllib.parse import urljoin

from .globals import (
    LIB_PAGE_ELEMENT_CLASS_NAME,
    SELE_DEFAULT_PAGE_LOAD_DELAY,
    SELE_DEFAULT_PAGE_LOADER_TIMEOUT,
)
from .wait import Wait


class BasePage:
    LOAD_DELAY = SELE_DEFAULT_PAGE_LOAD_DELAY
    LOADERS = None
    URL = ""

    def __init__(self, services):
        # Set useful internal attributes
        fpath = pathlib.Path(inspect.getfile(self.__class__))
        pagename = fpath.stem
        self.log = logging.getLogger("ui-group-{}".format(pagename))
        self.log.setLevel(services.log.level)
        self.pagename = pagename
        self.services = services
        self.__class__.group_name = pagename
        self.wait = Wait(self.driver, services.timeout)
        self.url = urljoin(self.base_url, self.URL)

        # Initialize page element machinery
        if hasattr(self, LIB_PAGE_ELEMENT_CLASS_NAME):
            self._el = getattr(self, LIB_PAGE_ELEMENT_CLASS_NAME)(self)

    @property
    def base_url(self):
        return self.services.base_url

    @property
    def driver(self):
        return self.services.browser

    @property
    def el(self):
        try:
            return self._el
        except AttributeError:
            self.log.warning(f'Page "{self.pagename}" missing PageElement definition!')
            raise

    @property
    def timeout(self):
        return self.services.timeout

    @timeout.setter
    def timeout(self, value):
        self.services.timeout = value

    @property
    def generic(self):
        return self.services.generic

    @property
    def root_object(self):
        return self.find_element_by_xpath("/*")

    def __dir__(self):
        return sorted(super().__dir__() + dir(self.driver))

    def __getattr__(self, attr):
        """
        Check the webdriver for any properties not defined here.
        """
        if hasattr(self.driver, attr):
            return getattr(self.driver, attr)
        raise AttributeError("'{}' object has no attribute '{}'".format(type(self).__name__, attr))

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        return

    def open(self):
        """
        Extension to the built-in open method to provide options to account for loaders.
        """
        self.driver.get(self.url)
        if self.LOAD_DELAY is not None:
            self.log.debug(
                'Page context "{}" has load delay on spawn; waiting {}s'.format(
                    self.pagename, self.LOAD_DELAY
                )
            )
            time.sleep(self.LOAD_DELAY)
        if self.LOADERS is not None:
            self.log.debug(
                'Page context "{}" has loaders on spawn; waiting for loaders: {}'.format(
                    self.pagename, self.LOADERS
                )
            )
            for loader_el in self.LOADERS:
                title = 'loader "{}" for context "{}"'.format(loader_el, self.pagename)
                if self.el.build_augmented_element_key(loader_el, ctx=self.generic) in dir(
                    self.el
                ):
                    self.generic.wait_for_event(
                        tag=loader_el,
                        event_title=title,
                        delay=0,
                        timestep=2,
                        timeout=SELE_DEFAULT_PAGE_LOADER_TIMEOUT,
                    )
                else:
                    self.generic.wait_for_event(
                        tag=loader_el,
                        ctx=self,
                        event_title=title,
                        delay=0,
                        timestep=2,
                        timeout=SELE_DEFAULT_PAGE_LOADER_TIMEOUT,
                    )
