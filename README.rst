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
>>> for item in snapshot[:3]:
...     print(item)
<Item (date=2019-06-11, title='ABCDE - Melbourne Office', detail=('10:30 - 18:06', None, 'XYZ', 'Assistant'))>
<Item (date=2019-06-12, title='ABCDE - Melbourne Office', detail=('10:30 - 18:06', None, 'XYZ', 'Assistant'))>
<Item (date=2019-06-13, title='ABCDE - Melbourne Office', detail=('10:30 - 18:06', None, 'XYZ', 'Assistant'))>

..  _Allocate Software: https://www.allocatesoftware.com


Features
--------

*   Roster data includes server-side retrieval timestamps.
*   Sessions automatically log out after use (when used in a ``with`` block).
*   Meaningful Python exceptions are raised when problems arise.
*   Requests & responses to/from RosterOn
    can optionally be logged to files for debugging.


Installation
------------

Install this module from PyPI_ using pip_::

    pip install rosteron


..  _PyPI: https://pypi.org/project/rosteron
..  _pip: https://pip.pypa.io/


Support
-------

Bug reports, feature requests, and questions are welcome
via the issue tracker.

:Issue tracker: https://github.com/Lx/python-rosteron/issues


Contribute
----------


Sample responses from other RosterOn installations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Roster output is minimally structured
on the assumption that each RosterOn instance formats its data differently
(the author has only seen data from one RosterOn Mobile instance).

Roster response samples from other RosterOn Mobile instances
would be very gratefully received,
as these may demonstrate uniformity across all instances,
which would allow future releases of this module to provide more structured output.


Source code
^^^^^^^^^^^

Pull requests are gratefully received and considered.

:GitHub repository: https://github.com/Lx/python-rosteron


License
-------

This project is licensed under the `MIT License`_.

..  _MIT License: https://opensource.org/licenses/MIT
