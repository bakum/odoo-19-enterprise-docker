from werkzeug import urls

from odoo import api, fields, models


class ApiRestVersion(models.Model):
    _name = "api.rest.version"
    _description = "API REST Version"

    name = fields.Char(string="Version", required=True)
    active = fields.Boolean(default=True)
    description = fields.Html()
    url_api_docs = fields.Char(compute="_compute_urls")
    url_swagger = fields.Char(compute="_compute_urls")
    path_ids = fields.One2many(
        "api.rest.path", "version_id", string="Paths", context={"active_test": False}
    )
    user_ids = fields.Many2many("res.users", string="Allowed Users")
    active_log = fields.Boolean()
    last_usage_date = fields.Datetime()
    log_ids = fields.One2many("api.rest.log", "version_id", string="Logs", readonly=True)

    @api.depends("name")
    def _compute_urls(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", default="")
        for record in self:
            record.url_api_docs = urls.url_join(base_url, f"/api-docs/v{record.name}")
            record.url_swagger = urls.url_join(base_url, f"/api-docs/v{record.name}/swagger.json")

    def go_to_api_docs(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": self.url_api_docs, "target": "_new"}

    def get_swagger_json(self):
        self.ensure_one()
        web_base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        parsed_url = urls.url_parse(web_base_url)
        paths = self.sudo().path_ids.filtered(lambda path: path.active)
        swagger_tags = [{"name": tag.name or "", "description": tag.description or ""} for tag in paths.mapped("tag_id")]
        swagger_paths = {}
        swagger_definitions = {}
        for path in paths:
            path._generate_path(swagger_paths)
            path._generate_definition(swagger_definitions)
        return {
            "swagger": "2.0",
            "info": {
                "version": self.name,
                "title": "OpenAPI Connector",
                "description": self.get_swagger_description(),
            },
            "host": parsed_url.netloc,
            "schemes": [parsed_url.scheme],
            "basePath": f"/api/v{self.name}",
            "paths": swagger_paths,
            "tags": swagger_tags,
            "securityDefinitions": {
                "api_key": {"type": "apiKey", "name": "Authorization", "in": "header"}
            },
            "definitions": swagger_definitions,
        }

    def get_swagger_description(self):
        self.ensure_one()
        description = self.description or ""
        other_versions = self.search([("id", "!=", self.id)])
        if other_versions:
            description += "<p><b>Other APIs available:</b></p><ul>"
            for api_version in other_versions:
                description += f"<li><a href='{api_version.url_api_docs}'>{api_version.url_api_docs}</a></li>"
            description += "</ul>"
        return description
