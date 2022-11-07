import unittest

import nredarwin.webservice
from tests.soap import soap_response


class NextDepartures(unittest.TestCase):

    def setUp(self):
        resp = soap_response("GetNextDepartures", "next-departures.xml")
        self.next_departures = nredarwin.webservice.DepartureBoard(resp)

    def test_basic(self):
        self.assertEqual(self.next_departures.crs, "ECR")
        self.assertEqual(self.next_departures.location_name, "East Croydon")

        self.assertEqual(len(self.next_departures.departures), 2)

    def test_firstDeparture(self):
        first_departure = self.next_departures.departures[0]
        self.assertEqual(first_departure.crs, "CLJ")
        self.assertEqual(first_departure.service.sta, "22:15")
        self.assertEqual(first_departure.service.eta, "On time")
        self.assertEqual(first_departure.service.std, "22:15")
        self.assertEqual(first_departure.service.etd, "On time")
        self.assertEqual(first_departure.service.platform, "4")
        self.assertEqual(first_departure.service.operator_name, "Southern")
        self.assertEqual(first_departure.service.operator_code, "SN")
        self.assertEqual(first_departure.service.length, "12")
        self.assertEqual(first_departure.service.service_id, "AjQqemx5vaZC87JCOBdU7A==")
        self.assertEqual(first_departure.service.origin_text, "East Grinstead")
        self.assertEqual(first_departure.service.origins[0].location_name, "East Grinstead")
        self.assertEqual(first_departure.service.origins[0].crs, "EGR")
        self.assertEqual(first_departure.service.destination_text, "London Victoria")
        self.assertEqual(first_departure.service.destinations[0].location_name, "London Victoria")
        self.assertEqual(first_departure.service.destinations[0].crs, "VIC")

    def test_secondDeparture(self):
        second_departure = self.next_departures.departures[1]
        self.assertEqual(second_departure.crs, "LBG")
        self.assertEqual(second_departure.service.sta, "22:19")
        self.assertEqual(second_departure.service.eta, "22:26")
        self.assertEqual(second_departure.service.std, "22:21")
        self.assertEqual(second_departure.service.etd, "22:27")
        self.assertEqual(second_departure.service.platform, "2")
        self.assertEqual(second_departure.service.operator_name, "Thameslink")
        self.assertEqual(second_departure.service.operator_code, "TL")
        self.assertEqual(second_departure.service.length, None)
        self.assertEqual(second_departure.service.service_id, "EFpoyguzo/xLlJw80uW6eA==")
        self.assertEqual(second_departure.service.origin_text, "Brighton")
        self.assertEqual(second_departure.service.origins[0].location_name, "Brighton")
        self.assertEqual(second_departure.service.origins[0].crs, "BTN")
        self.assertEqual(second_departure.service.destination_text, "London Bridge")
        self.assertEqual(second_departure.service.destinations[0].location_name, "London Bridge")
        self.assertEqual(second_departure.service.destinations[0].crs, "LBG")


class NextDeparturesWithDetails(unittest.TestCase):

    def setUp(self):
        resp = soap_response("GetNextDeparturesWithDetails", "next-departures-with-details.xml")
        self.next_departures = nredarwin.webservice.DepartureBoardWithDetails(resp)

    def test_firstDepartureCallingPoints(self):
        first_departure_calling_points = self.next_departures.departures[0].service.subsequent_calling_point_lists[
            0].calling_points
        self.assertEqual(len(first_departure_calling_points), 2)

        self.assertEqual(first_departure_calling_points[0].location_name, "Clapham Junction")
        self.assertEqual(first_departure_calling_points[0].crs, "CLJ")
        self.assertEqual(first_departure_calling_points[0].st, "22:25")
        self.assertEqual(first_departure_calling_points[0].et, "On time")
        self.assertEqual(first_departure_calling_points[0].length, "12")

        self.assertEqual(first_departure_calling_points[1].location_name, "London Victoria")
        self.assertEqual(first_departure_calling_points[1].crs, "VIC")
        self.assertEqual(first_departure_calling_points[1].st, "22:32")
        self.assertEqual(first_departure_calling_points[1].et, "On time")
        self.assertEqual(first_departure_calling_points[1].length, "12")

    def test_secondDepartureCallingPoints(self):
        second_departure_calling_points = self.next_departures.departures[1].service.subsequent_calling_point_lists[
            0].calling_points
        self.assertEqual(len(second_departure_calling_points), 1)

        self.assertEqual(second_departure_calling_points[0].location_name, "London Bridge")
        self.assertEqual(second_departure_calling_points[0].crs, "LBG")
        self.assertEqual(second_departure_calling_points[0].st, "22:39")
        self.assertEqual(second_departure_calling_points[0].et, "22:44")
        self.assertEqual(second_departure_calling_points[0].length, None)
