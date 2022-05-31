# coding: utf-8
"""
Created on 2022-05-27
@author: Eugeny Kurkovich
"""

"""Common exceptions
"""


class Error(Exception):
    """A base class for Fatmouse exceptions"""

    def __init__(self, *args, **data):
        super(Error, self).__init__(*args)
        if hasattr(self, "message_fmt"):
            self.message = getattr(self, "message_fmt").format(*args, self=self)
        self.__dict__.update(data)

    def __str__(self):
        if getattr(self, "message", None):
            return "{}".format(self.message)
        else:
            return super(Error, self).__str__()


class TimeoutError(Error):  # pylint: disable=redefined-builtin
    # XXX: Pick new name for TimeoutError
    """When operation/function/task/workflow has been timed out."""


class NotAuthorizedError(Error):
    """When operation is not authorized for given context."""


class NotFoundError(Error):
    """Some thing (e.g resource, object, utility, file) was not found."""

    @classmethod
    def for_command(cls, command):
        return NotFoundError(
            ("{0!r} was not found. " "Please make sure that {0!r} is installed and available in $PATH.").format(command)
        )
