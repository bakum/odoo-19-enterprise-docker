from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOpenApi(TransactionCase):
    def setUp(self):
        super().setUp()
        self.version = self.env["api.rest.version"].create({"name": "1"})
        partner_model = self.env["ir.model"].search([("model", "=", "res.partner")], limit=1)
        self.env["api.rest.path"].create(
            {
                "name": "partners",
                "version_id": self.version.id,
                "model_id": partner_model.id,
                "method": "get",
            }
        )

    def test_swagger_generation_contains_path(self):
        swagger = self.version.get_swagger_json()
        self.assertIn("/partners", swagger["paths"])
        self.assertEqual(swagger["basePath"], "/api/v1")


@tagged("post_install", "-at_install")
class TestOpenApiHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "openapi.cors_origins", "https://app.example.com"
        )
        version = cls.env["api.rest.version"].create({"name": "1"})
        partner_model = cls.env["ir.model"].search([("model", "=", "res.partner")], limit=1)
        cls.env["api.rest.path"].create(
            {
                "name": "partners",
                "version_id": version.id,
                "model_id": partner_model.id,
                "method": "get",
            }
        )

    def test_docs_swagger_json_available(self):
        response = self.url_open("/api-docs/v1/swagger.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn('"basePath": "/api/v1"', response.text)

    def test_docs_response_contains_cors_headers_for_allowed_origin(self):
        response = self.url_open(
            "/api-docs/v1/swagger.json",
            headers={
                "Origin": "https://app.example.com",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            "https://app.example.com",
        )
