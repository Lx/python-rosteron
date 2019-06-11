Private Methods & Classes
=========================

Knowledge of the following methods & classes
(which are not part of the public ``rosteron`` module API)
is only of benefit if further developing the ``rosteron`` module.


Private :class:`~rosteron.Session` Methods
------------------------------------------


:meth:`~rosteron.Session._browse` Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

..  automethod:: rosteron.Session._browse


:meth:`~rosteron.Session.__exit__` Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

..  automethod:: rosteron.Session.__exit__


Private :class:`~rosteron._Response` Class
------------------------------------------

..  autoclass:: rosteron._Response(time: datetime.datetime, id: str, content: bs4.Tag)


Private :class:`~rosteron._LogEntry` Class
------------------------------------------

..  autoclass:: rosteron._LogEntry(time: datetime.datetime, response: requests.Response, purpose: str)
