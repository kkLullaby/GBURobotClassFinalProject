"""Echo backend abstraction for the H018 spike."""

from typing import Any, AsyncIterator, List, Protocol


class TextBackend(Protocol):
    async def stream_response(
        self,
        messages: List[Any],
        model: str,
    ) -> AsyncIterator[str]:
        """Yield text deltas for a chat completion."""


def _message_role(message: Any) -> str:
    if isinstance(message, dict):
        return str(message.get("role", ""))
    return str(getattr(message, "role", ""))


def _message_content(message: Any) -> str:
    if isinstance(message, dict):
        content = message.get("content", "")
    else:
        content = getattr(message, "content", "")
    return content if isinstance(content, str) else ""


def _chunk_text(text: str, size: int = 20) -> List[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


class EchoBackend:
    """Echo the last user message as small text deltas."""

    async def stream_response(
        self,
        messages: List[Any],
        model: str,
    ) -> AsyncIterator[str]:
        del model
        user_text = ""
        for message in reversed(messages):
            if _message_role(message) == "user":
                user_text = _message_content(message)
                break

        for chunk in _chunk_text("echoed: " + user_text):
            yield chunk
