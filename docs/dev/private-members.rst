Private Methods & Classes
=========================

Knowledge of the following methods & classes
(which are not part of the public ``rosteron`` module API)
is only of benefit if further developing the ``rosteron`` module.


Private :class:`Session` Methods
--------------------------------


``_browse`` Method
^^^^^^^^^^^^^^^^^^

..  automethod:: rosteron.Session._browse


``__exit__`` Method
^^^^^^^^^^^^^^^^^^^

..  automethod:: rosteron.Session.__exit__


Private ``_Response`` Class
---------------------------

..  autoclass:: rosteron._Response(time: datetime.datetime, id: str, content: bs4.Tag)


Private ``_LogEntry`` Class
---------------------------

..  autoclass:: rosteron._LogEntry(time: datetime.datetime, response: requests.Response, purpose: str)
