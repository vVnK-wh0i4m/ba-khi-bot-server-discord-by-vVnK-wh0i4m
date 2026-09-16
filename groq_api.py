"""Client Groq async, đi qua rate limiter trước khi gọi mạng."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from ratelimit import LimiterRegistry

log = logging.getLogger("groq")

BASE_URL = "https://api.groq.com/openai/v1"


class GroqError(RuntimeError):
    pass


def estimate_tokens(text: str) -> int:
    """Ước lượng thô. Tiếng Việt có dấu tokenize nặng hơn tiếng Anh nhiều."""
    return max(1, int(len(text) / 2.5) + 4)


class GroqClient:
    def __init__(self, api_key: str, registry: LimiterRegistry, timeout: float = 25.0) -> None:
        self._registry = registry
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _post(self, payload: dict, attempts: int = 2) -> dict:
        last: Exception | None = None
        for i in range(attempts):
            try:
                resp = await self._http.post("/chat/completions", json=payload)
            except httpx.HTTPError as exc:
                last = exc
                await asyncio.sleep(0.8 * (i + 1))
                continue

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("retry-after", "2") or 2)
                log.warning("429 từ Groq (%s), chờ %.1fs", payload.get("model"), retry_after)
                if i + 1 >= attempts:
                    raise GroqError("rate limited")
                await asyncio.sleep(min(retry_after, 5.0))
                continue

            if resp.status_code >= 500:
                last = GroqError(f"HTTP {resp.status_code}")
                await asyncio.sleep(0.8 * (i + 1))
                continue

            if resp.status_code >= 400:
                raise GroqError(f"HTTP {resp.status_code}: {resp.text[:300]}")

            return resp.json()

        raise GroqError(str(last) if last else "unknown error")

    async def complete(
        self,
        model: str,
        messages: list[dict],
        *,
        max_tokens: Optional[int] = 256,
        temperature: float = 0.9,
        max_wait: float = 0.0,
        top_p: float = 0.95,
        max_input_tokens: int = 2500,
        reasoning_effort: Optional[str] = None,
    ) -> Optional[str]:
        """Trả về text, hoặc None nếu bị rate limit / hết quota ngày."""
        # cắt bớt lịch sử từ đầu (giữ system prompt + tin nhắn mới nhất) nếu
        # tổng ước lượng vượt trần — tránh 400 "reduce length of messages"
        # do free tier Groq giới hạn kích thước request nhỏ hơn nhiều so
        # với context window quảng cáo của model.
        if len(messages) > 2:
            system, *rest = messages
            while rest and len(rest) > 1:
                total = estimate_tokens(str(system.get("content", "")))
                total += sum(estimate_tokens(str(m.get("content", ""))) for m in rest)
                if total <= max_input_tokens:
                    break
                rest.pop(0)  # bỏ tin nhắn cũ nhất trong lịch sử
            messages = [system, *rest]

        est = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
        if max_tokens:
            est += max_tokens

        limiter = self._registry.get(model)
        reservation = await limiter.acquire(est, max_wait=max_wait)
        if reservation is None:
            log.info("bỏ qua request tới %s — hết slot rate limit", model)
            return None

        payload: dict = {"model": model, "messages": messages}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
            payload["temperature"] = temperature
            payload["top_p"] = top_p
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        try:
            data = await self._post(payload)
        except Exception:
            reservation.settle(est)  # coi như đã tiêu, tránh spam retry
            raise

        usage = data.get("usage") or {}
        reservation.settle(int(usage.get("total_tokens") or est))

        choices = data.get("choices") or []
        if not choices:
            return ""
        return (choices[0].get("message") or {}).get("content") or ""
