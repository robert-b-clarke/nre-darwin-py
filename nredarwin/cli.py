import argparse
from nredarwin.webservice import DarwinLdbSession
import csv
import sys
from tabulate import tabulate
from functools import partial


def rows_to_display(station_board):
    """
    Iterator for tabular output of board
    """
    yield (("Platform", "Destination", "Scheduled", "Due"))
    for service in station_board.train_services:
        yield (
            service.platform,
            service.destination_text,
            service.std,
            service.etd,
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "station", type=str, help="station CRS code, e.g. MAN for Manchester Piccadilly"
    )
    ap.add_argument(
        "--destination",
        type=str,
        required=False,
        help="Only include services travelling to this CRS code, e.g HUD",
    )
    ap.add_argument("--csv", action="store_true", help="output in csv format")
    args = ap.parse_args()
    darwin_session = DarwinLdbSession(
        wsdl="https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx"
    )
    # build up query
    board_query = partial(darwin_session.get_station_board, args.station)
    if args.destination:
        board_query = partial(board_query, destination_crs=args.destination)

    # convert to tabular data for display
    board_rows = rows_to_display(board_query())

    # output CSV if requested
    if args.csv:
        output_writer = csv.writer(sys.stdout, dialect="unix")
        output_writer.writerows(board_rows)
        return

    # Otherwise output human readable table
    print(tabulate(board_rows, headers="firstrow"))
