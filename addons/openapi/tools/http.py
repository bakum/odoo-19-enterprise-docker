import json
from datetime import date, datetime
from functools import wraps

from odoo import _, models
from odoo.http import Response, request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.safe_eval import safe_eval


HEADERS = [("Content-Type", "application/json")]


def make_error(code, error, description, status, version=False, request_data=False):
    response_data = json.dumps(
        {"code": code, "error": error, "description": description}
    )
    if version and version.active_log:
        request.env["api.rest.log"].create_log(version.id, request_data, response_data)
    return Response(response_data, status=status, headers=HEADERS + get_cors_headers())


class RecordNotFoundError(Exception):
    """Raised when filtered record does not exist."""


class api_management:
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request_data = kwargs.copy()
            if request.httprequest.method == "OPTIONS":
                return Response("", status=200, headers=get_cors_headers())
            api_version = kwargs.get("_api_version")
            api_name = kwargs.get("_api_name")
            api_method = kwargs.get("_api_method")
            if not api_version or not api_name:
                return make_error(1002, "Not found", _("Resource not found or unavailable"), 404)

            http_method = request.httprequest.method.lower()
            if api_method and api_method == "custom":
                http_method = "custom"
            path = request.env["api.rest.path"].sudo().search(
                [("version_id.name", "=", api_version), ("name", "=", api_name), ("method", "=", http_method)],
                limit=1,
            )
            if not path:
                return make_error(1003, "Not found", _("Resource not found or unavailable"), 404)

            if path.version_id.user_ids and request.env.user not in path.version_id.user_ids:
                return make_error(1004, "Forbidden", _("Unauthorized access"), 403, version=path.version_id, request_data=request_data)

            kwargs["_api_path"] = path
            try:
                result = decode_value(func(*args, **kwargs))
                response_data = json.dumps(result)
                if path.version_id.active_log:
                    request.env["api.rest.log"].create_log(
                        path.version_id.id, request_data, response_data, user=request.env.user
                    )
                request.env.cr.commit()
                return Response(response_data, headers=HEADERS + get_cors_headers())
            except Exception as exc:  # pylint: disable=broad-except
                request.env.cr.rollback()
                code = 1005
                status = 500
                error = "Internal server error"
                if isinstance(exc, RecordNotFoundError):
                    code = 1006
                    status = 404
                    error = "Not found"
                response_data = json.dumps(
                    {"code": code, "error": error, "description": str(exc)}
                )
                if path.version_id.active_log:
                    request.env["api.rest.log"].create_log(
                        path.version_id.id, request_data, response_data, user=request.env.user
                    )
                request.env.cr.commit()
                return Response(response_data, status=status, headers=HEADERS + get_cors_headers())

        return wrapper


def eval_request_params(kwargs):
    for key, value in kwargs.items():
        try:
            kwargs[key] = safe_eval(value)
        except Exception:  # pylint: disable=broad-except
            continue


def decode_value(result):
    if isinstance(result, (list, tuple)):
        return [decode_value(item) for item in result]
    if isinstance(result, dict):
        return {decode_value(k): decode_value(v) for k, v in result.items()}
    if isinstance(result, bytes):
        return result.decode("utf-8")
    if isinstance(result, datetime):
        return result.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    if isinstance(result, date):
        return result.strftime(DEFAULT_SERVER_DATE_FORMAT)
    if isinstance(result, models.BaseModel):
        return result.id
    return result


def get_cors_headers():
    """Return CORS headers only for allowed origins."""
    if not request or not request.httprequest:
        return []
    origin = request.httprequest.headers.get("Origin")
    if not origin:
        return []
    allowed_origins = (
        request.env["ir.config_parameter"]
        .sudo()
        .get_param("openapi.cors_origins", default="")
    )
    origins = {item.strip() for item in allowed_origins.split(",") if item.strip()}
    if origin not in origins:
        return []
    return [
        ("Access-Control-Allow-Origin", origin),
        ("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS"),
        ("Access-Control-Allow-Headers", "Authorization,Content-Type"),
        ("Access-Control-Allow-Credentials", "true"),
        ("Vary", "Origin"),
    ]
