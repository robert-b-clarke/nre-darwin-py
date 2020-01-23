from suds.client import Client
from suds.transport.http import HttpTransport

from suds.sax.element import Element
from suds import WebFault
from functools import partial
import logging
import os

log = logging.getLogger(__name__)
# TODO - timeouts and error handling
DARWIN_WEBSERVICE_NAMESPACE = (
    "com",
    "http://thalesgroup.com/RTTI/2010-11-01/ldb/commontypes",
)


class WellBehavedHttpTransport(HttpTransport):
    """
    Suds HttpTransport which properly obeys the ``*_proxy`` environment
    variables.
    """

    def u2handlers(self):
        """
        Override suds HTTP Transport as it does not properly honor local
        system configuration for proxy settings

        Derived from https://gist.github.com/rbarrois/3721801
        """
        return []


class DarwinLdbSession(object):
    """
    A connection to the Darwin LDB web service
    """

    def __init__(self, wsdl=None, api_key=None, timeout=5):
        """
        Constructor

        Keyword arguments:
        wsdl -- the URL of the Darwin LDB WSDL document. Will fall back to
        using the DARWIN_WEBSERVICE_WSDL environment variable if not supplied
        api_key -- a valid API key for the Darwin LDB webservice. Will fall
        back to the DARWIN_WEBSERVICE_API_KEY if not supplied
        timeout -- a timeout in seconds for calls to the LDB Webservice
        (default 5)
        """
        if not wsdl:
            wsdl = os.environ["DARWIN_WEBSERVICE_WSDL"]
        if not api_key:
            api_key = os.environ["DARWIN_WEBSERVICE_API_KEY"]
        self._soap_client = Client(wsdl, transport=WellBehavedHttpTransport())
        self._soap_client.set_options(timeout=timeout)
        # build soap headers
        token3 = Element("AccessToken", ns=DARWIN_WEBSERVICE_NAMESPACE)
        token_value = Element("TokenValue", ns=DARWIN_WEBSERVICE_NAMESPACE)
        token_value.setText(api_key)
        token3.append(token_value)
        self._soap_client.set_options(soapheaders=(token3))

    def _base_query(self):
        return self._soap_client.service["LDBServiceSoap"]

    def get_station_board(
        self,
        crs,
        rows=17,
        include_departures=True,
        include_arrivals=False,
        destination_crs=None,
        origin_crs=None,
    ):
        """
        Query the darwin webservice to obtain a board for a particular station
        and return a StationBoard instance

        Positional arguments:
        crs -- the three letter CRS code of a UK station

        Keyword arguments:
        rows -- the number of rows to retrieve (default 10)
        include_departures -- include departing services in the departure board
        (default True)
        include_arrivals -- include arriving services in the departure board
        (default False)
        destination_crs -- filter results so they only include services
        calling at a particular destination (default None)
        origin_crs -- filter results so they only include services
        originating from a particular station (default None)
        """
        # Determine the darwn query we want to make
        if include_departures and include_arrivals:
            query_type = "GetArrivalDepartureBoard"
        elif include_departures:
            query_type = "GetDepartureBoard"
        elif include_arrivals:
            query_type = "GetArrivalBoard"
        else:
            raise ValueError(
                "get_station_board must have either include_departures or \
include_arrivals set to True"
            )
        # build a query function
        q = partial(self._base_query()[query_type], crs=crs, numRows=rows)
        if destination_crs:
            if origin_crs:
                log.warn(
                    "Station board query can only filter on one of \
destination_crs and origin_crs, using only destination_crs"
                )
            q = partial(q, filterCrs=destination_crs, filterType="to")
        elif origin_crs:
            q = partial(q, filterCrs=origin_crs, filterType="from")
        try:
            soap_response = q()
        except WebFault:
            raise WebServiceError
        return StationBoard(soap_response)

    def get_service_details(self, service_id):
        """
        Get the details of an individual service and return a ServiceDetails
        instance.

        Positional arguments:
        service_id: A Darwin LDB service id
        """
        service_query = self._soap_client.service["LDBServiceSoap"]["GetServiceDetails"]
        try:
            soap_response = service_query(serviceID=service_id)
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
            setattr(self, "_" + dest_key, val)


