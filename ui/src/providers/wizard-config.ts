/**
 * Provider configurations and wizard step definitions for the setup wizard.
 * This is the single source of truth for all provider metadata used in the UI.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ProviderConfig {
  id: "anthropic" | "openai" | "gemini" | "ollama" | "openrouter" | "groq" | "custom";
  name: string;
  description: string;
  requires_api_key: boolean;
  models: string[];
  default_model: string;
  /** URL to the provider's API key / console page */
  console_url?: string;
  /** Whether this provider supports OAuth (future) */
  supports_oauth?: boolean;
  wizard_steps: WizardStep[];
}

export interface WizardStep {
  id: string;
  title: string;
  description: string;
  /** Actionable instructions shown in the step body */
  instructions?: string[];
  /** External links shown alongside instructions */
  links?: Array<{ label: string; url: string }>;
}

// ---------------------------------------------------------------------------
// Provider definitions
// ---------------------------------------------------------------------------

export const PROVIDERS: ProviderConfig[] = [
  // ---------------------------------------------------------------------------
  // Anthropic / Claude
  // ---------------------------------------------------------------------------
  {
    id: "anthropic",
    name: "Anthropic (Claude)",
    description:
      "Claude models from Anthropic — best reasoning and instruction following.",
    requires_api_key: true,
    models: [
      "claude-opus-4-5",
      "claude-sonnet-4-5",
      "claude-haiku-3-5",
    ],
    default_model: "claude-opus-4-5",
    console_url: "https://console.anthropic.com/account/keys",
    supports_oauth: false,
    wizard_steps: [
      {
        id: "welcome",
        title: "Welcome to Aloha",
        description:
          "Aloha connects your Home Assistant to an AI assistant. Let's get you set up in a few steps.",
        instructions: [
          "Choose your AI provider on the next screen.",
          "Enter your API key and Home Assistant token.",
          "Aloha will test the connection and you'll be ready to go.",
        ],
      },
      {
        id: "api_key",
        title: "Enter your Anthropic API key",
        description:
          "Create a free account on the Anthropic Console and generate an API key.",
        instructions: [
          "Go to console.anthropic.com and sign in (or create an account).",
          "Navigate to Account → API Keys.",
          "Click \"Create Key\", give it a name like \"Aloha\", and copy it.",
          "Paste the key in the field below.",
        ],
        links: [
          { label: "Anthropic Console", url: "https://console.anthropic.com/account/keys" },
        ],
      },
      {
        id: "ha_token",
        title: "Connect to Home Assistant",
        description:
          "Aloha needs a long-lived access token to control your Home Assistant.",
        instructions: [
          "In Home Assistant, open your profile (click your username in the sidebar).",
          "Scroll to the bottom to find \"Long-Lived Access Tokens\".",
          "Click \"Create Token\", name it \"Aloha\", and copy it.",
          "Paste the token in the field below.",
        ],
        links: [
          { label: "HA Profile page", url: "http://homeassistant.local:8123/profile" },
        ],
      },
      {
        id: "done",
        title: "You're all set!",
        description:
          "Aloha is connected to Anthropic Claude and your Home Assistant. Start chatting!",
      },
    ],
  },

  // ---------------------------------------------------------------------------
  // OpenAI
  // ---------------------------------------------------------------------------
  {
    id: "openai",
    name: "OpenAI",
    description: "GPT-4o and other OpenAI models.",
    requires_api_key: true,
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    default_model: "gpt-4o",
    console_url: "https://platform.openai.com/api-keys",
    supports_oauth: false,
    wizard_steps: [
      {
        id: "welcome",
        title: "Welcome to Aloha",
        description:
          "Aloha connects your Home Assistant to an AI assistant. Let's get you set up.",
        instructions: [
          "You've chosen OpenAI as your provider.",
          "You'll need an OpenAI API key with sufficient credits.",
          "The wizard will walk you through the remaining steps.",
        ],
      },
      {
        id: "api_key",
        title: "Enter your OpenAI API key",
        description:
          "Create or retrieve an API key from the OpenAI platform.",
        instructions: [
          "Go to platform.openai.com and sign in.",
          "Navigate to API Keys in the left sidebar.",
          "Click \"Create new secret key\", name it \"Aloha\", and copy it.",
          "Paste it in the field below. Make sure your account has billing set up.",
        ],
        links: [
          { label: "OpenAI API Keys", url: "https://platform.openai.com/api-keys" },
          { label: "OpenAI Billing", url: "https://platform.openai.com/account/billing" },
        ],
      },
      {
        id: "model",
        title: "Choose a model",
        description: "Select which OpenAI model Aloha should use.",
        instructions: [
          "gpt-4o — Most capable, best for complex tasks (higher cost).",
          "gpt-4o-mini — Faster and cheaper, great for most tasks.",
          "gpt-4-turbo — Previous generation, still very capable.",
        ],
      },
      {
        id: "ha_token",
        title: "Connect to Home Assistant",
        description:
          "Aloha needs a long-lived access token to control your Home Assistant.",
        instructions: [
          "In Home Assistant, open your profile (click your username in the sidebar).",
          "Scroll to the bottom and click \"Create Token\" under Long-Lived Access Tokens.",
          "Name it \"Aloha\" and paste the token below.",
        ],
        links: [
          { label: "HA Profile page", url: "http://homeassistant.local:8123/profile" },
        ],
      },
      {
        id: "done",
        title: "You're all set!",
        description:
          "Aloha is connected to OpenAI and your Home Assistant. Start chatting!",
      },
    ],
  },

  // ---------------------------------------------------------------------------
  // Google Gemini
  // ---------------------------------------------------------------------------
  {
    id: "gemini",
    name: "Google Gemini",
    description: "Gemini 2.0 Flash and Gemini 1.5 Pro from Google.",
    requires_api_key: true,
    models: ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    default_model: "gemini-2.0-flash",
    console_url: "https://aistudio.google.com/app/apikey",
    supports_oauth: false,
    wizard_steps: [
      {
        id: "welcome",
        title: "Welcome to Aloha",
        description: "You've chosen Google Gemini as your AI provider.",
        instructions: [
          "Gemini 2.0 Flash is fast and free-tier friendly.",
          "You'll need a Google AI Studio API key to continue.",
        ],
      },
      {
        id: "api_key",
        title: "Enter your Google AI Studio API key",
        description: "Get a free API key from Google AI Studio.",
        instructions: [
          "Go to aistudio.google.com and sign in with your Google account.",
          "Click \"Get API key\" and then \"Create API key\".",
          "Copy the key and paste it below.",
          "The free tier includes generous usage for Gemini 2.0 Flash.",
        ],
        links: [
          { label: "Google AI Studio", url: "https://aistudio.google.com/app/apikey" },
        ],
      },
      {
        id: "ha_token",
        title: "Connect to Home Assistant",
        description:
          "Aloha needs a long-lived access token to control your Home Assistant.",
        instructions: [
          "In Home Assistant, open your profile (click your username in the sidebar).",
          "Scroll to the bottom and click \"Create Token\" under Long-Lived Access Tokens.",
          "Name it \"Aloha\" and paste the token below.",
        ],
        links: [
          { label: "HA Profile page", url: "http://homeassistant.local:8123/profile" },
        ],
      },
      {
        id: "done",
        title: "You're all set!",
        description:
          "Aloha is connected to Google Gemini and your Home Assistant.",
      },
    ],
  },

  // ---------------------------------------------------------------------------
  // Ollama (local)
  // ---------------------------------------------------------------------------
  {
    id: "ollama",
    name: "Ollama (local)",
    description:
      "Run open-source models locally — fully private, no API key needed.",
    requires_api_key: false,
    models: [],
    default_model: "",
    console_url: "https://ollama.com/library",
    supports_oauth: false,
    wizard_steps: [
      {
        id: "welcome",
        title: "Welcome to Aloha",
        description:
          "You've chosen Ollama for fully local, private AI. No API keys or cloud accounts needed.",
        instructions: [
          "Ollama must be installed and running on your network.",
          "You'll enter the Ollama server URL and pick a model.",
          "Recommended models: llama3.3, mistral, qwen2.5.",
        ],
        links: [
          { label: "Install Ollama", url: "https://ollama.com" },
          { label: "Browse models", url: "https://ollama.com/library" },
        ],
      },
      {
        id: "ollama_url",
        title: "Ollama server URL",
        description: "Where is your Ollama server running?",
        instructions: [
          "Default: http://localhost:11434 (if Ollama is on the same machine as Aloha).",
          "If Ollama runs on another machine, enter its IP, e.g. http://192.168.1.100:11434.",
          "Make sure Ollama is running: run `ollama serve` or check its service status.",
        ],
      },
      {
        id: "model",
        title: "Choose a model",
        description:
          "Select from the models currently pulled into your Ollama instance.",
        instructions: [
          "Aloha will list models available on your Ollama server.",
          "If the list is empty, pull a model first: `ollama pull llama3.3`.",
          "For Home Assistant tasks, llama3.3 or qwen2.5:14b work well.",
        ],
        links: [
          { label: "Browse Ollama models", url: "https://ollama.com/library" },
        ],
      },
      {
        id: "ha_token",
        title: "Connect to Home Assistant",
        description:
          "Aloha needs a long-lived access token to control your Home Assistant.",
        instructions: [
          "In Home Assistant, open your profile (click your username in the sidebar).",
          "Scroll to the bottom and click \"Create Token\" under Long-Lived Access Tokens.",
          "Name it \"Aloha\" and paste the token below.",
        ],
        links: [
          { label: "HA Profile page", url: "http://homeassistant.local:8123/profile" },
        ],
      },
      {
        id: "done",
        title: "You're all set!",
        description:
          "Aloha is running with your local Ollama instance. All processing stays on your network.",
      },
    ],
  },

  // ---------------------------------------------------------------------------
  // OpenRouter
  // ---------------------------------------------------------------------------
  {
    id: "openrouter",
    name: "OpenRouter",
    description:
      "Access 100+ models (Claude, GPT-4, Gemini, Llama, Mistral) through a single API.",
    requires_api_key: true,
    models: [
      "anthropic/claude-opus-4-5",
      "anthropic/claude-sonnet-4-5",
      "openai/gpt-4o",
      "google/gemini-2.0-flash",
      "meta-llama/llama-3.3-70b-instruct",
    ],
    default_model: "anthropic/claude-sonnet-4-5",
    console_url: "https://openrouter.ai/keys",
    supports_oauth: false,
    wizard_steps: [
      {
        id: "welcome",
        title: "Welcome to Aloha",
        description:
          "You've chosen OpenRouter — access hundreds of AI models through one API key.",
        instructions: [
          "OpenRouter lets you switch between Claude, GPT-4, Gemini, Llama, and more.",
          "Pay-per-token pricing, often cheaper than direct provider APIs.",
          "Create a free account at openrouter.ai to get started.",
        ],
        links: [
          { label: "OpenRouter", url: "https://openrouter.ai" },
        ],
      },
      {
        id: "api_key",
        title: "Enter your OpenRouter API key",
        description: "Get an API key from openrouter.ai.",
        instructions: [
          "Go to openrouter.ai and sign in (or create a free account).",
          "Navigate to Keys and click \"Create Key\".",
          "Copy the key (it starts with sk-or-) and paste it below.",
          "Add credits at openrouter.ai/credits to enable usage.",
        ],
        links: [
          { label: "OpenRouter Keys", url: "https://openrouter.ai/keys" },
          { label: "Add credits", url: "https://openrouter.ai/credits" },
        ],
      },
      {
        id: "model",
        title: "Choose a model",
        description:
          "Select the model you want Aloha to use via OpenRouter.",
        instructions: [
          "anthropic/claude-opus-4-5 — Highest capability for complex tasks.",
          "anthropic/claude-sonnet-4-5 — Great balance of capability and speed.",
          "openai/gpt-4o — OpenAI's flagship multimodal model.",
          "google/gemini-2.0-flash — Fast and efficient.",
          "meta-llama/llama-3.3-70b-instruct — Open-source, low cost.",
        ],
        links: [
          { label: "Browse all OpenRouter models", url: "https://openrouter.ai/models" },
        ],
      },
      {
        id: "ha_token",
        title: "Connect to Home Assistant",
        description:
          "Aloha needs a long-lived access token to control your Home Assistant.",
        instructions: [
          "In Home Assistant, open your profile (click your username in the sidebar).",
          "Scroll to the bottom and click \"Create Token\" under Long-Lived Access Tokens.",
          "Name it \"Aloha\" and paste the token below.",
        ],
        links: [
          { label: "HA Profile page", url: "http://homeassistant.local:8123/profile" },
        ],
      },
      {
        id: "done",
        title: "You're all set!",
        description:
          "Aloha is connected to OpenRouter. You can switch models any time in Settings.",
      },
    ],
  },

  // ---------------------------------------------------------------------------
  // Groq
  // ---------------------------------------------------------------------------
  {
    id: "groq",
    name: "Groq",
    description:
      "Blazing-fast inference for Llama and Mixtral models via Groq LPU hardware.",
    requires_api_key: true,
    models: [
      "llama-3.3-70b-versatile",
      "llama-3.1-8b-instant",
      "mixtral-8x7b-32768",
    ],
    default_model: "llama-3.3-70b-versatile",
    console_url: "https://console.groq.com/keys",
    supports_oauth: false,
    wizard_steps: [
      {
        id: "welcome",
        title: "Welcome to Aloha",
        description:
          "You've chosen Groq — the fastest AI inference available, with a generous free tier.",
        instructions: [
          "Groq runs open-source models (Llama, Mixtral) on custom LPU hardware.",
          "Free tier includes thousands of tokens per minute.",
          "Create a free account at console.groq.com.",
        ],
        links: [
          { label: "Groq Console", url: "https://console.groq.com" },
        ],
      },
      {
        id: "api_key",
        title: "Enter your Groq API key",
        description: "Get a free API key from the Groq Console.",
        instructions: [
          "Go to console.groq.com and sign in (or create a free account).",
          "Click API Keys in the sidebar, then \"Create API Key\".",
          "Copy the key and paste it below.",
          "The free tier is generous — no credit card needed.",
        ],
        links: [
          { label: "Groq API Keys", url: "https://console.groq.com/keys" },
        ],
      },
      {
        id: "ha_token",
        title: "Connect to Home Assistant",
        description:
          "Aloha needs a long-lived access token to control your Home Assistant.",
        instructions: [
          "In Home Assistant, open your profile (click your username in the sidebar).",
          "Scroll to the bottom and click \"Create Token\" under Long-Lived Access Tokens.",
          "Name it \"Aloha\" and paste the token below.",
        ],
        links: [
          { label: "HA Profile page", url: "http://homeassistant.local:8123/profile" },
        ],
      },
      {
        id: "done",
        title: "You're all set!",
        description:
          "Aloha is connected to Groq. Enjoy ultra-fast AI responses for your Home Assistant.",
      },
    ],
  },

  // ---------------------------------------------------------------------------
  // Custom (OpenAI-compatible)
  // ---------------------------------------------------------------------------
  {
    id: "custom",
    name: "Custom (OpenAI-compatible)",
    description:
      "Any OpenAI-compatible API endpoint — LM Studio, vLLM, Together AI, etc.",
    requires_api_key: false,
    models: [],
    default_model: "",
    supports_oauth: false,
    wizard_steps: [
      {
        id: "custom_url",
        title: "Custom API endpoint",
        description:
          "Enter the base URL of your OpenAI-compatible API server.",
        instructions: [
          "The URL should point to the root of the API, e.g. http://localhost:1234/v1.",
          "Compatible servers include: LM Studio, vLLM, Together AI, Fireworks AI, Anyscale.",
          "An API key is optional — leave it blank if your server doesn't require one.",
        ],
        links: [
          { label: "LM Studio", url: "https://lmstudio.ai" },
          { label: "Together AI", url: "https://api.together.xyz" },
        ],
      },
      {
        id: "ha_token",
        title: "Connect to Home Assistant",
        description:
          "Aloha needs a long-lived access token to control your Home Assistant.",
        instructions: [
          "In Home Assistant, open your profile (click your username in the sidebar).",
          "Scroll to the bottom and click \"Create Token\" under Long-Lived Access Tokens.",
          "Name it \"Aloha\" and paste the token below.",
        ],
        links: [
          { label: "HA Profile page", url: "http://homeassistant.local:8123/profile" },
        ],
      },
      {
        id: "done",
        title: "You're all set!",
        description:
          "Aloha is connected to your custom OpenAI-compatible endpoint.",
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Lookup helper
// ---------------------------------------------------------------------------

export function getProviderConfig(id: string): ProviderConfig | undefined {
  return PROVIDERS.find((p) => p.id === id);
}
