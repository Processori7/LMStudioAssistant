import json
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from flowlauncher import FlowLauncher


class LMStudioPlugin(FlowLauncher):
    icon_path = "Images/icon.png"
    last_model_key: Optional[str] = None

    def query(self, query: str) -> List[Dict[str, Any]]:
        text = (query or "").strip()
        if not text:
            return self._help_results()

        command, argument = self._split_query(text)

        if command in {"help", "?"}:
            return self._help_results()

        if command == "models":
            return self._handle_models()

        if command == "status":
            if not argument:
                return self._handle_runtime_status()
            return self._handle_download_status(argument)

        if command in {"chat", "chat!"}:
            if not argument:
                return [
                    self._info_result(
                        "Chat usage",
                        "Use: lm chat <prompt> or lm chat <model_key> :: <prompt>",
                    )
                ]
            return self._handle_chat(argument)

        if command in {"load", "load!"}:
            if command == "load":
                return self._handle_load_picker(argument)
            return self._handle_load(argument)

        if command in {"unload", "unload!"}:
            if command == "unload":
                return [self._info_result("Unload model", "Use: lm unload! <instance_id>")]
            return self._handle_unload(argument)

        if command in {"download", "download!"}:
            if command == "download":
                return [self._info_result("Download model", "Use: lm download! <model_or_hf_url>")]
            return self._handle_download(argument)

        return [
            self._info_result(
                "Unknown command",
                "Use: models, chat, load, unload, download, status, help",
            )
        ] + self._help_results()

    def _help_results(self) -> List[Dict[str, Any]]:
        return [
            self._command_result("models", "List available models from LM Studio"),
            self._command_result("status", "Show loaded model(s), context length and runtime config"),
            self._command_result("chat ", "Start chat with default or auto-selected model"),
            self._command_result("load", "List models and press Enter to load selected"),
            self._command_result("load! ", "Direct load by model key"),
            self._command_result("unload! ", "Unload a model instance"),
            self._command_result("download! ", "Start model download"),
            self._command_result("status ", "Check download status by job_id"),
        ]

    def _handle_models(self) -> List[Dict[str, Any]]:
        payload, error = self._api_request("GET", "/api/v1/models")
        if error:
            return [self._error_result(error)]

        models = payload.get("models", []) if isinstance(payload, dict) else []
        if not models:
            return [self._info_result("No models found", "LM Studio returned an empty model list")]

        results: List[Dict[str, Any]] = [
            self._info_result(
                f"Found {len(models)} model(s)",
                "Select model and press Enter to load it",
            )
        ]

        for model in models[:30]:
            if not isinstance(model, dict):
                continue

            model_type = model.get("type", "unknown")
            display_name = model.get("display_name") or model.get("key") or "Unknown model"
            model_key = model.get("key", "")
            loaded_instances = model.get("loaded_instances") or []
            loaded_count = len(loaded_instances)
            size_text = self._human_size(model.get("size_bytes"))

            subtitle = (
                f"{model_type} | key: {model_key} | loaded: {loaded_count} | size: {size_text}"
            )
            results.append(
                {
                    "Title": display_name,
                    "SubTitle": subtitle + " | Enter: load model",
                    "IcoPath": self.icon_path,
                    "JsonRPCAction": {
                        "method": "load_model_action",
                        "parameters": [model_key],
                    },
                }
            )

        return results

    def _handle_load_picker(self, filter_text: str) -> List[Dict[str, Any]]:
        payload, error = self._api_request("GET", "/api/v1/models")
        if error:
            return [self._error_result(error)]

        models = payload.get("models", []) if isinstance(payload, dict) else []
        if not models:
            return [self._info_result("No models found", "LM Studio returned an empty model list")]

        normalized_filter = (filter_text or "").strip().lower()
        filtered_models: List[Dict[str, Any]] = []

        for model in models:
            if not isinstance(model, dict):
                continue
            key = str(model.get("key", ""))
            display_name = str(model.get("display_name") or key)
            if normalized_filter and normalized_filter not in key.lower() and normalized_filter not in display_name.lower():
                continue
            filtered_models.append(model)

        if not filtered_models:
            return [self._info_result("No matching models", f"Filter: {filter_text}")]

        results: List[Dict[str, Any]] = [
            self._info_result(
                f"Load model ({len(filtered_models)} found)",
                "Select model and press Enter to load",
            )
        ]

        for model in filtered_models[:30]:
            model_type = model.get("type", "unknown")
            display_name = model.get("display_name") or model.get("key") or "Unknown model"
            model_key = model.get("key", "")
            loaded_instances = model.get("loaded_instances") or []
            loaded_count = len(loaded_instances)
            size_text = self._human_size(model.get("size_bytes"))

            subtitle = (
                f"{model_type} | key: {model_key} | loaded: {loaded_count} | size: {size_text}"
            )

            results.append(
                {
                    "Title": display_name,
                    "SubTitle": subtitle + " | Enter: load model",
                    "IcoPath": self.icon_path,
                    "JsonRPCAction": {
                        "method": "load_model_action",
                        "parameters": [model_key],
                    },
                }
            )

        return results

    def load_model_action(self, model_key: str) -> bool:
        model_key = (model_key or "").strip()
        if not model_key:
            return False

        body: Dict[str, Any] = {"model": model_key}
        context_length = self._parse_int(self._setting("contextLength", ""), None)
        if context_length is not None and context_length > 0:
            body["context_length"] = context_length

        payload, error = self._api_request("POST", "/api/v1/models/load", body)
        if error is None:
            instance_id = payload.get("instance_id", model_key) if isinstance(payload, dict) else model_key
            if isinstance(instance_id, str) and instance_id.strip():
                self.last_model_key = instance_id.strip()
            else:
                self.last_model_key = model_key
        return error is None

    def _handle_chat(self, argument: str) -> List[Dict[str, Any]]:
        model, prompt, parse_error = self._parse_chat_input(argument)
        if parse_error:
            return [self._info_result("Chat input error", parse_error)]

        body: Dict[str, Any] = {
            "model": model,
            "input": prompt,
            "stream": False,
        }

        system_prompt = self._setting("systemPrompt", "").strip()
        if system_prompt:
            body["system_prompt"] = system_prompt

        temperature = self._parse_float(self._setting("temperature", ""), None)
        if temperature is not None:
            body["temperature"] = max(0.0, min(1.0, temperature))

        max_output_tokens = self._parse_int(self._setting("maxOutputTokens", ""), None)
        if max_output_tokens is not None and max_output_tokens > 0:
            body["max_output_tokens"] = max_output_tokens

        reasoning = self._setting("reasoning", "").strip().lower()
        if reasoning in {"off", "low", "medium", "high", "on"}:
            body["reasoning"] = reasoning

        context_length = self._parse_int(self._setting("contextLength", ""), None)
        if context_length is not None and context_length > 0:
            body["context_length"] = context_length

        payload, error = self._api_request("POST", "/api/v1/chat", body)
        if error:
            return [self._error_result(error)]

        self.last_model_key = model

        response_text = self._extract_chat_text(payload)
        preview = self._truncate(response_text.replace("\n", " "), 230)

        stats = payload.get("stats", {}) if isinstance(payload, dict) else {}
        subtitle_parts = [f"model: {model}"]
        total_output_tokens = stats.get("total_output_tokens")
        if isinstance(total_output_tokens, (int, float)):
            subtitle_parts.append(f"tokens: {int(total_output_tokens)}")
        tokens_per_second = stats.get("tokens_per_second")
        if isinstance(tokens_per_second, (int, float)):
            subtitle_parts.append(f"tps: {tokens_per_second:.2f}")

        results = [
            {
                "Title": f"Response ({model})",
                "SubTitle": preview + " | Enter: copy full response",
                "IcoPath": self.icon_path,
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [response_text],
                },
            },
            self._info_result(
                "Chat stats",
                " | ".join(subtitle_parts),
            ),
        ]

        raw_json = json.dumps(payload, ensure_ascii=True, indent=2)
        results.append(
            self._info_result(
                "Copy raw JSON response",
                "Enter: copy full LM Studio response JSON",
                raw_json,
            )
        )
        return results

    def _handle_load(self, model_key: str) -> List[Dict[str, Any]]:
        model_key = (model_key or "").strip()
        if not model_key:
            return [self._info_result("Usage", "lm load! <model_key>")]

        body: Dict[str, Any] = {"model": model_key}

        context_length = self._parse_int(self._setting("contextLength", ""), None)
        if context_length is not None and context_length > 0:
            body["context_length"] = context_length

        payload, error = self._api_request("POST", "/api/v1/models/load", body)
        if error:
            return [self._error_result(error)]

        instance_id = payload.get("instance_id", model_key)
        model_type = payload.get("type", "unknown")
        load_time = payload.get("load_time_seconds")

        if isinstance(instance_id, str) and instance_id.strip():
            self.last_model_key = instance_id.strip()
        else:
            self.last_model_key = model_key

        subtitle = f"type: {model_type}"
        if isinstance(load_time, (int, float)):
            subtitle += f" | load_time: {load_time:.2f}s"

        return [
            self._info_result(f"Loaded: {instance_id}", subtitle, str(instance_id)),
        ]

    def _handle_unload(self, instance_id: str) -> List[Dict[str, Any]]:
        instance_id = (instance_id or "").strip()
        if not instance_id:
            return [self._info_result("Usage", "lm unload! <instance_id>")]

        body = {"instance_id": instance_id}
        payload, error = self._api_request("POST", "/api/v1/models/unload", body)
        if error:
            return [self._error_result(error)]

        unloaded = payload.get("instance_id", instance_id)
        return [
            self._info_result(
                f"Unloaded: {unloaded}",
                "Model instance was unloaded from LM Studio",
                str(unloaded),
            )
        ]

    def _handle_download(self, model_name: str) -> List[Dict[str, Any]]:
        model_name = (model_name or "").strip()
        if not model_name:
            return [self._info_result("Usage", "lm download! <model_or_hf_url>")]

        body = {"model": model_name}
        payload, error = self._api_request("POST", "/api/v1/models/download", body)
        if error:
            return [self._error_result(error)]

        status = payload.get("status", "unknown")
        job_id = payload.get("job_id", "")

        subtitle = "Download request accepted"
        if job_id:
            subtitle = f"job_id: {job_id} | use: lm status {job_id}"
        elif status == "already_downloaded":
            subtitle = "Model is already downloaded"

        copy_value = job_id or model_name
        return [
            self._info_result(f"Download status: {status}", subtitle, str(copy_value)),
        ]

    def _handle_download_status(self, job_id: str) -> List[Dict[str, Any]]:
        encoded_job_id = quote(job_id.strip(), safe="")
        payload, error = self._api_request(
            "GET", f"/api/v1/models/download/status/{encoded_job_id}"
        )
        if error:
            return [self._error_result(error)]

        status = payload.get("status", "unknown")
        downloaded_bytes = payload.get("downloaded_bytes")
        total_size_bytes = payload.get("total_size_bytes")

        subtitle_parts = [f"job_id: {job_id}"]
        if isinstance(downloaded_bytes, (int, float)) and isinstance(total_size_bytes, (int, float)):
            subtitle_parts.append(
                f"{self._human_size(downloaded_bytes)} / {self._human_size(total_size_bytes)}"
            )
        elif isinstance(total_size_bytes, (int, float)):
            subtitle_parts.append(f"size: {self._human_size(total_size_bytes)}")

        return [
            self._info_result(
                f"Download status: {status}",
                " | ".join(subtitle_parts),
                json.dumps(payload, ensure_ascii=True, indent=2),
            )
        ]

    def _handle_runtime_status(self) -> List[Dict[str, Any]]:
        payload, error = self._api_request("GET", "/api/v1/models")
        if error:
            return [self._error_result(error)]

        models = payload.get("models", []) if isinstance(payload, dict) else []
        if not isinstance(models, list):
            return [self._error_result("Invalid response from LM Studio models endpoint")]

        loaded_results: List[Dict[str, Any]] = []

        for model in models:
            if not isinstance(model, dict):
                continue

            loaded_instances = model.get("loaded_instances") or []
            if not isinstance(loaded_instances, list) or not loaded_instances:
                continue

            display_name = str(model.get("display_name") or model.get("key") or "Unknown model")
            model_key = str(model.get("key") or "")

            for instance in loaded_instances:
                if isinstance(instance, dict):
                    instance_id = str(instance.get("id") or model_key)
                    raw_config = instance.get("config")
                    config: Dict[str, Any] = raw_config if isinstance(raw_config, dict) else {}
                else:
                    instance_id = str(instance)
                    config = {}

                context_length = config.get("context_length")
                eval_batch_size = config.get("eval_batch_size")
                flash_attention = config.get("flash_attention")
                offload_kv_cache_to_gpu = config.get("offload_kv_cache_to_gpu")

                subtitle_parts = [f"key: {model_key}"]
                if isinstance(context_length, int):
                    subtitle_parts.append(f"ctx: {context_length}")
                if isinstance(eval_batch_size, int):
                    subtitle_parts.append(f"batch: {eval_batch_size}")
                if isinstance(flash_attention, bool):
                    subtitle_parts.append(f"flash: {str(flash_attention).lower()}")
                if isinstance(offload_kv_cache_to_gpu, bool):
                    subtitle_parts.append(f"kv_gpu: {str(offload_kv_cache_to_gpu).lower()}")

                loaded_results.append(
                    self._info_result(
                        f"Loaded: {display_name}",
                        f"instance: {instance_id} | " + " | ".join(subtitle_parts),
                        instance_id,
                    )
                )

        if not loaded_results:
            return [
                self._info_result(
                    "No loaded models",
                    "Load a model first using: lm load",
                )
            ]

        summary = self._info_result(
            f"Loaded instances: {len(loaded_results)}",
            "Enter on an item copies its instance id",
        )
        return [summary] + loaded_results

    def _api_request(
        self, method: str, path: str, body: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        base_url = self._setting("baseUrl", "http://localhost:1234").strip()
        if not base_url:
            base_url = "http://localhost:1234"
        url = f"{base_url.rstrip('/')}{path}"

        headers = {"Content-Type": "application/json"}
        api_token = self._setting("apiToken", "").strip()
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"

        timeout = self._parse_float(self._setting("timeoutSeconds", "30"), 30.0)
        if timeout is None or timeout <= 0:
            timeout = 30.0

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            return (
                {},
                "Cannot reach LM Studio API. Check LM Studio server and baseUrl "
                f"({base_url}). Details: {exc}",
            )

        if response.status_code >= 400:
            detail = (response.text or "").strip()
            if len(detail) > 450:
                detail = detail[:447] + "..."
            return {}, f"HTTP {response.status_code}: {detail or response.reason}"

        if not response.text:
            return {}, None

        try:
            parsed = response.json()
        except ValueError:
            return {}, "LM Studio returned non-JSON response"

        if isinstance(parsed, dict):
            return parsed, None

        return {}, "LM Studio returned unexpected JSON format"

    def _parse_chat_input(self, argument: str) -> Tuple[str, str, Optional[str]]:
        raw = (argument or "").strip()
        if not raw:
            return "", "", "Usage: lm chat <prompt> or lm chat <model_key> :: <prompt>"

        default_model = self._setting("defaultModel", "").strip()
        detect_error: Optional[str] = None

        if "::" in raw:
            model_part, prompt_part = raw.split("::", 1)
            model = model_part.strip() or default_model
            prompt = prompt_part.strip()
        else:
            model = ""
            prompt = raw

        if not model:
            detected_model, detect_error = self._resolve_default_chat_model()
            if detected_model:
                model = detected_model

        if not model:
            if default_model:
                model = default_model

        if not model and self.last_model_key:
            model = self.last_model_key

        if not model:
            if detect_error:
                return "", "", detect_error
            return "", "", "No model available. Set defaultModel or load a model first."

        if not prompt:
            return "", "", "Prompt is empty"

        return model, prompt, None

    def _resolve_default_chat_model(self) -> Tuple[Optional[str], Optional[str]]:
        payload, error = self._api_request("GET", "/api/v1/models")
        if error:
            return None, f"Cannot determine model automatically: {error}"

        models = payload.get("models", []) if isinstance(payload, dict) else []
        if not isinstance(models, list):
            return None, "Cannot determine model automatically: invalid models response"

        first_llm_key: Optional[str] = None

        for model in models:
            if not isinstance(model, dict):
                continue
            if model.get("type") != "llm":
                continue

            model_key = model.get("key")
            if not isinstance(model_key, str) or not model_key.strip():
                continue

            if first_llm_key is None:
                first_llm_key = model_key

            loaded_instances = model.get("loaded_instances") or []
            if isinstance(loaded_instances, list) and loaded_instances:
                for instance in loaded_instances:
                    if isinstance(instance, dict):
                        instance_id = instance.get("id")
                        if isinstance(instance_id, str) and instance_id.strip():
                            return instance_id.strip(), None
                    elif isinstance(instance, str) and instance.strip():
                        return instance.strip(), None

        if first_llm_key:
            return first_llm_key, None

        return None, "No LLM models found in LM Studio"

    def _extract_chat_text(self, payload: Dict[str, Any]) -> str:
        output_items = payload.get("output", []) if isinstance(payload, dict) else []
        if not isinstance(output_items, list):
            return "LM Studio returned no output items"

        messages: List[str] = []
        tool_calls: List[str] = []

        for item in output_items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "message" and item.get("content"):
                messages.append(str(item["content"]).strip())
            elif item_type == "tool_call":
                tool_name = str(item.get("tool", "unknown_tool"))
                tool_calls.append(f"tool_call: {tool_name}")

        if messages:
            return "\n\n".join([msg for msg in messages if msg])

        if tool_calls:
            return "\n".join(tool_calls)

        return "LM Studio returned an empty response"

    def _split_query(self, text: str) -> Tuple[str, str]:
        parts = text.split(maxsplit=1)
        command = parts[0].strip().lower()
        argument = parts[1].strip() if len(parts) > 1 else ""
        return command, argument

    def _setting(self, key: str, default: str) -> str:
        settings = getattr(self, "settings", {})
        if not isinstance(settings, dict):
            return default
        value = settings.get(key)
        if value is None:
            return default
        return str(value)

    def _info_result(
        self, title: str, subtitle: str, copy_value: Optional[str] = None
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "Title": title,
            "SubTitle": subtitle,
            "IcoPath": self.icon_path,
        }
        if copy_value is not None:
            result["JsonRPCAction"] = {
                "method": "Flow.Launcher.CopyToClipboard",
                "parameters": [copy_value],
            }
        return result

    def _command_result(self, command_text: str, subtitle: str) -> Dict[str, Any]:
        full_query = f"lm {command_text}"
        return {
            "Title": command_text,
            "SubTitle": subtitle + " | Enter: autocomplete",
            "IcoPath": self.icon_path,
            "JsonRPCAction": {
                "method": "Flow.Launcher.ChangeQuery",
                "parameters": [full_query, False],
                "dontHideAfterAction": True,
            },
        }

    def _error_result(self, message: str) -> Dict[str, Any]:
        return {
            "Title": "LM Studio API error",
            "SubTitle": message,
            "IcoPath": self.icon_path,
        }

    def _human_size(self, value: Any) -> str:
        if not isinstance(value, (int, float)):
            return "n/a"
        size = float(value)
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if size < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)}{unit}"
                return f"{size:.2f}{unit}"
            size /= 1024
        return "n/a"

    def _parse_int(self, value: str, default: Optional[int]) -> Optional[int]:
        raw = (value or "").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def _parse_float(self, value: str, default: Optional[float]) -> Optional[float]:
        raw = (value or "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    def _truncate(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        if max_len <= 3:
            return text[:max_len]
        return text[: max_len - 3] + "..."


if __name__ == "__main__":
    LMStudioPlugin()
