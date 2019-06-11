"""
``rosteron``: Read-only RosterOn Mobile roster access
=====================================================

The ``rosteron`` module allows read-only access
to rostering information in instances of RosterOn Mobile,
a workforce management product from `Allocate Software`_.

>>> import rosteron
>>> with rosteron.Session('https://rosteron.xyz.com.au/RosterOnProd/Mobile') as session:
...     session.log_in('joe.bloggs', 'abc123')
...     snapshot = session.get_roster()
>>> print(snapshot)
<Snapshot (time=2019-06-10T08:03:12+00:00, len=19)>
>>> for item in snapshot[:3]: print(item)
<Item (date=2019-06-11, title='ABCDE - Melbourne Office', detail=('10:30 - 18:06', None, 'XYZ', 'Assistant'))>
<Item (date=2019-06-12, title='ABCDE - Melbourne Office', detail=('10:30 - 18:06', None, 'XYZ', 'Assistant'))>
<Item (date=2019-06-13, title='ABCDE - Melbourne Office', detail=('10:30 - 18:06', None, 'XYZ', 'Assistant'))>

Roster output is minimally structured
on the assumption that each RosterOn instance formats its data differently
(the author has only seen data from one RosterOn Mobile instance).

Roster response samples from other RosterOn Mobile instances
would be very gratefully received,
as these may demonstrate uniformity across all instances,
which would allow future releases of this module to provide more structured output.

.. _Allocate Software: https://www.allocatesoftware.com
"""
from contextlib import AbstractContextManager
from datetime import datetime, date as date_type, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Sequence, Optional, List

import attr  # from attrs
import bs4  # from beautifulsoup4
import mechanicalsoup
import requests
from requests import RequestException

from . import exceptions


@attr.s(frozen=True)
class Item:
    # noinspection PyUnresolvedReferences
    """
    An :class:`Item` object represents one item on the roster.

    :class:`Item` objects aren't returned directly;
    they are instead returned within a :class:`Snapshot` object.

    Data in an :class:`Item` is minimally structured
    on the assumption that each RosterOn instance formats its data differently
    (the author has only seen data from one RosterOn Mobile instance).
    Future releases of this module can provide more structured output
    if samples are provided from other RosterOn Mobile instances.

    :param date:
        a :class:`date <datetime.date>` object.

    :param title:
        the text from the title above the roster item,
        minus the date and following separator.

    :param detail:
        a :class:`tuple` of :class:`str`/``None`` values,
        where each value is either:

        * a string extracted from a ``<p>`` element in the roster item;
          or
        * ``None`` where an empty ``<p>`` element is encountered.
    """
    date: date_type = attr.ib()
    title: str = attr.ib()
    detail: Sequence[Optional[str]] = attr.ib(converter=tuple)

    def __str__(self):
        return '<Item (date={}, title={}, detail={})>'.format(
            self.date.isoformat(),
            repr(self.title),
            repr(self.detail),
        )


@attr.s(frozen=True)
class Snapshot:
    # noinspection PyUnresolvedReferences
    """
    A :class:`Snapshot` object represents the state of a RosterOn user's roster
    at a specific point in time.

    :class:`Snapshot` objects are returned directly by the :meth:`Session.get_roster` method,
    are *subscriptable*,
    are *iterable*,
    and have a *length* corresponding to the number of contained :class:`Items <Item>`:

    >>> snapshot[0] == snapshot.items[0]
    True
    >>> [item for item in snapshot][0] == snapshot.items[0]
    True
    >>> len(snapshot) == len(snapshot.items)
    True

    :param time:
        a :class:`datetime <datetime.datetime>` object
        holding the server's timestamp at which the roster was retrieved.

    :param items:
        a :class:`tuple` of :class:`Item` objects comprising the roster.
    """
    time: datetime = attr.ib()
    items: Sequence[Item] = attr.ib(converter=tuple)

    def __str__(self):
        return '<Snapshot (time={}, len={})>'.format(
            self.time.isoformat(),
            len(self.items),
        )

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def __iter__(self):
        return iter(self.items)


@attr.s(frozen=True)
class _Response:
    # noinspection PyUnresolvedReferences
    """
    A semi-evaluated RosterOn response,
    returned by the :meth:`Session._browse` method.

    Every interesting response from RosterOn Mobile
    conveniently holds its interesting content in a structure like this::

        ...
        <div data-role="page" id="account-login">
            ...
            <div data-role="content">
                <!-- content of interest within -->
            </div>
        </div>
        ...

    The ``id`` attribute can be used
    to very confidently (and cheaply) determine the intent of the page.
    The content itself should only be further processed if that ID is as expected.

    :param time:
        ideally the time as returned by the server in the response header;
        failing that, the client time when the request was started.

    :param id:
        the page ID as specified by the ``id`` attribute
        in the ``<div data-role="page">`` element.

    :param content:
        the ``<div data-role="content">`` element as a :any:`bs4.Tag <bs4:tag>` object.
    """
    time: datetime = attr.ib()
    id: str = attr.ib()
    content: bs4.Tag = attr.ib()


