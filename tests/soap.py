from pathlib import Path

from dill import load, dump
from suds import Client


class _TestSoapClient(object):
    def __init__(self):
        self._client = Client(
            "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx",
        )

    def mock_response_from_file(self, operation_a, operation_b, file_path):
        with file_path.open("r") as handle:
            xml_content = handle.read()
        xml_content = xml_content.encode("utf-8")
        return self._client.service[operation_a][operation_b](
            __inject={"reply": xml_content}
        )


__client_instance = None


def _get_instance():
    global __client_instance
    if __client_instance is None:
        __client_instance = _TestSoapClient()

    return __client_instance


def soap_response(query_name, xml_filename):
    base_path = Path(__file__).parent
    xml_path = base_path / "testdata" / xml_filename
    cache_path = xml_path.with_suffix(".dill")

    #  Attempt to load the cached result - this saves create an instance of the SOAP client
    if cache_path.exists():
        with cache_path.open("rb") as handle:
            resp = load(handle)
    else:
        resp = _get_instance().mock_response_from_file(
            "LDBServiceSoap",
            query_name,
            xml_path)
        with cache_path.open("wb") as handle:
            dump(resp, handle)
    return resp
