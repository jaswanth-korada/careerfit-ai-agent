import json
import logging
import os
import re
import time
from typing import Any, Optional, Type, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

PROMPT_VERSION = "v3"
logger = logging.getLogger("careerfit.llm")

ModelT = TypeVar("ModelT", bound=BaseModel)

MODEL_ROUTING = {
    "jd_classifier": "openai",
    "ats_keyword_agent": "openai",
    "resume_match_agent": "openai",
    "truthfulness_guardrail": "claude",
    "resume_tailor": "claude",
    "interview_prep": "claude",
    "synthesis_agent": "claude",
    "self_critique_agent": "claude",
}

PROVIDER_ALIASES = {
    "anthropic": "claude",
    "claude": "claude",
    "openai": "openai",
}


class LLMError(RuntimeError):
    pass


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class StructuredLLMClient:
    def __init__(self) -> None:
        configured_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
        self.configured_provider = configured_provider
        if configured_provider:
            self.provider = PROVIDER_ALIASES.get(configured_provider, configured_provider)
        elif os.getenv("OPENAI_API_KEY"):
            self.provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            self.provider = "claude"
        else:
            self.provider = "fallback"

        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
        self.enable_multi_model = env_bool("ENABLE_MULTI_MODEL", True)
        self.enable_cross_model_critique = env_bool("ENABLE_CROSS_MODEL_CRITIQUE", True)

    def generate(
        self,
        *,
        schema: Type[ModelT],
        system_prompt: str,
        user_prompt: str,
        fallback: ModelT,
        route: str | None = None,
    ) -> ModelT:
        provider_order = self._provider_order(route)
        logger.info(
            "llm_generate_start schema=%s route=%s provider_order=%s prompt_version=%s system_chars=%s user_chars=%s",
            schema.__name__,
            route or "default",
            provider_order,
            PROMPT_VERSION,
            len(system_prompt),
            len(user_prompt),
        )
        if not provider_order:
            logger.info(
                "llm_generate_fallback schema=%s route=%s reason=no_available_provider",
                schema.__name__,
                route or "default",
            )
            return fallback

        errors: list[str] = []
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=True)
        fallback_triggered = False

        for provider_index, provider in enumerate(provider_order):
            if provider_index > 0:
                fallback_triggered = True
                logger.warning(
                    "llm_provider_fallback_triggered schema=%s route=%s from=%s to=%s",
                    schema.__name__,
                    route or "default",
                    provider_order[provider_index - 1],
                    provider,
                )

            prompt = (
                f"{user_prompt}\n\n"
                "Return one valid JSON object only. Do not include markdown fences, commentary, or extra keys.\n"
                f"Validate against this JSON schema:\n{schema_json}"
            )

            for attempt in range(self.max_retries + 1):
                start = time.perf_counter()
                try:
                    logger.info(
                        "llm_attempt schema=%s route=%s provider=%s model=%s attempt=%s max_retries=%s prompt_version=%s",
                        schema.__name__,
                        route or "default",
                        provider,
                        self._model_name(provider),
                        attempt + 1,
                        self.max_retries,
                        PROMPT_VERSION,
                    )
                    raw, usage = self._complete(provider, system_prompt, prompt)
                    data = self._extract_json(raw)
                    validated = schema.model_validate(data)
                    latency_ms = round((time.perf_counter() - start) * 1000)
                    logger.info(
                        "llm_generate_success schema=%s route=%s provider=%s model=%s attempt=%s latency_ms=%s usage=%s fallback_triggered=%s",
                        schema.__name__,
                        route or "default",
                        provider,
                        self._model_name(provider),
                        attempt + 1,
                        latency_ms,
                        usage,
                        fallback_triggered,
                    )
                    return validated
                except Exception as exc:
                    latency_ms = round((time.perf_counter() - start) * 1000)
                    errors.append(f"{provider} attempt {attempt + 1}: {exc}")
                    logger.warning(
                        "llm_validation_failure schema=%s route=%s provider=%s model=%s attempt=%s latency_ms=%s error=%s",
                        schema.__name__,
                        route or "default",
                        provider,
                        self._model_name(provider),
                        attempt + 1,
                        latency_ms,
                        exc,
                    )
                    prompt = (
                        f"{user_prompt}\n\n"
                        "The previous response failed validation. Return corrected JSON only, with no markdown.\n"
                        f"Validation errors: {' | '.join(errors[-2:])}\n"
                        f"Schema: {schema_json}"
                    )

        logger.error(
            "llm_generate_exhausted schema=%s route=%s provider_order=%s errors=%s",
            schema.__name__,
            route or "default",
            provider_order,
            " | ".join(errors),
        )
        return fallback

    def _provider_order(self, route: str | None) -> list[str]:
        if self.provider in {"fallback", "mock", "none", "off"}:
            return []

        if not self.enable_multi_model or not route:
            provider = PROVIDER_ALIASES.get(self.provider, self.provider)
            return [provider] if self._provider_configured(provider) else []

        preferred = PROVIDER_ALIASES.get(MODEL_ROUTING.get(route, self.provider), self.provider)
        secondary = "claude" if preferred == "openai" else "openai"
        ordered = []
        for provider in [preferred, secondary]:
            if provider not in ordered and self._provider_configured(provider):
                ordered.append(provider)
        return ordered

    def _provider_configured(self, provider: str) -> bool:
        if provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
        if provider == "claude":
            return bool(os.getenv("ANTHROPIC_API_KEY"))
        return False

    def _model_name(self, provider: str) -> str:
        if provider == "openai":
            return self.openai_model
        if provider == "claude":
            return self.anthropic_model
        return provider

    def _complete(self, provider: str, system_prompt: str, user_prompt: str) -> tuple[str, dict[str, Any]]:
        if provider == "openai":
            return self._complete_openai(system_prompt, user_prompt)
        if provider == "claude":
            return self._complete_anthropic(system_prompt, user_prompt)
        raise LLMError(f"Unsupported LLM provider '{provider}'.")

    def _complete_openai(self, system_prompt: str, user_prompt: str) -> tuple[str, dict[str, Any]]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("Install the openai package or set LLM_PROVIDER=fallback.") from exc

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=self.openai_model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content: Optional[str] = response.choices[0].message.content
        if not content:
            raise LLMError("OpenAI returned an empty response.")
        usage_obj = getattr(response, "usage", None)
        usage = {
            "input_tokens": getattr(usage_obj, "prompt_tokens", None),
            "output_tokens": getattr(usage_obj, "completion_tokens", None),
            "total_tokens": getattr(usage_obj, "total_tokens", None),
        }
        return content, usage

    def _complete_anthropic(self, system_prompt: str, user_prompt: str) -> tuple[str, dict[str, Any]]:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise LLMError("Install the anthropic package or set LLM_PROVIDER=fallback.") from exc

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=self.anthropic_model,
            temperature=self.temperature,
            max_tokens=3000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        content = "\n".join(parts).strip()
        if not content:
            raise LLMError("Anthropic returned an empty response.")
        usage_obj = getattr(response, "usage", None)
        usage = {
            "input_tokens": getattr(usage_obj, "input_tokens", None),
            "output_tokens": getattr(usage_obj, "output_tokens", None),
            "total_tokens": None,
        }
        if usage["input_tokens"] is not None and usage["output_tokens"] is not None:
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
        return content, usage

    def _extract_json(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            parsed = json.loads(cleaned[start : end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("LLM response must be a JSON object.")
        return parsed


llm_client = StructuredLLMClient()
