"""
LLM client with three backends behind one interface: Ollama (local,
default — matches the capstone brief's zero-cloud-dependency
requirement), Groq (optional cloud), and Gemini (optional cloud).

Every caller in the codebase (pipeline.py, main.py) just does
LLMClient(api_key).chat(...) / .chat_json(...) — which provider actually
handles that call is decided once, from config.LLM_PROVIDER, not by the
caller. Switching providers is an environment variable, not a code change.

When LLM_PROVIDER=groq, the fallback chain is: GROQ_MODEL ->
GROQ_FALLBACK_MODEL -> (if GEMINI_API_KEY is set) Gemini, as a second
fallback so a Groq outage or exhausted quota doesn't take the app down
entirely. This only kicks in once both Groq models have failed.
"""

import json
import os
import re
import time

import requests

from config import (
    DEFAULT_TEMPERATURE,
    GEMINI_FALLBACK_MODEL,
    GEMINI_MODEL,
    LLM_PROVIDER,
    MAX_TOKENS,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SECONDS,
)

MAX_RATE_LIMIT_RETRIES = 4
DEFAULT_RETRY_SECONDS = 2.0
# A wait this long means a bigger Groq quota is exhausted, not a brief
# per-minute burst. Actually sleeping that long inside a background task
# would leave a generation hanging for most of a demo, so past this cap
# we fail fast with a clear message instead of blocking.
MAX_ACCEPTABLE_WAIT_SECONDS = 10.0


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, api_key: str | None, on_retry=None, provider: str | None = None):
        self.provider = (provider or LLM_PROVIDER).strip().lower()
        self.on_retry = on_retry
        self.api_key = api_key

        self._groq_client = None
        if self.provider == "groq":
            if api_key:
                from groq import Groq  # imported lazily so Ollama-only setups don't need the package
                self._groq_client = Groq(api_key=api_key)

        self._gemini_client = None
        if self.provider == "gemini":
            if api_key:
                from google import genai  # imported lazily so Ollama/Groq-only setups don't need the package
                self._gemini_client = genai.Client(api_key=api_key)

    def is_ready(self) -> bool:
        if self.provider == "ollama":
            return self._ollama_reachable()
        if self.provider == "gemini":
            return self._gemini_client is not None
        return self._groq_client is not None

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = DEFAULT_TEMPERATURE,
              json_mode: bool = False) -> str:
        if self.provider == "ollama":
            return self._chat_ollama(system_prompt, user_prompt, temperature, json_mode)
        if self.provider == "gemini":
            return self._chat_gemini(self._gemini_client, system_prompt, user_prompt, temperature, json_mode)
        return self._chat_groq(system_prompt, user_prompt, temperature, json_mode)

    def chat_json(self, system_prompt: str, user_prompt: str, temperature: float = DEFAULT_TEMPERATURE) -> dict:
        raw = self.chat(system_prompt, user_prompt, temperature=temperature, json_mode=True)
        return safe_parse_json(raw)

    def _ollama_reachable(self) -> bool:
        try:
            resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _chat_ollama(self, system_prompt: str, user_prompt: str, temperature: float, json_mode: bool) -> str:
        if not self._ollama_reachable():
            raise LLMError(
                f"Could not reach Ollama at {OLLAMA_BASE_URL}. Make sure it's running "
                f"(`ollama serve`) and the model is pulled (`ollama pull {OLLAMA_MODEL}`)."
            )

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": MAX_TOKENS,
            },
        }
        if json_mode:
            payload["format"] = "json"

        try:
            resp = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT_SECONDS
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(
                f"Lost connection to Ollama at {OLLAMA_BASE_URL}. Is `ollama serve` still running? "
                f"({exc})"
            )
        except requests.exceptions.Timeout:
            raise LLMError(
                f"Ollama did not respond within {OLLAMA_TIMEOUT_SECONDS}s. CPU-only inference on a "
                f"larger model can be slow — try a smaller model (e.g. phi3) or raise "
                f"OLLAMA_TIMEOUT_SECONDS."
            )
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text[:300] if exc.response is not None else str(exc)
            raise LLMError(f"Ollama returned an error: {body}")
        except (KeyError, ValueError) as exc:
            raise LLMError(f"Unexpected response from Ollama: {exc}")

    def _chat_gemini(self, client, system_prompt: str, user_prompt: str, temperature: float, json_mode: bool) -> str:
        from google.genai import errors as genai_errors
        from google.genai import types as genai_types

        if client is None:
            raise LLMError(
                "No Gemini API key configured. Set GEMINI_API_KEY as an environment "
                "variable, or provide one from the app's settings panel."
            )

        config_kwargs = dict(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=MAX_TOKENS,
        )
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        generation_config = genai_types.GenerateContentConfig(**config_kwargs)

        models_to_try = [GEMINI_MODEL, GEMINI_FALLBACK_MODEL]
        last_error = None

        for model in models_to_try:
            attempt = 0
            while attempt <= MAX_RATE_LIMIT_RETRIES:
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=user_prompt,
                        config=generation_config,
                    )
                    if not response.text:
                        raise LLMError(f"Gemini returned an empty response from {model}.")
                    return response.text

                except genai_errors.ClientError as exc:
                    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                    is_rate_limited = status_code == 429 or "RESOURCE_EXHAUSTED" in str(exc)
                    if not is_rate_limited:
                        # Non-rate-limit client error (bad key, bad model name, etc.) —
                        # no point retrying the same request.
                        last_error = exc
                        break

                    last_error = exc
                    wait_seconds = _retry_wait_seconds(exc)

                    if wait_seconds > MAX_ACCEPTABLE_WAIT_SECONDS:
                        message = (
                            f"{model} needs {wait_seconds / 60:.1f} min before it has "
                            f"quota again — skipping straight to the fallback model "
                            f"instead of waiting."
                        )
                        print(f"[LLMClient] {message}")
                        if self.on_retry:
                            try:
                                self.on_retry(message)
                            except Exception:  # noqa: BLE001
                                pass
                        break

                    attempt += 1
                    if attempt > MAX_RATE_LIMIT_RETRIES:
                        break
                    message = (
                        f"Rate limited on {model}, waiting {wait_seconds:.1f}s "
                        f"and retrying (attempt {attempt}/{MAX_RATE_LIMIT_RETRIES})..."
                    )
                    print(f"[LLMClient] {message}")
                    if self.on_retry:
                        try:
                            self.on_retry(message)
                        except Exception:  # noqa: BLE001
                            pass
                    time.sleep(wait_seconds)
                    continue

                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    break

        raise LLMError(
            f"All Gemini model attempts failed, including after retrying rate limits. "
            f"Last error: {last_error}"
        )

    def _chat_groq(self, system_prompt: str, user_prompt: str, temperature: float, json_mode: bool) -> str:
        import groq
        from config import GROQ_FALLBACK_MODEL, GROQ_MODEL

        if self._groq_client is None:
            raise LLMError(
                "No Groq API key configured. Set GROQ_API_KEY as an environment "
                "variable, or provide one from the app's settings panel."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        models_to_try = [GROQ_MODEL, GROQ_FALLBACK_MODEL]
        last_error = None

        for model in models_to_try:
            attempt = 0
            while attempt <= MAX_RATE_LIMIT_RETRIES:
                try:
                    kwargs = dict(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=MAX_TOKENS,
                    )
                    if json_mode:
                        kwargs["response_format"] = {"type": "json_object"}
                    completion = self._groq_client.chat.completions.create(**kwargs)
                    return completion.choices[0].message.content

                except groq.RateLimitError as exc:
                    last_error = exc
                    wait_seconds = _retry_wait_seconds(exc)

                    if wait_seconds > MAX_ACCEPTABLE_WAIT_SECONDS:
                        message = (
                            f"{model} needs {wait_seconds / 60:.1f} min before it has "
                            f"quota again — skipping straight to the fallback model "
                            f"instead of waiting."
                        )
                        print(f"[LLMClient] {message}")
                        if self.on_retry:
                            try:
                                self.on_retry(message)
                            except Exception:  # noqa: BLE001
                                pass
                        break

                    attempt += 1
                    if attempt > MAX_RATE_LIMIT_RETRIES:
                        break
                    message = (
                        f"Rate limited on {model}, waiting {wait_seconds:.1f}s "
                        f"and retrying (attempt {attempt}/{MAX_RATE_LIMIT_RETRIES})..."
                    )
                    print(f"[LLMClient] {message}")
                    if self.on_retry:
                        try:
                            self.on_retry(message)
                        except Exception:  # noqa: BLE001
                            pass
                    time.sleep(wait_seconds)
                    continue

                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    break

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            message = (
                "Both Groq models failed — falling back to Gemini "
                f"({GEMINI_MODEL})."
            )
            print(f"[LLMClient] {message}")
            if self.on_retry:
                try:
                    self.on_retry(message)
                except Exception:  # noqa: BLE001
                    pass
            try:
                return self._chat_gemini(
                    self._gemini_fallback_client(gemini_key), system_prompt, user_prompt, temperature, json_mode
                )
            except LLMError as gemini_exc:
                last_error = f"{last_error} | Gemini fallback also failed: {gemini_exc}"

        if isinstance(last_error, groq.RateLimitError):
            wait_hint = _retry_wait_seconds(last_error)
            if wait_hint > MAX_ACCEPTABLE_WAIT_SECONDS:
                raise LLMError(
                    f"Both Groq models are rate-limited on this Groq API key, and "
                    f"the quota needs roughly {wait_hint / 60:.0f} more minute(s) "
                    f"to reset. Wait and try again, use a different Groq API key "
                    f"in Settings, or set GEMINI_API_KEY to enable the Gemini "
                    f"fallback."
                )

        raise LLMError(
            f"All model attempts failed (Groq primary, Groq fallback"
            f"{', Gemini fallback' if gemini_key else ''}), including after "
            f"retrying rate limits. Last error: {last_error}"
        )

    def _gemini_fallback_client(self, api_key: str):
        """Lazily builds (and caches) a Gemini client used only as the
        second fallback after both Groq models fail. Kept separate from
        self._gemini_client, which is only populated when LLM_PROVIDER is
        actually "gemini"."""
        if getattr(self, "_gemini_fallback", None) is None:
            from google import genai  # imported lazily so Groq-only setups don't need the package
            self._gemini_fallback = genai.Client(api_key=api_key)
        return self._gemini_fallback


def _retry_wait_seconds(exc) -> float:
    try:
        response = getattr(exc, "response", None)
        if response is not None:
            retry_after = response.headers.get("retry-after")
            if retry_after:
                return max(float(retry_after), 0.1)
    except Exception:  # noqa: BLE001
        pass

    message = str(exc)
    match = re.search(r"try again in ([\d.]+)ms", message)
    if match:
        return max(float(match.group(1)) / 1000.0, 0.1)

    match = re.search(r"try again in ([\d.]+)s", message)
    if match:
        return max(float(match.group(1)), 0.1)

    return DEFAULT_RETRY_SECONDS


def safe_parse_json(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise LLMError(f"Could not parse JSON from model output:\n{raw[:500]}")
