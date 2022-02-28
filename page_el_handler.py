from . import exceptions


class PageElementDescriptorHandler:
    """
    This object handles all page element descriptor objects.
    """

    def __init__(self, pageobj):
        """
        PageElementDescriptorHandlers are created per page
        """
        self.log = pageobj.log
        self.obj = PageElementObjectDelegator(self)
        self.__class__.pageobj = pageobj

    @property
    def pageobj(self):
        return self.__class__.pageobj

    @property
    def pagename(self):
        return self.pageobj.pagename

    @property
    def timeout(self):
        return self.pageobj.timeout

    @timeout.setter
    def timeout(self, value):
        self.pageobj.timeout = value

    def __getattr__(self, attr):
        """
        Delegate to the underlying webdriver if we cannot find the named page element.
        """
        return getattr(self.pageobj, attr)


class PageElementObjectDelegator:
    def __init__(self, el_handler):
        self._el_handler = el_handler

    def __getattr__(self, attr):
        try:
            return vars(type(self._el_handler))[attr]
        except KeyError as err:
            msg = 'No element named "{}" in group "{}"'.format(attr, self._el_handler.pagename)
            raise exceptions.SolUiNameError(msg) from err