@attr.s(frozen=True)
class _LogEntry:
    # noinspection PyUnresolvedReferences
    """
    A saved, timestamped RosterOn request/response pair
    for potential later logging to file.

    These are constructed in :meth:`Session._browse`,
    appended to the :obj:`Session._log` :class:`list`,
    and emitted on request by :meth:`Session.save_logs` as files.

    :param time:
        the client time when the request was started.

    :param response:
        the final returned :class:`requests.Response` object,
        which holds its corresponding request in its :attr:`~requests.Response.request` attribute
        and intermediate responses (if any) in its :attr:`~requests.Response.history` attribute.

    :param purpose:
        the type of output that was expected by this operation
        (``login``, ``home``, ``roster``, or ``logout``).
        Used in the filename.
    """
    time: datetime = attr.ib()
    response: requests.Response = attr.ib()
    purpose: str = attr.ib()


@attr.s(frozen=True)
class Session(AbstractContextManager):
    # noinspection PyUnresolvedReferences
    """
    A :class:`Session` object represents a connection to a RosterOn server,
    managing logging in, roster :class:`Snapshot` retrieval, logging out,
    and optional file-based logging of RosterOn HTTP requests & responses.

    :class:`Session` objects are `context managers`_,
    enabling automatic session log-out if used in a ``with`` block::

        with Session(...) as session:
            session.log_in(...)
            snapshot = session.get_roster()

        # session will always be logged out by this point

    ..  _context managers:
        https://docs.python.org/3/reference/datamodel.html#with-statement-context-managers

    :param url:
        the base URL of the **Mobile** version of the RosterOn instance,
        e.g. ``https://rosteron.example.com.au/RosterOnProd/Mobile``.
        The correct URL can be obtained for a RosterOn Mobile instance
        by visiting its "Log In" page in a browser
        and copying the portion of the URL prior to ``/Account/Login``.

    :param browser:
        if specified,
        a custom :class:`mechanicalsoup.StatefulBrowser` instance.
        Not required in normal usage;
        primarily intended for testing & diagnostic purposes.
    """
    url: str = attr.ib()
    browser: mechanicalsoup.StatefulBrowser = attr.ib(factory=mechanicalsoup.StatefulBrowser)
    _log: List[_LogEntry] = attr.ib(init=False, factory=list)

    @property
    def is_logged_in(self) -> bool:
        """
        Whether or not a user is logged in to RosterOn.

        :rtype:
            :class:`bool`
        """
        return '.ASPXAUTH' in self.browser.get_cookiejar()

    def log_in(self, username: str, password: str):
        """
        Log in to RosterOn with the specified user credentials.

        :param username:
            the RosterOn user whose shifts are to be retrieved.

        :param password:
            the relevant RosterOn user's password.

        :raise BadCredentialsError:
            if the RosterOn server doesn't accept the provided credentials.

        :raise BadResponseError:
            if the RosterOn server returns an unexpected response.

        :return:
            this :class:`Session` object,
            such that a :meth:`log_in` call can be used in a ``with`` block if desired::

                with session.log_in(...):
                    snapshot = session.get_roster()

                # session will always be logged out by this point
        """
        self._browse('Account/Login', 'login')
        form = self.browser.select_form()
        form['UserName'], form['Password'] = username, password
        response = self._browse(None, 'home')
        if response.id == 'home-index':
            return self
        else:
            error_div = response.content.find(class_='validation-summary-errors')
            errors = tuple(li.string.strip() for li in error_div.find_all('li'))
            if len(errors) == 1 and errors[0] == 'Logon failure: unknown user name or bad password.':
                raise exceptions.BadCredentialsError(username)
            else:
                raise exceptions.BadResponseError('home')

    def get_roster(self) -> Snapshot:
        """
        Retrieve a snapshot of the logged-in user's roster.

        :rtype:
            :class:`Snapshot`

        :raise NotLoggedInError:
            if no RosterOn user is logged in.

        :raise BadResponseError:
            if the RosterOn server returns an unexpected response.
        """
        response = self._browse('Roster/List?pageNo=1&row=1', 'roster')
        if response.id == 'account-login':
            raise exceptions.NotLoggedInError
        list_view = response.content.find(attrs={'data-role': 'listview'})
        shifts: List[Item] = []
        date: Optional[date_type] = None
        title: Optional[str] = None
        for li in list_view.find_all('li', recursive=False):
            if 'data-role' in li.attrs and li['data-role'] == 'list-divider':
                raw_date, _, title = li.string.partition(' - ')
                date = datetime.strptime(raw_date, '%a %d/%m/%Y').date()
            else:
                detail = tuple([p.string for p in li.find('table').find_all('p')])
                shifts.append(Item(date, title, detail))
        return Snapshot(response.time, shifts)

    def log_out(self) -> None:
        """
        If a user is logged in to RosterOn, log them out;
        otherwise, do nothing.

        This method is called automatically if the :class:`Session` is used in a ``with`` block::

            with Session(...) as session:
                session.log_in(...)
                snapshot = session.get_roster()

            # session will always be logged out by this point

        :raise BadResponseError:
            if a user is logged in
            **and** the RosterOn server returns an unexpected response while attempting to log out.
        """
        if self.is_logged_in:
            self._browse('Account/LogOff', 'logout')

    def save_logs(self, directory: str) -> None:
        """
        Log, to the specified directory,
        all RosterOn server requests & responses made over the life of the :class:`Session`.
        Intended only for diagnostic purposes.
        Login credentials are not logged.

        Each request/response will be saved to ``<yyyymmddThhmmss.microseconds>Z-<purpose>-<n>.txt``
        in the specified directory,
        where:

        * ``<yyyymmddThhmmss.microseconds>Z``
          is the date & time of the initial request in UTC;
        * ``<purpose>``
          is the type of output expected
          for the operation triggering the initial request
          (``login``, ``home``, ``roster``, or ``logout``);
          and
        * ``n``
          is ``0`` for the initial request/response pair in one operation,
          and a higher number for each subsequent request/response pair in that operation.

        The typical :class:`Session` usage of logging in, retrieving the roster, and logging out
        triggers requests & responses that would be logged as such::

            20190610T042837.160169Z-login-0.txt
            20190610T042838.576616Z-home-0.txt
            20190610T042838.576616Z-home-1.txt
            20190610T042838.934080Z-roster-0.txt
            20190610T042839.134057Z-logout-0.txt
            20190610T042839.134057Z-logout-1.txt

        Each file will contain the date & time of the request,
        the request method & URL (not login credentials),
        and the server response (including status and headers)::

            2019-06-10 04:28:37.160169+00:00
            GET https://rosteron.xyz.com.au/RosterOnProd/Mobile/Account/Login
            200 OK

            Date: Mon, 10 Jun 2019 04:28:38 GMT
            Content-Type: text/html; charset=utf-8

            <!DOCTYPE html>
            ...

        :param directory:
            The directory where the requests & responses will be logged,
            which is assumed to exist and have appropriate write permissions.
        """
        for entry in self._log:
            for index, response in enumerate([*entry.response.history, entry.response]):
                filename = '{}-{}-{}.txt'.format(
                    entry.time.strftime('%Y%m%dT%H%M%S.%fZ'),
                    entry.purpose,
                    index,
                )
                with (Path(directory) / filename).open('w') as file:
                    file.writelines([
                        str(entry.time),
                        '\n',
                        '{} {}\n'.format(response.request.method, response.request.url),
                        '{} {}\n'.format(response.status_code, response.reason),
                        '\n',
                        *('{}: {}\n'.format(key, value) for key, value in response.headers.items()),
                        '\n',
                        response.text,
                    ])

    def _browse(self, url_fragment: Optional[str], purpose: str) -> _Response:
        """
        Note the current client time,
        browse to the next page,
        log the response in case :meth:`save_logs` is called later,
        and attempt to build a corresponding :class:`_Response` object.

        :param url_fragment:
            if specified,
            the URL (minus the base :class:`Session` URL) that will be navigated to;
            if not specified,
            the current page's selected form will be submitted.

        :param purpose:
            the type of output expected by this navigation/submission
            (``login``, ``home``, ``roster``, or ``logout``).
            Used in :exc:`~exceptions.BadResponseError` messages and response logging.

        :rtype:
            :class:`_Response`

        :raise BadResponseError:
            if the response doesn't have the expected RosterOn page traits.
        """
        request_time = datetime.now(timezone.utc)
        try:
            if url_fragment:
                response = self.browser.open('/'.join([self.url, url_fragment]))
            else:
                response = self.browser.submit_selected()
        except RequestException as e:
            raise exceptions.BadResponseError(purpose) from e
        self._log.append(_LogEntry(request_time, response, purpose))
        if 'Date' in response.headers:
            dt = parsedate_to_datetime(response.headers['Date'])
        else:
            dt = request_time
        soup = self.browser.get_current_page()
        try:
            page_div = soup.find(attrs={'data-role': 'page'})
            page_id = page_div['id']
            content_div = page_div.find(attrs={'data-role': 'content'})
            return _Response(time=dt.astimezone(timezone.utc), id=page_id, content=content_div)
        except (AttributeError, TypeError):
            raise exceptions.BadResponseError(purpose)

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Ensure that the RosterOn user is logged out.
        Called at the end of any ``with`` block that uses this :class:`Session` object.

        The parameters describe the exception raised inside the ``with`` block, if any,
        and are not used.

        :return:
            ``False``,
            to indicate that any exception that occurred
            should propagate to the caller rather than be suppressed.
        """
        self.log_out()
        return False
