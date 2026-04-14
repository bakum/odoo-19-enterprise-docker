from werkzeug.exceptions import abort

from odoo.http import Controller, route, request, Response
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPHandler, HTTPSHandler
import base64
import binascii
import re

KNOWN_HOSTS = {
    "czo.gov.ua",
    "zc.bank.gov.ua",
    "acskidd.gov.ua",
    "ca.informjust.ua",
    "csk.uz.gov.ua",
    "masterkey.ua",
    "ocsp.masterkey.ua",
    "tsp.masterkey.ua",
    "csk.uss.gov.ua",
    "csk.ukrsibbank.com",
    "acsk.privatbank.ua",
    "ca.mil.gov.ua",
    "acsk.dpsu.gov.ua",
    "acsk.er.gov.ua",
    "ca.mvs.gov.ua",
    "canbu.bank.gov.ua",
    "uakey.com.ua",
    "altersign.com.ua",
    "ca.altersign.com.ua",
    "ocsp.altersign.com.ua",
    "acsk.treasury.gov.ua",
    "ocsp.treasury.gov.ua",
    "ca.gp.gov.ua",
    "acsk.oree.com.ua",
    "ca.treasury.gov.ua",
    "ca.depositsign.com",
    "ca.alfabank.kiev.ua",
    "cesaris.itsway.kiev.ua",
    "ca.credit-agricole.ua",
    "ca.e-life.com.ua",
    "ocsp.e-life.com.ua",
    "tsp.e-life.com.ua",
    "cmp.e-life.com.ua",
    "ca.bankalliance.ua",
    "ca.vchasno.ua",
    "qca.ukrgasbank.com",
    "ca.tax.gov.ua",
    "ca.diia.gov.ua",
    "ca.sensebank.com.ua",
    "ca.tascombank.com.ua",
    "ca.tascombank.ua",
    "va1-knedp.ssu.gov.ua",
    "root-test.czo.gov.ua",
    "ca-test.czo.gov.ua",
    "ca.monobank.ua",
}
URI_MAX_LENGTH = 255
URI_REGEX = r'^(https?:\/\/)?([a-zA-Z0-9.\-]+)(:[0-9]{1,5})?(\/(.*))?$'
HTTP_REQUEST_PARAMETER_ADDRESS = "address"
HTTP_CONTENT_TYPE_BASE64 = "X-user/base64-data"
REQUEST_TIMEOUT_SECONDS = 10
MAX_PROXY_REQUEST_BYTES = 8 * 1024 * 1024
MAX_PROXY_RESPONSE_BYTES = 8 * 1024 * 1024


class EUSignerProxyHundler(Controller):
    def _open_url(self, url, method, headers, data=None):
        request_obj = Request(url=url, data=data, headers=headers, method=method)
        opener = build_opener(HTTPHandler(), HTTPSHandler())
        return opener.open(request_obj, timeout=REQUEST_TIMEOUT_SECONDS)

    def isKnownHost(self, uriValue):
        try:
            if len(uriValue) > URI_MAX_LENGTH or not re.match(URI_REGEX, uriValue):
                return False
            if uriValue.find("://") == -1:
                uriValue = "http://" + uriValue
            uri = urlparse(uriValue)
            if uri.scheme != "http" and uri.scheme != "https":
                return False
            host = uri.hostname
            if host is None or host == "":
                host = uriValue
            if host.lower() in KNOWN_HOSTS:
                return True
        except (ValueError, TypeError):
            return False
        return False

    def getContentType(self, uriValue):
        try:
            if uriValue.find("://") == -1:
                uriValue = "http://" + uriValue

            path = urlparse(uriValue).path
            if path == None or path == "":
                return ""

            if path[len(path) - 1] == '/':
                path = path[:-1]

            if path == "/services/cmp" or path == '/public/x509/cmp' or path == 'cmp' or path == '/api/PKI/CMP':
                return ""
            elif path == "/services/ocsp" or path == "/services/ocsp/" or path == "/public/ocsp" or path == "/ocsp" or path == "/ocsp-rsa" or path == "/ocsp-ecdsa" or path == "/OCSPsrv/ocsp" or path == "/queries/ocsp/":
                return "application/ocsp-request"
            elif path == "/services/tsp" or path == "/services/tsp/" or path == "/services/tsp/dstu" or path == "/services/tsp/dstu/" or path == "/services/tsp/rsa" or path == "/services/tsp/rsa/" or path == "/services/tsp/ecdsa" or path == "/services/tsp/ecdsa/" or path == "/public/tsa" or path == "/public/tsp" or path == "/tsp" or path == "/tsp-rsa" or path == "/ecdsa" or path == "/TspHTTPServer/tsp":
                return "application/timestamp-query"
            else:
                return ""
        except (ValueError, TypeError):
            return ""

    def HandleRequest(self, httpMethod, httpHeaders, httpURLParams, httpRequestData):
        returnResponse = {'status': 200, 'data': ''}

        address = httpURLParams.get(HTTP_REQUEST_PARAMETER_ADDRESS, '')
        if address == "":
            returnResponse['status'] = 400
            return returnResponse
        if self.isKnownHost(address) == False:
            returnResponse['status'] = 403
            return returnResponse

        url = address
        if url.find("://") == -1:
            url = "http://" + url

        headers = {"Accept": "*/*", "Pragma": "no-cache"}

        try:
            if httpMethod == 'POST':
                if httpHeaders.get('Content-Type') != HTTP_CONTENT_TYPE_BASE64:
                    returnResponse['status'] = 400
                    return returnResponse
                if len(httpRequestData) > MAX_PROXY_REQUEST_BYTES:
                    returnResponse['status'] = 413
                    return returnResponse

                headers['Content-Type'] = self.getContentType(address)
                requestData = base64.b64decode(httpRequestData, validate=True)
                if len(requestData) > MAX_PROXY_REQUEST_BYTES:
                    returnResponse['status'] = 413
                    return returnResponse
                response = self._open_url(
                    url,
                    "POST",
                    headers,
                    requestData,
                )
            else:
                response = self._open_url(
                    url,
                    "GET",
                    headers,
                )

            status_code = response.getcode()
            response_content = response.read()
            returnResponse['status'] = status_code
            if status_code == 200:
                if len(response_content) > MAX_PROXY_RESPONSE_BYTES:
                    returnResponse['status'] = 502
                    return returnResponse
                returnResponse['data'] = base64.b64encode(response_content).decode('utf-8')
        except (binascii.Error, ValueError):
            returnResponse['status'] = 400
        except HTTPError as error:
            returnResponse['status'] = error.code
        except (URLError, TimeoutError):
            returnResponse['status'] = 500

        return returnResponse

    @route("/signer/proxyHandler", auth="public", csrf=False, methods=["GET", "POST"])
    def proxy(self, **kwargs):
        proxyResponse = self.HandleRequest(request.httprequest.method, request.httprequest.headers, request.httprequest.args, request.httprequest.data)
        if proxyResponse['status'] != 200:
            abort(proxyResponse['status'])

        returnResponse = Response(proxyResponse['data'], content_type=HTTP_CONTENT_TYPE_BASE64)

        return returnResponse
