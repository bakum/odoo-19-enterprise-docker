import base64
import json

from odoo import fields, models
from odoo.http import request


RESPONSE_DATA_MAX_CHARACTERS = 5000


class ApiRestLog(models.Model):
    _name = "api.rest.log"
    _order = "create_date desc"
    _description = "API REST Log"

    version_id = fields.Many2one("api.rest.version", required=True, ondelete="cascade")
    request_url = fields.Char()
    request_headers = fields.Text()
    request_data = fields.Text()
    response_data = fields.Text()
    length_response_data = fields.Integer(compute="_compute_response_info", store=True)
    summary_response_data = fields.Text("Details", compute="_compute_response_info", store=True)
    file_response_data = fields.Binary(compute="_compute_response_info", store=True)
    filename_response_data = fields.Char(compute="_compute_response_info", store=True)

    def _compute_response_info(self):
        for record in self:
            payload = record.response_data or ""
            length = len(payload)
            summary = payload[:RESPONSE_DATA_MAX_CHARACTERS]
            if length > RESPONSE_DATA_MAX_CHARACTERS:
                summary += "....."
            record.length_response_data = length
            record.summary_response_data = summary
            record.file_response_data = base64.b64encode(payload.encode("utf-8"))
            record.filename_response_data = f"response_data_{record.id}.log"

    def create_log(self, version_id, request_data, response_data, user=False):
        values = {
            "version_id": version_id,
            "request_url": request.httprequest.base_url,
            "request_headers": json.dumps(dict(request.httprequest.headers)),
            "request_data": json.dumps(request_data, default=str),
            "response_data": response_data,
        }
        user_to_use = user or self.env.ref("base.public_user")
        log = self.sudo().with_user(user_to_use).create(values)
        log.sudo().version_id.last_usage_date = fields.Datetime.now()
        return log
