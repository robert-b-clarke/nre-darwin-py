from suds.client import Client
from suds.sax.element import Element
from suds import WebFault
from functools import partial
import logging
import os

log = logging.getLogger(__name__)
#TODO - timeouts and error handling
DARWIN_WEBSERVICE_NAMESPACE = ('com','http://thalesgroup.com/RTTI/2010-11-01/ldb/commontypes')

class DarwinLdbSession(object):
    """
    A connection to the Darwin LDB web service
    """

    def __init__(self, wsdl=None, api_key=None, timeout=5):
        if not wsdl:
            wsdl = os.environ['DARWIN_WEBSERVICE_WSDL']
        if not api_key:
            api_key = os.environ['DARWIN_WEBSERVICE_API_KEY']
        self._soap_client = Client(wsdl)
        self._soap_client.set_options(timeout=timeout)
        #build soap headers
        token3 = Element('AccessToken', ns=DARWIN_WEBSERVICE_NAMESPACE)
        token_value = Element('TokenValue', ns=DARWIN_WEBSERVICE_NAMESPACE)
        token_value.setText(api_key)
        token3.append(token_value)
        self._soap_client.set_options(soapheaders=(token3))

    def _base_query(self):
        return self._soap_client.service['LDBServiceSoap']

    def get_station_board(self, crs, rows=10, include_departures=True, include_arrivals=False, destination_crs=None, origin_crs=None):
        """
        Query the darwin webservice to obtain a board for a particular station. Three letter CRS code is an expected parameter. By default only departures are included

        returns a StationBoard object
        """
        #Determine the darwn query we want to make
        if include_departures and include_arrivals:
            query_type = 'GetArrivalDepartureBoard'
        elif include_departures:
            query_type = 'GetDepartureBoard'
        elif include_arrivals:
            query_type = 'GetArrivalBoard'
        else:
            raise ValueError("get_station_board must have either include_departures or include_arrivals set to True")
        #build a query function
        q = partial(self._base_query()[query_type], crs=crs, numRows=rows)
        if destination_crs:
            if origin_crs:
                log.warn("Station board query can only filter on one of destination_crs and origin_crs, using only destination_crs")
            q = partial(q, filterCrs=destination_crs, filterType='to')
        elif origin_crs:
            q = partial(q, filterCrs=origin_crs, filterType='from')
        try:
            soap_response = q()
        except WebFault:
            raise WebServiceError
        return StationBoard(soap_response)

    
    def get_service_details(self, service_id):
        """
        Get the details of an individual service using a serviceId
        """
        try:
            soap_response = self._soap_client.service['LDBServiceSoap']['GetServiceDetails'](serviceID=service_id)
        except WebFault:
            raise WebServiceError
        return ServiceDetails(soap_response)

class SoapResponseBase(object):

    def __init__(self, soap_response):
        for dest_key, src_key in self.__class__.field_mapping:
            try:
                val = getattr(soap_response, src_key)
            except AttributeError:
                val = None
            setattr(self, '_' + dest_key, val)

        

class StationBoard(SoapResponseBase):
    """
    An abstract representation of a station departure board
    """

    field_mapping = [
        ('generated_at', 'generatedAt'),
        ('crs', 'crs'),
        ('location_name', 'locationName'),
    ]

    service_lists = [
        ('train_services', 'trainServices'),
        ('bus_services', 'busServices'),
        ('ferry_services', 'ferryServices')
    ]

    def __init__(self, soap_response, *args, **kwargs):
        super(StationBoard,self).__init__(soap_response, *args, **kwargs)
        #populate service lists - these are specific to station board objects, so not included in base class
        for dest_key, src_key in self.__class__.service_lists:
            try:
                service_rows = getattr(getattr(soap_response, src_key), 'service')
            except AttributeError:
                setattr(self, '_' + dest_key, [])
                continue

            setattr(self, '_' + dest_key, [ServiceItem(s) for s  in service_rows])
        #populate nrcc_messages
        if hasattr(soap_response, 'nrccMessages') and hasattr(soap_response.nrccMessages, 'message'):
            #TODO - would be nice to strip HTML from these, especially as it's not compliant with modern standards
            self._nrcc_messages = soap_response.nrccMessages.message
        else:
            self._nrcc_messages = []

    @property
    def generated_at(self):
        """
        The time at which the station board was generated. 
        """
        return self._generated_at

    @property
    def crs(self):
        """
        The CRS code of the location that the station board is for. 
        """
        return self._crs

    @property
    def location_name(self):
        """
        The name of the location that the station board is for.
        """
        return self._location_name

    @property
    def train_services(self):
        """
        A list of train services that appear on this board. Empty if there are none
        """
        return self._train_services

    @property
    def bus_services(self):
        """
        A list of bus services that appear on this board. Empty if there are none
        """
        return self._bus_services

    @property
    def ferry_services(self):
        """
        A list of ferry services that appear on this board. Empty if there are none
        """
        return self._ferry_services

    @property
    def nrcc_messages(self):
        """
        An optional list of textual messages that should be displayed with the station board. The message may include embedded and xml encoded HTML-like hyperlinks and paragraphs. The messages are typically used to display important disruption information that applies to the location that the station board was for.
        """
        return self._nrcc_messages

    def __str__(self):
        return "%s - %s" % (self.crs, self.location_name)

