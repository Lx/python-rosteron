from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from mechanicalsoup import StatefulBrowser
from pytest import raises
from requests.cookies import create_cookie

from rosteron import Snapshot, Item, Session
from rosteron.exceptions import BadResponseError, BadCredentialsError, NotLoggedInError

HTML: Path = Path(__file__).parent / 'HTML'

TEST_URL: str = 'http://example.com/RosterOnProd/Mobile'


def _item(date):
    return Item(date=date, title='ABCDE - Melbourne Office', detail=['10:30 - 18:06', None, 'XYZ', 'Assistant'])


def test_item():
    date = datetime.today().date()
    item = _item(date)
    assert str(item) == '<Item (date={}, title={!r}, detail={!r})>'.format(
        date.isoformat(),
        item.title,
        tuple(item.detail),
    )


def test_snapshot():
    time = datetime.utcnow()
    items = [_item(time.date())]
    snapshot = Snapshot(time=time, items=items)
    assert str(snapshot) == '<Snapshot (time={}, len={})>'.format(time.isoformat(), len(snapshot))
    assert snapshot[0] == items[0]
    assert [item for item in snapshot][0] == items[0]


class TestSession:

    def test_is_logged_in(self, requests_mock):
        requests_mock.get(TEST_URL + '/Account/Login', text=(HTML / 'login.html').read_text())
        requests_mock.post(
            TEST_URL + '/Account/Login',
            cookies={'.ASPXAUTH': 'XXX'},
            text=(HTML / 'home.html').read_text(),
        )
        requests_mock.get(
            TEST_URL + '/Account/LogOff',
            cookies={'.ASPXAUTH': None},
            text=(HTML / 'login.html').read_text(),
        )
        browser = StatefulBrowser()
        session = Session(TEST_URL, browser)
        assert not session.is_logged_in
        session.log_in('joe.bloggs', 'abc123')

        # The ``requests-mock`` library currently doesn't mock cookies in sessions properly.
        # In the meantime, mock the cookie by directly setting it on the ``browser`` object.
        # https://github.com/jamielennox/requests-mock/issues/17
        browser.get_cookiejar().set_cookie(create_cookie(name='.ASPXAUTH', value='XXX'))

        assert session.is_logged_in
        session.log_out()

        # As above.
        browser.get_cookiejar().set_cookie(create_cookie(name='.ASPXAUTH', value=None))

        assert not session.is_logged_in

    def test_log_in_bad_first_page(self, requests_mock):
        requests_mock.get(TEST_URL + '/Account/Login', text=(HTML / 'unexpected.html').read_text())
        with raises(BadResponseError):
            Session(TEST_URL).log_in('joe.bloggs', 'abc123')

    def test_log_in_bad_creds(self, requests_mock):
        requests_mock.get(TEST_URL + '/Account/Login', text=(HTML / 'login.html').read_text())
        requests_mock.post(TEST_URL + '/Account/Login', text=(HTML / 'login-badcreds.html').read_text())
        with raises(BadCredentialsError):
            Session(TEST_URL).log_in('joe.bloggs', 'abc123')

    def test_log_in_server_error_after_login(self, requests_mock):
        requests_mock.get(TEST_URL + '/Account/Login', text=(HTML / 'login.html').read_text())
        requests_mock.post(TEST_URL + '/Account/Login', text=(HTML / 'unexpected.html').read_text())
        with raises(BadResponseError):
            Session(TEST_URL).log_in('joe.bloggs', 'abc123')

    def test_log_in_strange_error(self, requests_mock):
        requests_mock.get(TEST_URL + '/Account/Login', text=(HTML / 'login.html').read_text())
        requests_mock.post(TEST_URL + '/Account/Login', text=(HTML / 'login-baderror.html').read_text())
        with raises(BadResponseError):
            Session(TEST_URL).log_in('joe.bloggs', 'abc123')

    def test_get_roster(self, requests_mock):
        server_time_str = 'Mon, 10 Jun 2019 04:28:38 GMT'
        requests_mock.get(
            TEST_URL + '/Roster/List?pageNo=1&row=1',
            headers={'Date': server_time_str},
            text=(HTML / 'roster.html').read_text(),
        )
        snapshot = Session(TEST_URL).get_roster()
        assert isinstance(snapshot, Snapshot)
        assert snapshot.time == parsedate_to_datetime(server_time_str)

    def test_get_roster_not_logged_in(self, requests_mock):
        requests_mock.get(TEST_URL + '/Roster/List?pageNo=1&row=1', text=(HTML / 'login.html').read_text())
        with raises(NotLoggedInError):
            Session(TEST_URL).get_roster()

    # noinspection PyUnusedLocal
    # (unused requests_mock ensures no requests are made)
    def test_log_out_already_logged_out(self, requests_mock):
        session = Session(TEST_URL)
        assert not session.is_logged_in
        session.log_out()
        assert not session.is_logged_in

    def test_save_logs(self, requests_mock, tmp_path: Path):
        requests_mock.get(TEST_URL + '/Account/Login', text=(HTML / 'login.html').read_text())
        requests_mock.post(
            TEST_URL + '/Account/Login',
            cookies={'.ASPXAUTH': 'XXX'},
            text=(HTML / 'home.html').read_text(),
        )
        requests_mock.get(
            TEST_URL + '/Account/LogOff',
            cookies={'.ASPXAUTH': None},
            text=(HTML / 'login.html').read_text(),
        )
        browser = StatefulBrowser()
        session = Session(TEST_URL, browser)
        session.log_in('joe.bloggs', 'abc123')

        # The ``requests-mock`` library currently doesn't mock cookies in sessions properly.
        # In the meantime, mock the cookie by directly setting it on the ``browser`` object.
        # https://github.com/jamielennox/requests-mock/issues/17
        browser.get_cookiejar().set_cookie(create_cookie(name='.ASPXAUTH', value='XXX'))

        session.log_out()

        # As above.
        browser.get_cookiejar().set_cookie(create_cookie(name='.ASPXAUTH', value=None))

        session.save_logs(str(tmp_path))
        files = list(sorted(tmp_path.iterdir()))
        assert len(files) == 3
        assert files[0].name.endswith('Z-login-0.txt')
        assert files[1].name.endswith('Z-home-0.txt')
        assert files[2].name.endswith('Z-logout-0.txt')
        with files[0].open() as log:
            assert isinstance(datetime.fromisoformat(next(log).strip()), datetime)
            assert next(log).startswith('GET ' + TEST_URL)
            assert next(log).startswith('200 None')
            assert next(log) == '\n'
        assert files[0].read_text().endswith((HTML / 'login.html').read_text())

    def test_auto_logout(self, requests_mock):
        requests_mock.get(TEST_URL + '/Account/Login', text=(HTML / 'login.html').read_text())
        requests_mock.post(
            TEST_URL + '/Account/Login',
            cookies={'.ASPXAUTH': 'XXX'},
            text=(HTML / 'home.html').read_text(),
        )
        requests_mock.get(
            TEST_URL + '/Account/LogOff',
            cookies={'.ASPXAUTH': None},
            text=(HTML / 'login.html').read_text(),
        )
        browser = StatefulBrowser()
        session = Session(TEST_URL, browser)
        session.log_in('joe.bloggs', 'abc123')

        # The ``requests-mock`` library currently doesn't mock cookies in sessions properly.
        # In the meantime, mock the cookie by directly setting it on the ``browser`` object.
        # https://github.com/jamielennox/requests-mock/issues/17
        browser.get_cookiejar().set_cookie(create_cookie(name='.ASPXAUTH', value='XXX'))

        assert session.is_logged_in
        with session:
            pass

        # As above.
        browser.get_cookiejar().set_cookie(create_cookie(name='.ASPXAUTH', value=None))
        assert not session.is_logged_in

    def test_connection_error(self, requests_mock):
        requests_mock.get(TEST_URL + '/Roster/List?pageNo=1&row=1', exc=requests.exceptions.ConnectionError)
        with raises(BadResponseError):
            Session(TEST_URL).get_roster()

    def test_http_error(self, requests_mock):
        requests_mock.get(TEST_URL + '/Roster/List?pageNo=1&row=1', exc=requests.exceptions.HTTPError)
        with raises(BadResponseError):
            Session(TEST_URL).get_roster()
