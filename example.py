import nredarwin.webservice

# initiate a session
# this depends on the DARWIN_WEBSERVICE_API_KEY environment variable
# The WSDL environment variable also allows for
darwin_session = nredarwin.webservice.Session(wsdl='https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx')
print("Enter 3 digit CRS code:")
try:
    input = raw_input #python2 has raw_input, python3 has input
except NameError:
    pass
crs_code = input().upper()

# retrieve departure board
board = darwin_session.get_station_board(crs_code)

# print table header
print("\nNext departures for %s" % (board.location_name))
print("""
-------------------------------------------------------------------------------
|  PLAT  | DEST                                        |   SCHED   |    DUE   |
------------------------------------------------------------------------------- """)

# Loop through services
for service in board.train_services:
    print("| %6s | %43s | %9s | %8s |" %(service.platform or "", service.destination_text, service.std, service.etd))

# Print a footer 
print("-------------------------------------------------------------------------------")
