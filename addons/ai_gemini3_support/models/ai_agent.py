from odoo import fields, models


class AIAgent(models.Model):
    _inherit = "ai.agent"

    def _get_llm_model_selection(self):
        selection = list(super()._get_llm_model_selection())
        to_add = [
            ("gemini-3-flash-preview", "Gemini 3 Flash Preview"),
            ("gemini-3-flash-lite-preview", "Gemini 3 Flash Lite Preview"),
            ("gemini-3.1-flash-lite-preview", "Gemini 3.1 Flash Lite Preview"),
            ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview"),
        ]
        existing = {value for value, _label in selection}
        for item in to_add:
            if item[0] not in existing:
                selection.append(item)
        deprecated_models = {"gemini-1.5-pro", "gemini-1.5-flash"}
        return [item for item in selection if item[0] not in deprecated_models]

    llm_model = fields.Selection(
        selection="_get_llm_model_selection",
        string="LLM Model",
        default="gemini-3-flash-lite-preview",
        required=True,
    )
