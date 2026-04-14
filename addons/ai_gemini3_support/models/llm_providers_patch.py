from odoo.addons.ai.utils import llm_providers


GEMINI_3_LLMS = [
    ("gemini-3-flash-preview", "Gemini 3 Flash Preview"),
    ("gemini-3-flash-lite-preview", "Gemini 3 Flash Lite Preview"),
    ("gemini-3.1-flash-lite-preview", "Gemini 3.1 Flash Lite Preview"),
    ("gemini-3.1-pro-preview", "Gemini 3.1 Pro Preview"),
]


def _patch_google_provider_llms():
    providers = list(llm_providers.PROVIDERS)
    for index, provider in enumerate(providers):
        if provider.name != "google":
            continue

        merged_llms = list(provider.llms)
        existing_model_names = {name for name, _label in merged_llms}
        for model_name, model_label in GEMINI_3_LLMS:
            if model_name not in existing_model_names:
                merged_llms.append((model_name, model_label))

        providers[index] = llm_providers.Provider(
            provider.name,
            provider.display_name,
            provider.embedding_model,
            provider.embedding_config,
            merged_llms,
        )
        llm_providers.PROVIDERS = providers
        break


_patch_google_provider_llms()
