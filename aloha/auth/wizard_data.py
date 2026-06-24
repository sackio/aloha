"""
aloha/auth/wizard_data.py

Static wizard step data for each AI provider's setup flow.

Each entry in WIZARD_STEPS maps a provider id to a list of step dicts.
Step dict fields:
    step        — 1-based step index
    title       — short title shown as the step heading
    instruction — full instruction text shown to the user
    url         — (optional) URL to open in a new tab
    image_alt   — (optional) alt text for a screenshot image
    action      — (optional) machine-readable action hint for the frontend
                  e.g. "copy_key", "enter_key", "enter_url", "run_command"
"""

from __future__ import annotations

WIZARD_STEPS: dict[str, list[dict]] = {
    "openai": [
        {
            "step": 1,
            "title": "Create an OpenAI account",
            "instruction": (
                "Visit platform.openai.com and sign up for an account. "
                "If you already have an account, log in."
            ),
            "url": "https://platform.openai.com/signup",
            "image_alt": "OpenAI Platform sign-up page",
        },
        {
            "step": 2,
            "title": "Navigate to API Keys",
            "instruction": (
                "In the OpenAI Platform, click your profile icon in the top-right, "
                "then choose 'API keys' from the menu, or go directly to the link below."
            ),
            "url": "https://platform.openai.com/api-keys",
            "image_alt": "OpenAI API Keys management page",
        },
        {
            "step": 3,
            "title": "Create a new secret key",
            "instruction": (
                "Click the '+ Create new secret key' button. "
                "Give it a descriptive name like 'Aloha'. "
                "Copy the key immediately — it will not be shown again."
            ),
            "action": "copy_key",
        },
        {
            "step": 4,
            "title": "Add billing credits",
            "instruction": (
                "OpenAI requires prepaid credits to use the API. "
                "Go to the billing page and add a payment method and credits."
            ),
            "url": "https://platform.openai.com/settings/organization/billing",
            "image_alt": "OpenAI billing page",
        },
        {
            "step": 5,
            "title": "Enter your API key",
            "instruction": "Paste the OpenAI API key you just copied into the field below.",
            "action": "enter_key",
        },
    ],

    "openrouter": [
        {
            "step": 1,
            "title": "Create an OpenRouter account",
            "instruction": (
                "Visit openrouter.ai and sign up with your email, Google, or GitHub account."
            ),
            "url": "https://openrouter.ai/",
            "image_alt": "OpenRouter sign-up page",
        },
        {
            "step": 2,
            "title": "Create an API key",
            "instruction": (
                "Go to openrouter.ai/keys, click 'Create Key', give it a name, "
                "and copy it. OpenRouter gives a small amount of free credits on sign-up."
            ),
            "url": "https://openrouter.ai/keys",
            "image_alt": "OpenRouter API keys page",
        },
        {
            "step": 3,
            "title": "Add credits (optional)",
            "instruction": (
                "To use paid models like Claude or GPT-4o, add credits at openrouter.ai/credits. "
                "Many models have free tiers."
            ),
            "url": "https://openrouter.ai/credits",
            "image_alt": "OpenRouter credits page",
        },
        {
            "step": 4,
            "title": "Enter your API key",
            "instruction": "Paste your OpenRouter API key in the field below.",
            "action": "enter_key",
        },
    ],

    "groq": [
        {
            "step": 1,
            "title": "Create a Groq account",
            "instruction": (
                "Visit console.groq.com and sign up. "
                "Groq provides very fast inference for open-source models."
            ),
            "url": "https://console.groq.com/",
            "image_alt": "Groq Console sign-up page",
        },
        {
            "step": 2,
            "title": "Create an API key",
            "instruction": (
                "Go to console.groq.com/keys, click 'Create API Key', "
                "give it a name (e.g. 'Aloha'), and copy the key."
            ),
            "url": "https://console.groq.com/keys",
            "image_alt": "Groq API keys page",
        },
        {
            "step": 3,
            "title": "Enter your API key",
            "instruction": "Paste your Groq API key in the field below.",
            "action": "enter_key",
        },
    ],

    "custom": [
        {
            "step": 1,
            "title": "Enter your API base URL",
            "instruction": (
                "Enter the base URL of your OpenAI-compatible API endpoint. "
                "For example: http://localhost:1234/v1 (LM Studio), "
                "http://localhost:8080/v1 (llama.cpp server), "
                "or any other OpenAI-compatible service."
            ),
            "action": "enter_url",
        },
        {
            "step": 2,
            "title": "Enter your API key (if required)",
            "instruction": (
                "If your endpoint requires authentication, enter the API key here. "
                "Leave blank for local endpoints that do not require a key "
                "(e.g. Ollama, LM Studio in local mode)."
            ),
            "action": "enter_key",
        },
    ],
}