class StationBoard(SoapResponseBase):
    """
    An abstract representation of a station departure board
    """

    field_mapping = [
        ("generated_at", "generatedAt"),
        ("crs", "crs"),
        ("location_name", "locationName"),
    ]

    service_lists = [
        ("train_services", "trainServices"),
        ("bus_services", "busServices"),
        ("ferry_services", "ferryServices"),
    ]

    def __init__(self, soap_response, *args, **kwargs):
        super(StationBoard, self).__init__(soap_response, *args, **kwargs)
        # populate service lists - these are specific to station board
        # objects, so not included in base class
        for dest_key, src_key in self.__class__.service_lists:
            try:
                service_rows = getattr(getattr(soap_response, src_key), "service")
            except AttributeError:
                setattr(self, "_" + dest_key, [])
                continue

            setattr(self, "_" + dest_key, [ServiceItem(s) for s in service_rows])
        # populate nrcc_messages
        if hasattr(soap_response, "nrccMessages") and hasattr(
            soap_response.nrccMessages, "message"
        ):
            # TODO - would be nice to strip HTML from these, especially as
            # it's not compliant with modern standards
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
        The CRS code for the station.
        """
        return self._crs

    @property
    def location_name(self):
        """
        The name of the station.
        """
        return self._location_name

    @property
    def train_services(self):
        """
        A list of train services that appear on this board. Empty if there are
        none
        """
        return self._train_services

    @property
    def bus_services(self):
        """
        A list of bus services that appear on this board. Empty if there are
        none
        """
        return self._bus_services

    @property
    def ferry_services(self):
        """
        A list of ferry services that appear on this board. Empty if there are
        none
        """
        return self._ferry_services

    @property
    def nrcc_messages(self):
        """
        An optional list of important messages that should be displayed with
        the station board. Messages may include HTML hyperlinks and
        paragraphs
        """
        return self._nrcc_messages

    def __str__(self):
        return "%s - %s" % (self.crs, self.location_name)


class ServiceDetailsBase(SoapResponseBase):
    # The generic stuff that both service details classes have
    field_mapping = [
        ("sta", "sta"),
        ("eta", "eta"),
        ("std", "std"),
        ("etd", "etd"),
        ("platform", "platform"),
        ("operator_name", "operator"),
        ("operator_code", "operatorCode"),
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
        Scheduled Time of Arrival. This is optional and may be present for
        station boards which include arrivals.

        This is a human readable string rather than a proper datetime object
        and may not be a time at all
        """
        return self._sta

    @property
    def eta(self):
        """
        Estimated Time of Arrival. This is optional and may be present when an
        sta (Scheduled Time of Arrival) is available.

        This is a human readable string rather than a proper datetime object
        and may not be a time at all
        """
        return self._eta

    @property
    def std(self):
        """
        Scheduled Time of Departure. This is optional and may be present for
        station boards which include departures

        This is a human readable string rather than a proper datetime object
        and may not be a time at all
        """
        return self._std

    @property
    def etd(self):
        """
        Estimated Time of Departure. This is optional and may be present for
        results which contain an std (Scheduled Time of Departure)

        This is a human readable string rather than a proper datetime object
        and may not be a time at all
        """
        return self._etd

    @property
    def platform(self):
        """
        The platform number for the service at this station. Optional.
        """
        return self._platform

    @property
    def operator_name(self):
        """
        The name of the train operator
        """
        return self._operator_name

    @property
    def operator_code(self):
        """
        The National Rail abbreviation for the train operator
        """
        return self._operator_code

    # TODO -Adhoc alerts, datetime inflators - if possible