class ServiceDetailsBase(SoapResponseBase):
    #The generic stuff that both service details classes have
    field_mapping = [
        ('sta', 'sta'),
        ('eta', 'eta'),
        ('std', 'std'),
        ('etd', 'etd'),
        ('platform', 'platform'),
        ('operator_name', 'operator'),
        ('operator_code', 'operatorCode'),
    ]


    @property
    def scheduled_arrival(self):
        raise NotImplementedError()

    @property
    def estimated_arrival(self):
        raise NotImplementedError()
        
    @property
    def scheduled_departure(self):
        raise NotImplementedError()

    @property
    def estimated_departure(self):
        raise NotImplementedError()

    @property
    def sta(self):
        """
        An optional Scheduled Time of Arrival of the service at the station board location. Arrival times will only be available for Arrival and Arrival & Departure station boards but may also not be present at locations that are not scheduled to arrive at the location (e.g. the origin)

        This is a human readable string rather than a proper datetime object and may not be a time at all
        """
        return self._sta

    @property
    def eta(self):
        """
        An optional Estimated Time of Arrival of the service at the station board location. Arrival times will only be available for Arrival and Arrival & Departure station boards and only where an sta time is present.

        This is a human readable string rather than a proper datetime object and may not be a time at all
        """
        return self._eta

    @property
    def std(self):
        """
        An optional Scheduled Time of Departure of the service at the station board location. Departure times will only be available for Departure and Arrival & Departure station boards but may also not be present at locations that are not scheduled to depart at the location

        This is a human readable string rather than a proper datetime object and may not be a time at all
        """
        return self._std

    @property
    def etd(self):
        """
        An optional Estimated Time of Departure of the service at the station board location. Departure times will only be available for Departure and Arrival & Departure station boards and only where an std time is present. 

        This is a human readable string rather than a proper datetime object and may not be a time at all
        """
        return self._etd

    @property
    def platform(self):
        """
        An optional platform number for the service at this location
        """
        return self._platform

    @property
    def operator_name(self):
        """
        The name of the Train Operating Company that operates the service
        """
        return self._operator_name

    @property
    def operator_code(self):
        """
        The code of the Train Operating Company that operates the service
        """
        return self._operator_code

    #TODO -Adhoc alerts, datetime inflators - if possible

class ServiceItem(ServiceDetailsBase):
    """
    A single service from a bus, train or ferry departure/arrival board
    """

    field_mapping = ServiceDetailsBase.field_mapping + [
        ('is_circular_route', 'isCircularRoute'),
        ('service_id', 'serviceID'),
    ]
    
    def __init__(self, soap_data, *args, **kwargs):
        super(ServiceItem, self).__init__(soap_data, *args, **kwargs)

        #handle service location lists - these should be empty lists if there are no locations
        self._origins = [ServiceLocation(l) for l  in soap_data.origin.location] if hasattr(soap_data.origin, 'location') else []
        self._destinations = [ServiceLocation(l) for l  in soap_data.destination.location] if hasattr(soap_data.origin, 'location') else []

    @property
    def is_circular_route(self):
        """
        If this value is present and true then the service is operating on a circular route through the network and will call again at this location later on its journey
        """
        return self._is_circular_route

    @property
    def service_id(self):
        """
        The unique service identifier of this service relative to the station board on which it is displayed
        """
        return self._service_id

    @property
    def origins(self):
        """
        A list of ServiceLocation objects giving origins of this service. Note that a service may have more than one origin, if the service comprises of multiple trains that join at a previous location in the schedule.
        """
        return self._origins

    @property
    def destinations(self):
        """
        A list of ServiceLocation objects giving destinations of this service. Note that a service may have more than one destination, if the service comprises of multiple trains that divide at a subsequent location in the schedule
        """
        return self._destinations

    @property
    def destination_text(self):
        """
        Human readable string describing the destination(s) of this service
        """
        return self._location_formatter(self.destinations)

    @property
    def origin_text(self):
        """
        Human readable string describing the origin(s) of this service
        """
        return self._location_formatter(self.origins)

    def _location_formatter(self, location_list):
        return ", ".join([str(l) for l in location_list])

    def __str__(self):
        return "Service %s" % (self.service_id)


