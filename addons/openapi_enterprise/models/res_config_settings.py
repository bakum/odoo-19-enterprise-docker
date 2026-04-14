from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    openapi_cors_origins = fields.Char(
        string="OpenAPI Allowed CORS Origins",
        config_parameter="openapi.cors_origins",
        help="Comma-separated list, for example: https://app.example.com,https://admin.example.com",
    )
