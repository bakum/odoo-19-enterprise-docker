from copy import deepcopy

from odoo import _, api, fields, models
from odoo.tools import safe_eval


MAPPING_FIELDS_SWAGGER = {
    "binary": ("string", "binary"),
    "boolean": ("boolean", ""),
    "char": ("string", ""),
    "date": ("string", "date"),
    "datetime": ("string", "date-time"),
    "float": ("number", "float"),
    "html": ("string", ""),
    "integer": ("integer", ""),
    "many2many": ("array", ""),
    "many2one": ("integer", ""),
    "many2one_reference": ("integer", ""),
    "monetary": ("number", "float"),
    "one2many": ("array", ""),
    "reference": ("string", ""),
    "selection": ("array", ""),
    "text": ("string", ""),
}
LIMIT_MAX = 500


def _convert_field_type_to_swagger(ttype):
    return MAPPING_FIELDS_SWAGGER.get(ttype, ("string", ""))


def _format_definition_name(name):
    return (name or "").replace(" ", "")


class ApiRestPath(models.Model):
    _name = "api.rest.path"
    _order = "model_id"
    _rec_name = "model_id"
    _description = "API REST Path"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    version_id = fields.Many2one("api.rest.version", string="API Version", required=True, ondelete="cascade")
    model_id = fields.Many2one("ir.model", required=True, ondelete="cascade")
    model = fields.Char(related="model_id.model", readonly=True)
    method = fields.Selection(
        [("get", "Read"), ("post", "Create"), ("put", "Update"), ("delete", "Delete"), ("custom", "Custom function")],
        required=True,
    )
    description = fields.Html()
    deprecated = fields.Boolean()
    tag_id = fields.Many2one("api.rest.tag", string="Tag", ondelete="set null")
    filter_domain = fields.Char(default="[]")
    field_ids = fields.Many2many("ir.model.fields", domain="[('model_id', '=', model_id)]", string="Fields")
    limit = fields.Integer(string="Limit of results", default=500)
    warning_required = fields.Boolean(compute="_compute_warning_required", compute_sudo=True)
    api_field_ids = fields.One2many("api.rest.field", "path_id", string="Fields", copy=True)
    update_domain = fields.Char(default="[]")
    unlink_domain = fields.Char(default="[]")
    function_apply_on_record = fields.Boolean()
    function_domain = fields.Char(default="[]")
    function = fields.Char()
    function_parameter_ids = fields.One2many("api.rest.function.parameter", "path_id", string="Parameters", copy=True)

    _sql_constraints = [
        ("name_uniq", "unique (name, version_id, method)", "Name, Version and Method must be unique!"),
    ]

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.field_ids = False
        self.api_field_ids = False

    def _compute_warning_required(self):
        for record in self:
            warning_required = False
            if record.api_field_ids:
                model_required = record.model_id.field_id.filtered(lambda f: f.required).mapped("name")
                api_required = record.api_field_ids.filtered(lambda f: f.required).mapped("field_id.name")
                warning_required = not all(field in api_required for field in model_required)
            record.warning_required = warning_required

    def _normalize_values(self, values):
        if values.get("name"):
            values["name"] = values["name"].replace(" ", "")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_values(vals)
        return super().create(vals_list)

    def write(self, values):
        self._normalize_values(values)
        return super().write(values)

    def copy(self, default=None):
        default = dict(default or {})
        default.update(name=_("%s (copy)") % (self.name or ""))
        return super().copy(default)

    def _generate_path(self, swagger_paths):
        self.ensure_one()
        values = {
            "tags": [self.tag_id.name or ""] if self.tag_id else [],
            "description": self.description or "",
            "deprecated": self.deprecated,
            "produces": ["application/json"],
            "responses": {
                "200": {"description": "OK"},
                "401": {"description": "Unauthorized", "schema": {"$ref": "#/definitions/ApiErrorResponse"}},
                "403": {"description": "Forbidden", "schema": {"$ref": "#/definitions/ApiErrorResponse"}},
                "404": {"description": "Not found", "schema": {"$ref": "#/definitions/ApiErrorResponse"}},
                "500": {"description": "Internal server error", "schema": {"$ref": "#/definitions/ApiErrorResponse"}},
            },
            "security": [{"api_key": []}],
        }
        if self.method == "get":
            get_path = f"/{self.name}"
            get_one_path = f"/{self.name}/{{Id}}"
            swagger_paths.setdefault(get_path, {})
            swagger_paths.setdefault(get_one_path, {})
            values["responses"]["200"].update(
                {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "results": {"type": "array", "items": {"$ref": f"#/definitions/{_format_definition_name(self.name)}"}},
                            "total": {"type": "integer"},
                            "offset": {"type": "integer"},
                            "limit": {"type": "integer"},
                        },
                    }
                }
            )
            values.update(parameters=self._get_parameters_all_elements())
            swagger_paths[get_path].update({"get": values})
            values_one = deepcopy(values)
            values_one["responses"]["200"].update({"schema": {"$ref": f"#/definitions/{_format_definition_name(self.name)}"}})
            values_one.update(parameters=self._get_parameters_one_element())
            swagger_paths[get_one_path].update({"get": values_one})
        elif self.method == "post" and self.api_field_ids:
            post_path = f"/{self.name}"
            swagger_paths.setdefault(post_path, {})
            values["responses"]["200"].update({"description": _("Identifier of the created resource."), "schema": {"type": "integer"}})
            values.update(consumes=self._form_urlencoded_consumes(), parameters=self._post_parameters())
            swagger_paths[post_path].update({"post": values})
        elif self.method == "put" and self.api_field_ids:
            put_path = f"/{self.name}/{{Id}}"
            swagger_paths.setdefault(put_path, {})
            values["responses"]["200"].update({"description": _("Return true when update succeeds."), "schema": {"type": "boolean"}})
            values.update(consumes=self._form_urlencoded_consumes(), parameters=self._put_parameters())
            swagger_paths[put_path].update({"put": values})
        elif self.method == "delete":
            delete_path = f"/{self.name}/{{Id}}"
            swagger_paths.setdefault(delete_path, {})
            values["responses"]["200"].update({"description": _("Return true when delete succeeds."), "schema": {"type": "boolean"}})
            values.update(parameters=self._delete_parameters())
            swagger_paths[delete_path].update({"delete": values})
        elif self.method == "custom":
            route = f"/{self.name}/custom"
            if self.function_apply_on_record:
                route = f"/{self.name}/custom/{{Id}}"
            values.update(consumes=self._form_urlencoded_consumes(), parameters=self._custom_parameters())
            swagger_paths[route] = {"put": values}

    def _generate_definition(self, swagger_definitions):
        self.ensure_one()
        if self.method == "get":
            swagger_definitions[_format_definition_name(self.name)] = {
                "type": "object",
                "properties": self._get_definition_properties(),
            }
        swagger_definitions["ApiErrorResponse"] = {
            "type": "object",
            "properties": {
                "code": {"type": "integer", "description": _("Error code")},
                "error": {"type": "string", "description": _("Error name")},
                "description": {"type": "string", "description": _("Error description")},
            },
        }

    def _id_parameter(self):
        return {"name": "Id", "in": "path", "description": "ID", "required": True, "type": "integer"}

    def _context_parameter(self, parameter_type="query"):
        return {"name": "context", "in": parameter_type, "description": _('Example: `{"lang": "en_US"}`'), "type": "string", "required": False}

    def _domain_parameter(self):
        return {"name": "domain", "in": "query", "description": _("Search domain."), "required": False, "type": "string"}

    def _fields_parameter(self):
        return {"name": "fields", "in": "query", "description": _("List of fields."), "required": False, "type": "string"}

    def _offset_parameter(self):
        return {"name": "offset", "in": "query", "description": _("Number of records to skip."), "required": False, "type": "integer"}

    def _limit_parameter(self):
        return {"name": "limit", "in": "query", "default": self.limit, "description": _("Maximum number of records."), "required": False, "type": "integer"}

    def _order_parameter(self):
        return {"name": "order", "in": "query", "description": _("Sort expression, e.g. `name asc`."), "required": False, "type": "string"}

    def _get_parameters_all_elements(self):
        return [self._domain_parameter(), self._fields_parameter(), self._offset_parameter(), self._limit_parameter(), self._order_parameter(), self._context_parameter()]

    def _get_parameters_one_element(self):
        return [self._id_parameter(), self._fields_parameter(), self._context_parameter()]

    def _search_treatment_kwargs(self, kwargs):
        self.ensure_one()
        limit = kwargs.get("limit", 0)
        max_limit = self.limit or LIMIT_MAX
        kwargs["limit"] = limit if (limit and limit <= max_limit) else max_limit
        domain = kwargs.get("domain", [])
        if self.filter_domain:
            domain += self._eval_domain(self.filter_domain)
        kwargs["domain"] = domain
        self._treatment_fields(kwargs)

    def _read_treatment_kwargs(self, kwargs):
        self.ensure_one()
        self._treatment_fields(kwargs)

    def _treatment_fields(self, kwargs):
        allowed_fields = ["id"] + self.field_ids.mapped("name")
        requested = kwargs.get("fields", [])
        kwargs["fields"] = list(set(requested) & set(allowed_fields)) if requested else allowed_fields

    def _get_definition_properties(self):
        properties = {"id": {"type": "integer"}}
        for field in self.field_ids:
            swagger_type, swagger_format = _convert_field_type_to_swagger(field.ttype)
            values = {"type": swagger_type, "format": swagger_format, "description": field.field_description or ""}
            self._update_values_ttype(field, values, definition=True)
            properties[field.name] = values
        return properties

    def _post_parameters(self):
        return self._post_properties() + [self._context_parameter(parameter_type="formData")]

    def _post_properties(self):
        properties = []
        for api_field in self.api_field_ids.filtered(lambda field: not field.default_value):
            swagger_type, swagger_format = _convert_field_type_to_swagger(api_field.field_id.ttype)
            values = {
                "in": "formData",
                "name": api_field.field_name,
                "type": swagger_type,
                "format": swagger_format,
                "description": api_field.description or "",
                "required": api_field.required,
            }
            self._update_values_ttype(api_field.field_id, values)
            properties.append(values)
        return properties

    def _post_treatment_values(self, post_values):
        self.ensure_one()
        new_values = post_values.copy()
        allowed_fields = self.api_field_ids.mapped("field_name")
        for field in list(post_values):
            if field not in allowed_fields:
                new_values.pop(field, None)
        for field in self.api_field_ids.filtered(lambda item: item.default_value):
            new_values[field.field_name] = safe_eval.safe_eval(field.default_value)
        for field in self.api_field_ids.filtered(lambda item: item.field_id.ttype == "boolean").mapped("field_name"):
            if field in post_values:
                new_values[field] = post_values.get(field) in ["1", "true", "True", True]
        for field in self.api_field_ids.filtered(lambda item: item.field_id.ttype in ["many2many", "one2many"]).mapped("field_name"):
            if field in post_values and isinstance(post_values.get(field), int):
                new_values[field] = [post_values.get(field)]
        return new_values

    def _put_parameters(self):
        return [self._id_parameter()] + self._post_properties() + [self._context_parameter(parameter_type="formData")]

    def _delete_parameters(self):
        return [self._id_parameter(), self._context_parameter(parameter_type="formData")]

    def _custom_parameters(self):
        parameters = self._custom_function_parameters() + [self._context_parameter(parameter_type="formData")]
        if self.function_apply_on_record:
            return [self._id_parameter()] + parameters
        return parameters

    def _custom_function_parameters(self):
        properties = []
        for parameter in self.function_parameter_ids.filtered(lambda item: not item.default_value):
            parameter_type = parameter.type
            parameter_format = ""
            if parameter_type == "float":
                parameter_type = "number"
                parameter_format = "float"
            values = {
                "name": parameter.name,
                "in": "formData",
                "description": parameter.description or "",
                "required": parameter.required,
                "type": parameter_type,
                "format": parameter_format,
            }
            if parameter_type == "array":
                values.update(items={"type": "string"})
            properties.append(values)
        return properties

    def _custom_treatment_values(self, post_values):
        python_types = {"integer": int, "float": float, "boolean": bool, "string": str, "array": list, "object": dict}
        values = {}
        for parameter in self.function_parameter_ids:
            if parameter.name in post_values:
                value = post_values.get(parameter.name)
                expected_type = python_types.get(parameter.type)
                if expected_type and not isinstance(value, expected_type):
                    try:
                        values[parameter.name] = expected_type(value)
                    except Exception:  # pylint: disable=broad-except
                        continue
                else:
                    values[parameter.name] = value
            if parameter.default_value:
                values[parameter.name] = safe_eval.safe_eval(parameter.default_value)
        return values

    def _form_urlencoded_consumes(self):
        return ["application/x-www-form-urlencoded"]

    def _update_values_ttype(self, field, values, definition=False):
        field_name = field.name
        if field.ttype == "selection":
            if definition:
                values.update({"type": "string"})
            else:
                selection_keys = list(dict(self.env[self.model].fields_get([field_name])[field_name]["selection"]).keys())
                values.update({"items": {"type": "string", "enum": selection_keys}})
        if field.ttype in ["many2many", "one2many"]:
            values.update({"items": {"type": "integer"}})
        if field.ttype == "many2one" and definition:
            values.update({"type": "array", "items": {"type": "string"}})
        if field.ttype == "date":
            values["description"] = f"{values.get('description', '')}\n\n{_('Example: `YYYY-MM-DD`')}"
        if field.ttype == "datetime":
            values["description"] = f"{values.get('description', '')}\n\n{_('Example: `YYYY-MM-DD HH:MM:SS`')}"
        return values

    def _get_eval_context(self):
        return {
            "datetime": safe_eval.datetime,
            "dateutil": safe_eval.dateutil,
            "time": safe_eval.time,
            "uid": self.env.uid,
            "user": self.env.user,
        }

    def _eval_domain(self, domain):
        self.ensure_one()
        return safe_eval.safe_eval(domain, self._get_eval_context())