class ServiceLocation(SoapResponseBase):
    """
    A single location from a service origin/destination list
    """
    field_mapping = [
        ('location_name', 'locationName'),
        ('crs', 'crs'),
        ('via', 'via'),
        ('future_change_to', 'futureChangeTo')
    ]
    
    @property
    def location_name(self):
        """
        The name of the location.
        """
        return self._location_name

    @property
    def crs(self):
        """
        The CRS code of this location. A CRS code of ??? indicates an error situation where no crs code is known for this location.
        """
        return self._crs

    @property
    def via(self):
        """
        An optional via text that should be displayed after the location, to indicate further information about an ambiguous route. Note that vias are only present for ServiceLocation objects that appear in destination lists
        """
        return self._via

    @property
    def future_change_to(self):
        """
        A text string contianing service type (Bus/Ferry/Train) to which will be changed in the future.
        """
        return self._future_change_to
    
    def __str__(self):
        if self.via:
            return "%s %s" % (self.location_name, self.via)
        else:
            return self.location_name

class ServiceDetails(ServiceDetailsBase):
    """
    In depth details of a single service
    """

    field_mapping = ServiceDetailsBase.field_mapping + [
        ('is_cancelled', 'isCancelled'),
        ('disruption_reason', 'disruptionReason'),
        ('overdue_message', 'overdueMessage'),
        ('ata', 'ata'),
        ('atd', 'atd'),
    ]
   
    def __init__(self, soap_data, *args, **kwargs):
        super(ServiceDetails, self).__init__(soap_data, *args, **kwargs)
        #print soap_data.subsequentCallingPoints.callingPointList[0]
        self._previous_calling_points = self._calling_point_list(soap_data, 'previousCallingPoints')
        self._subsequent_calling_points = self._calling_point_list(soap_data, 'subsequentCallingPoints')

    def _calling_point_list(self, soap_data, src_key):
        try:
            calling_points = getattr(getattr(soap_data, src_key), 'callingPointList')
        except AttributeError:
            return []
        #print calling_points[0].callingPoint[0]
        points = []
        for sublist in calling_points:
            for point in sublist.callingPoint:
                points.append(CallingPoint(point))
        return points

    @property
    def is_cancelled(self):
        """
        Indicates that the service is cancelled at this location.
        """
        return self._is_cancelled

    @property
    def disruption_reason(self):
        """
        A disruption reason for this service. If the service is cancelled, this will be a cancellation reason. If the service is running late at this location, this will be a late-running reason.
        """
        return self._disruption_reason

    @property
    def overdue_message(self):
        """
        If an expected movement report has been missed, this will contain a message describing the missed movement.
        """
        return self._overdue_message

    @property
    def ata(self):
        """
        The actual time of arrival. Will only be present if sta is also present and eta is not present.
        """
        return self._ata

    @property
    def atd(self):
        """
        The actual time of departure. Will only be present if std is also present and etd is not present.
        """
        return self._atd

    @property
    def previous_calling_points(self):
        """
        A list of CallingPoint objects representing the previous calling points in the journey. A separate calling point list will be present for each origin of the service, relative to the current location
        """
        return self._previous_calling_points

    @property
    def subsequent_calling_points(self):
        """
        A list of CallingPoint objects representing the subsequent calling points in the journey. A separate calling point list will be present for each destination of the service, relative to the current location. 
        """
        return self._subsequent_calling_points

class CallingPoint(SoapResponseBase):
    """A single calling point on a train route"""
    field_mapping = [
        ('location_name', 'locationName'),
        ('crs', 'crs'),
        ('et', 'et'),
        ('at', 'at')
    ]

    @property
    def location_name(self):
        """
        The name of the location.
        """
        return self._location_name

    @property
    def crs(self):
        """
        The CRS code of this location. A CRS code of ??? indicates an error situation where no crs code is known for this location.
        """
        return self._crs

    @property
    def at(self):
        """
        The actual time of the service at this location. The time will be either an arrival or departure time, depending on whether it is in the subsequent or previous calling point list. Will only be present if an estimated time (et) is not present.

        Human readable string, no guaranteed format
        """
        return self._at

    @property
    def et(self):
        """
The estimated time of the service at this location. The time will be either an arrival or departure time, depending on whether it is in the subsequent or previous calling point list. Will only be present if an actual time (at) is not present. 

        Human readable string, no guaranteed format
        """
        return self._et

class WebServiceError(Exception):
    pass
