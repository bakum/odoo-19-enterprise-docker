import json

from odoo import _
from odoo.http import Controller, request, route

from ..tools import RecordNotFoundError, api_management, eval_request_params
from ..tools.http import get_cors_headers


def _get_model_obj(model_name, kwargs):
    model_obj = request.env[model_name]
    if "context" in kwargs:
        model_obj = model_obj.with_context(**kwargs.get("context"))
        del kwargs["context"]
    return model_obj


class OpenApiDocs(Controller):
    @route("/api-docs/v<string:version>", auth="public", methods=["GET"])
    def api_docs(self, version=False, **kwargs):
        api_version = request.env["api.rest.version"].sudo().search(
            [("name", "=", version)], limit=1
        )
        if not api_version:
            return request.not_found()
        return request.render("openapi.openapi", {"url_swagger": api_version.url_swagger})

    @route("/api-docs/v<string:version>/swagger.json", auth="public", methods=["GET"])
    def api_json(self, version, **kwargs):
        api_version = request.env["api.rest.version"].sudo().search(
            [("name", "=", version)], limit=1
        )
        if not api_version:
            return {"error": "API not found"}
        data = api_version.get_swagger_json()
        return request.make_response(
            json.dumps(data),
            headers=[("Content-Type", "application/json")] + get_cors_headers(),
        )


class OpenApiController(Controller):
    @route(
        [
            "/api/v<string:_api_version>/<string:_api_name>",
            "/api/v<string:_api_version>/<string:_api_name>/<int:_api_id>",
            "/api/v<string:_api_version>/<string:_api_name>/<string:_api_method>",
            "/api/v<string:_api_version>/<string:_api_name>/<string:_api_method>/<int:_api_id>",
        ],
        auth="public",
        methods=["OPTIONS"],
        csrf=False,
    )
    def preflight(self, **kwargs):
        return request.make_response("", headers=get_cors_headers())

    @route("/api/v<string:_api_version>/<string:_api_name>", auth="bearer_api_key", methods=["GET"], csrf=False)
    @api_management()
    def search_read(self, _api_version, _api_name, _api_path, **kwargs):
        eval_request_params(kwargs)
        _api_path._search_treatment_kwargs(kwargs)
        model_obj = _get_model_obj(_api_path.model, kwargs)
        domain = kwargs.get("domain", [])
        return {
            "results": model_obj.search_read(**kwargs),
            "total": model_obj.search_count(domain),
            "offset": kwargs.get("offset", 0),
            "limit": kwargs.get("limit", 0),
            "version": _api_version,
        }

    @route(
        "/api/v<string:_api_version>/<string:_api_name>/<int:_api_id>",
        auth="bearer_api_key",
        methods=["GET"],
        csrf=False,
    )
    @api_management()
    def read(self, _api_version, _api_name, _api_id, _api_path, **kwargs):
        eval_request_params(kwargs)
        _api_path._read_treatment_kwargs(kwargs)
        model_obj = _get_model_obj(_api_path.model, kwargs)
        read_domain = _api_path._eval_domain(_api_path.filter_domain) + [("id", "=", _api_id)]
        record = model_obj.search(read_domain, limit=1)
        if not record:
            raise RecordNotFoundError(_("Record not found"))
        result = record.read(**kwargs)
        return result[0] if result else {}

    @route("/api/v<string:_api_version>/<string:_api_name>", auth="bearer_api_key", methods=["POST"], csrf=False)
    @api_management()
    def create(self, _api_version, _api_name, _api_path, **kwargs):
        eval_request_params(kwargs)
        model_obj = _get_model_obj(_api_path.model, kwargs)
        return model_obj.create(_api_path._post_treatment_values(kwargs)).id

    @route(
        "/api/v<string:_api_version>/<string:_api_name>/<int:_api_id>",
        auth="bearer_api_key",
        methods=["PUT"],
        csrf=False,
    )
    @api_management()
    def write(self, _api_version, _api_name, _api_id, _api_path, **kwargs):
        eval_request_params(kwargs)
        model_obj = _get_model_obj(_api_path.model, kwargs)
        update_domain = _api_path._eval_domain(_api_path.update_domain) + [("id", "=", _api_id)]
        record = model_obj.search(update_domain, limit=1)
        if not record:
            raise RecordNotFoundError(_("Record not found"))
        return record.write(_api_path._post_treatment_values(kwargs))

    @route(
        "/api/v<string:_api_version>/<string:_api_name>/<int:_api_id>",
        auth="bearer_api_key",
        methods=["DELETE"],
        csrf=False,
    )
    @api_management()
    def unlink(self, _api_version, _api_name, _api_id, _api_path, **kwargs):
        eval_request_params(kwargs)
        model_obj = _get_model_obj(_api_path.model, kwargs)
        unlink_domain = _api_path._eval_domain(_api_path.unlink_domain) + [("id", "=", _api_id)]
        record = model_obj.search(unlink_domain, limit=1)
        if not record:
            raise RecordNotFoundError(_("Record not found"))
        return record.unlink()

    @route(
        [
            "/api/v<string:_api_version>/<string:_api_name>/<string:_api_method>",
            "/api/v<string:_api_version>/<string:_api_name>/<string:_api_method>/<int:_api_id>",
        ],
        auth="bearer_api_key",
        methods=["PUT"],
        csrf=False,
    )
    @api_management()
    def custom_method(self, _api_version, _api_name, _api_method, _api_path, _api_id=False, **kwargs):
        eval_request_params(kwargs)
        model_obj = _get_model_obj(_api_path.model, kwargs)
        if _api_id and _api_path.function_apply_on_record:
            function_domain = _api_path._eval_domain(_api_path.function_domain) + [("id", "=", _api_id)]
            record = model_obj.search(function_domain, limit=1)
            if not record:
                raise RecordNotFoundError(_("Record not found"))
        else:
            record = model_obj.browse()
        kwargs = _api_path._custom_treatment_values(kwargs)
        return getattr(record, _api_path.function)(**kwargs)
