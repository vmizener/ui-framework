from selenium.common.exceptions import TimeoutException


class SolUiLibraryStateException(Exception):
    pass


class SolUiPageLoadException(Exception):
    pass


class SolUiNameError(Exception):
    pass


class SolUiTimeoutException(TimeoutException):
    pass
