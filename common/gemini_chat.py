"""Preserve Gemini tool-call metadata with the pinned LangChain OpenAI adapter.

langchain-openai 0.3.28 retains raw tool calls in AIMessage.additional_kwargs,
but its outgoing converter rebuilds calls without Google's extra_content.
Gemini requires the original thought_signature on the next tool-result turn.
"""

from copy import deepcopy

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI


class GeminiChatOpenAI(ChatOpenAI):
    """OpenAI-compatible Gemini client that round-trips signed tool calls."""

    def _get_request_payload(self, input_, *, stop=None, **kwargs):
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        messages = self._convert_input(input_).to_messages()
        for message, outgoing in zip(messages, payload.get("messages", [])):
            if not isinstance(message, AIMessage):
                continue
            raw_by_id = {
                call.get("id"): call
                for call in message.additional_kwargs.get("tool_calls", [])
            }
            for call in outgoing.get("tool_calls", []):
                raw = raw_by_id.get(call.get("id"), {})
                if "extra_content" in raw:
                    call["extra_content"] = deepcopy(raw["extra_content"])
        return payload
