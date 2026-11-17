"""Deterministic fixture model. It never calls an LLM provider.

Only tests import this module. Canned markers verify orchestration, not legal quality.
"""

import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class FixtureChatModel(BaseChatModel):
    tool_names: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "offline-test-fixture"

    def bind_tools(self, tools, **kwargs):
        names = [t.name if hasattr(t, "name") else t["function"]["name"] for t in tools]
        return self.model_copy(update={"tool_names": names})

    def _generate(self, messages, stop=None, run_manager=None, **kwargs: Any):
        system = "\n".join(str(m.content) for m in messages if isinstance(m, SystemMessage)).lower()
        human = next((str(m.content) for m in reversed(messages) if isinstance(m, HumanMessage)), "")
        tools = [m for m in messages if isinstance(m, ToolMessage)]
        if "routing expert" in system:
            question = human.lower()
            content = json.dumps({
                "needs_tax": any(w in question for w in ("tax", "irs", "thuế")),
                "needs_compliance": any(w in question for w in ("compliance", "sec", "regulation")),
                "needs_privacy": any(w in question for w in ("data", "gdpr", "privacy", "dữ liệu")),
            })
        elif self.tool_names and not tools:
            name = self.tool_names[0]
            arg = "question" if name == "delegate_to_legal_agent" else "keywords" if name == "search_case_law" else "query"
            response = AIMessage(content="", tool_calls=[{
                "name": name, "args": {arg: human}, "id": "fixture-tool-1", "type": "tool_call",
            }])
            return ChatResult(generations=[ChatGeneration(message=response)])
        elif tools:
            content = "[FIXTURE:TOOL_RESULT]\n" + "\n".join(str(m.content) for m in tools)
        elif "synthesising" in system or "tổng hợp" in human.lower():
            content = "[FIXTURE:AGGREGATE]\n" + human
        elif "specialist tax" in system or "chuyên gia thuế" in human.lower():
            content = "[FIXTURE:TAX] Canned tax response, not legal advice."
        elif "compliance officer" in system or "chuyên gia compliance" in human.lower():
            content = "[FIXTURE:COMPLIANCE] Canned compliance response."
        elif human.lower().startswith("bạn là chuyên gia về gdpr"):
            content = "[FIXTURE:PRIVACY] Canned privacy response."
        else:
            content = "[FIXTURE:LAW] Canned general-law response."
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


def get_test_llm(*args, **kwargs):
    return FixtureChatModel()
