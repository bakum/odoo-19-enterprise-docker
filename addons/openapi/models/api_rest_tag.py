from odoo import fields, models


class ApiRestTag(models.Model):
    _name = "api.rest.tag"
    _description = "API REST Tag"

    name = fields.Char(required=True)
    description = fields.Char()
