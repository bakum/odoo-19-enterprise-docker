from odoo import http, models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_bearer_api_key(cls):
        auth_header = http.request.httprequest.headers.get("Authorization")
        if not auth_header:
            raise http.BadRequest("Authorization header with API key missing")
        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0] != "Bearer":
            raise http.BadRequest("Authorization must be Bearer type")
        user_id = http.request.env["res.users.apikeys"]._check_credentials(
            scope="api", key=parts[1]
        )
        if not user_id:
            raise http.BadRequest("API key invalid")
        http.request.update_env(user=user_id)
