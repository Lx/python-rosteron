class RosterOnError(Exception):
    """
    :exc:`RosterOnError` exceptions are never raised directly.

    This exception class exists solely as a base class for all other RosterOn-related exception classes,
    to enable "catch-all" error-handling
    when the specifics of the failure (beyond the fact that it is RosterOn-related)
    are unimportant::

        try:
            ...
        except RosterOnError:
            print('There was a RosterOn problem; continuing')
    """


class BadResponseError(RosterOnError):
    """
    :exc:`BadResponseError` exceptions are raised
    when the RosterOn server returns a response
    that doesn't satisfy the needs of the current operation.

    This could happen when an incorrect :class:`~rosteron.Session` URL is used,
    when the RosterOn server is down,
    when a login error other than "bad username/password" occurs,
    or when logout occurs at an unexpected time.

    The exception message includs the type of output that was expected
    (``login``, ``home``, ``roster``, or ``logout``).

    >>> from rosteron import exceptions
    >>> raise exceptions.BadResponseError('login')
    Traceback (most recent call last):
      File "<input>", line 1, in <module>
    rosteron.exceptions.BadResponseError: RosterOn returned an unexpected response for an operation expecting 'login'
    """

    def __init__(self, purpose: str):
        super().__init__('RosterOn returned an unexpected response for an operation expecting {!r}'.format(purpose))


class BadCredentialsError(RosterOnError):
    """
    :exc:`BadCredentialsError` exceptions are raised
    when RosterOn rejects the supplied username & password
    during a login operation.

    The exception message includes the supplied username.

    >>> from rosteron import exceptions
    >>> raise exceptions.BadCredentialsError('joe.bloggs')
    Traceback (most recent call last):
      File "<input>", line 1, in <module>
    rosteron.exceptions.BadCredentialsError: RosterOn rejected the login credentials for username 'joe.bloggs'
    """

    def __init__(self, username: str):
        super().__init__('RosterOn rejected the login credentials for username {!r}'.format(username))


class NotLoggedInError(RosterOnError):
    """
    :exc:`NotLoggedInError` exceptions are raised
    when :meth:`~rosteron.Session.get_roster` is called
    on a :class:`~rosteron.Session` where a user has not yet successfully logged in.

    >>> from rosteron import exceptions
    >>> raise exceptions.NotLoggedInError
    Traceback (most recent call last):
      File "<input>", line 1, in <module>
    rosteron.exceptions.NotLoggedInError: a RosterOn user must successfully log in before a roster can be retrieved
    """

    def __init__(self):
        super().__init__('a RosterOn user must successfully log in before a roster can be retrieved')
