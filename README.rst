=========================================
National Rail Enquiries Darwin Webservice
=========================================

Introduction
------------

`nre-darwin-py` provides an abstraction layer for accessing National Rail Enquiries Darwin service via their LDB SOAP web service.

This module has the following goals:

* Allow developers to avoid the complexity of SOAP and the decisions involved in choosing a Python SOAP client
* Provide a more pythonic interface to station board and service details information
* Make useful documentation available through pydoc or through the `help` command in the python shell
* Facilitate the easy creation of departure board websites and webservices

Getting started
---------------

Firstly you need to register for Darwin access, you can do this via National Rail Enquires `developer site <http://www.nationalrail.co.uk/46391.aspx>`_.

Basic usage
-----------

Initiate a session::

    >>> import nredarwin.webservice
    >>> darwin_sesh = nredarwin.webservice.Session(wsdl="https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx", api_key="YOUR_KEY")

Retrieve the departure board for Manchester Piccadilly station::

    >>> board = darwin_sesh.get_station_board('MAN')
    >>> board.location_name
    'Manchester Piccadilly'
    >> board.train_services[0].destination_text
    'Rose Hill Marple'

Retrieve more detailed information regarding a particular service::

    >>> service_id = board.train_services[0].service_id
    >>> service = darwin_sesh.get_service_details(service_id)
    >>> [cp.location_name for cp in service.subsequent_calling_points]
    [Gorton, Fairfield, Guide Bridge, Hyde Central, Woodley, Romiley, Rose Hill Marple]

The provided example.py script shows a simple departure board implementation for your reference
