from odoo import api, fields, models


class ApiRestFunctionParameter(models.Model):
    _name = "api.rest.function.parameter"
    _description = "API REST Function Parameter"

    path_id = fields.Many2one("api.rest.path", required=True, ondelete="cascade")
    name = fields.Char(required=True)
    sequence = fields.Integer()
    type = fields.Selection(
        [
            ("integer", "Integer"),
            ("float", "Float"),
            ("boolean", "Boolean"),
            ("string", "String"),
            ("array", "Array"),
            ("object", "Object (Dictionary)"),
        ],
        required=True,
    )
    description = fields.Char()
    required = fields.Boolean()
    default_value = fields.Char()

    @api.onchange("default_value", "required")
    def _onchange_default_value(self):
        if self.default_value:
            self.required = False