class ServiceItem(ServiceDetailsBase):
    """
    A single service from a bus, train or ferry departure/arrival board
    """

    field_mapping = ServiceDetailsBase.field_mapping + [
        ("is_circular_route", "isCircularRoute"),
        ("service_id", "serviceID"),
    ]

    def __init__(self, soap_data, *args, **kwargs):
        super(ServiceItem, self).__init__(soap_data, *args, **kwargs)

        # handle service location lists - these should be empty lists if there
        # are no locations
        self._origins = list()
        self._destinations = list()
        if hasattr(soap_data.origin, "location"):
            for orig_loc in soap_data.origin.location:
                self._origins.append(ServiceLocation(orig_loc))
            for dst_loc in soap_data.destination.location:
                self._destinations.append(ServiceLocation(dst_loc))

    @property
    def is_circular_route(self):
        """
        If True this service is following a circular route and will call again
        at this station.
        """
        return self._is_circular_route

    @property
    def service_id(self):
        """
        The unique ID of this service. This ID is specific to the Darwin LDB
        Service
        """
        return self._service_id

    @property
    def origins(self):
        """
        A list of ServiceLocation objects describing the origins of this
        service. A service may have more than multiple origins.
        """
        return self._origins

    @property
    def destinations(self):
        """
        A list of ServiceLocation objects describing the destinations of this
        service. A service may have more than multiple destinations.
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
        ("location_name", "locationName"),
        ("crs", "crs"),
        ("via", "via"),
        ("future_change_to", "futureChangeTo"),
    ]

    @property
    def location_name(self):
        """
        Location name
        """
        return self._location_name

    @property
    def crs(self):
        """
        The CRS code of the location
        """
        return self._crs

    @property
    def via(self):
        """
        An optional string that should be displayed alongside the
        location_name. This provides additional context regarding an
        ambiguous route.
        """
        return self._via

    @property
    def future_change_to(self):
        """
        An optional string that indicates a service type (Bus/Ferry/Train)
        which will replace the current service type in the future.
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
        ("is_cancelled", "isCancelled"),
        ("disruption_reason", "disruptionReason"),
        ("overdue_message", "overdueMessage"),
        ("ata", "ata"),
        ("atd", "atd"),
        ("location_name", "locationName"),
        ("crs", "crs"),
    ]

    def __init__(self, soap_data, *args, **kwargs):
        super(ServiceDetails, self).__init__(soap_data, *args, **kwargs)
        self._previous_calling_point_lists = self._calling_point_lists(
            soap_data, "previousCallingPoints"
        )
        self._subsequent_calling_point_lists = self._calling_point_lists(
            soap_data, "subsequentCallingPoints"
        )

    def _calling_point_lists(self, soap_data, src_key):
        try:
            calling_points = getattr(getattr(soap_data, src_key), "callingPointList")
        except AttributeError:
            return []
        lists = []
        for sublist in calling_points:
            lists.append(CallingPointList(sublist))
        return lists

    @property
    def is_cancelled(self):
        """
        True if this service is cancelled at this location.
        """
        return self._is_cancelled

    @property
    def disruption_reason(self):
        """
        A string containing a disruption reason for this service, if it is
        delayed or cancelled.
        """
        return self._disruption_reason

    @property
    def overdue_message(self):
        """
        A string that describes an overdue event
        """
        return self._overdue_message

    @property
    def ata(self):
        """
        Actual Time of Arrival.

        A human readable string, not guaranteed to be a machine-parsable time
        """
        return self._ata

    @property
    def atd(self):
        """
        Actual Time of Departure.

        A human readable string, not guaranteed to be a machine-parsable time
        """
        return self._atd

    @property
    def location_name(self):
        """
        Location Name

        The name of the location from which the details of this service are
        being accessed and to which the service attributes such as times
        correspond.
        """
        return self._location_name

    @property
    def crs(self):
        """
        The CRS code corresponding to the location_name property.
        """
        return self._crs

    @property
    def previous_calling_point_lists(self):
        """
        A list of CallingPointLists.

        The first CallingPointList is all the calling points of the through
        train from its origin up until immediately before here, with any
        additional CallingPointLIsts (if they are present) containing the
        calling points of associated trains which join the through train from
        their respective origins through to the calling point at which they
        join with the through train.
        """
        return self._previous_calling_point_lists

    @property
    def subsequent_calling_point_lists(self):
        """
        A list of CallingPointLists.

        The first CallingPointList is all the calling points of the through
        train after here until its destination, with any additional
        CallingPointLists (if they are present) containing the calling points
        of associated trains which split from the through train from the
        calling point at which they split off from the through train until
        their respective destinations.
        """
        return self._subsequent_calling_point_lists

    @property
    def previous_calling_points(self):
        """
        A list of CallingPoint objects.

        This is the list of all previous calling points for the service,
        including all associated services if multiple services join together
        to form this service.
        """
        calling_points = list()
        for cpl in self._previous_calling_point_lists:
            calling_points += cpl.calling_points
        return calling_points

    @property
    def subsequent_calling_points(self):
        """
        A list of CallingPoint objects.

        This is the list of all subsequent calling points for the service,
        including all associated services if the service splits into multiple
        services.
        """
        calling_points = list()
        for cpl in self._subsequent_calling_point_lists:
            calling_points += cpl.calling_points
        return calling_points


class CallingPoint(SoapResponseBase):
    """A single calling point on a train route"""

    field_mapping = [
        ("location_name", "locationName"),
        ("crs", "crs"),
        ("et", "et"),
        ("at", "at"),
        ("st", "st"),
    ]

    @property
    def location_name(self):
        """
        Location name
        """
        return self._location_name

    @property
    def crs(self):
        """
        The CRS code for this location
        """
        return self._crs

    @property
    def at(self):
        """
        Actual time

        Human readable string, no guaranteed format
        """
        return self._at

    @property
    def et(self):
        """
        Estimated time

        Human readable string, no guaranteed format
        """
        return self._et

    @property
    def st(self):
        """
        Scheduled time

        Human readable string, no guaranteed format
        """
        return self._st


class CallingPointList(SoapResponseBase):
    """ A list of calling points"""

    field_mapping = [
        ("service_type", "_serviceType"),
        ("service_change_required", "_serviceChangeRequired"),
        ("association_is_cancelled", "_assocIsCancelled"),
    ]

    def __init__(self, soap_data, *args, **kwargs):
        super(CallingPointList, self).__init__(soap_data, *args, **kwargs)
        self._calling_points = self._calling_point_list(soap_data, "callingPoint")

    def _calling_point_list(self, soap_data, src_key):
        try:
            calling_points = getattr(soap_data, src_key)
        except AttributeError:
            return []
        calling_points_list = []
        for point in calling_points:
            calling_points_list.append(CallingPoint(point))
        return calling_points_list

    @property
    def calling_points(self):
        """
        List of CallingPoint objects

        All the calling points contained within this calling point list
        """
        return self._calling_points

    @property
    def service_type(self):
        """
        Service type

        The service type of the service with these calling points (e.g.
        "train")
        """
        return self._service_type

    @property
    def service_change_required(self):
        """
        Service change required

        A boolean indicating whether a change is required between the through
        service and the service to these calling points.
        """
        return self._service_change_required

    @property
    def association_is_cancelled(self):
        """
        Association is cancelled

        A boolean indicating whether this association is cancelled.
        """
        return self._association_is_cancelled


class WebServiceError(Exception):
    pass
