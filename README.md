# LM Studio Assistant for Flow Launcher

Flow Launcher Python plugin for local LM Studio API.

> Русская версия: [README_ru.md](README_ru.md)

## Features

- Chat with loaded local models via `POST /api/v1/chat`
- List models via `GET /api/v1/models`
- Load and unload model instances
- Start model download and check download status
- Optional Bearer token header (not required for local unsecured setups)

## Commands

Use action keyword `lm`.

You can type only `lm`, select any command from the list, and press Enter to autocomplete it.

- `lm models` (select model and press Enter to load)
- `lm chat <prompt>`
- `lm chat <model_key> :: <prompt>`
- `lm load` (or `lm load <filter>`) then Enter on model to load
- `lm load! <model_key>` (direct load by key)
- `lm unload! <instance_id>`
- `lm download! <model_or_hf_url>`
- `lm status` (show loaded model instances and runtime config)
- `lm status <job_id>` (check download status)

`!` commands are available for direct actions by explicit key/ID.

For `lm chat`, the model reply is shown in results and pressing Enter copies the full reply.
If a model instance is already running in LM Studio, chat uses that running instance automatically.

## Settings

Open plugin settings in Flow Launcher and configure:

- `baseUrl` default: `http://localhost:1234`
- `apiToken` optional (empty by default)
- `defaultModel` model key for chat without explicit model
- `systemPrompt` optional system prompt
- `temperature` 0..1
- `maxOutputTokens` optional integer
- `reasoning` off/low/medium/high/on
- `contextLength` optional integer
- `timeoutSeconds` HTTP timeout

## Install

1. Put this folder into `%APPDATA%\FlowLauncher\Plugins\LMStudioAssistant`.
2. Install dependencies in that folder: `pip install -r requirements.txt`.
3. Restart Flow Launcher or run `Reload Plugin Data`.
4. Trigger plugin with `lm`.

## Notes

- LM Studio must be running with local API enabled.
- If authentication is disabled in LM Studio, leave `apiToken` empty.
