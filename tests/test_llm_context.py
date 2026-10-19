from core.llm import _select_history, ask_llm
from core.pipeline import query_department
from core.prompt_builder import build_prompt


def test_history_keeps_most_recent_complete_turns_within_budget():
    history = [
        {"role": "user", "content": "older question"},
        {"role": "assistant", "content": "older answer"},
        {"role": "user", "content": "recent question"},
        {"role": "assistant", "content": "recent answer"},
    ]

    selected = _select_history(history, token_budget=8)

    assert selected == history[-2:]


def test_history_truncates_latest_turn_when_it_exceeds_budget():
    history = [
        {"role": "user", "content": "Question " * 20},
        {"role": "assistant", "content": "Answer " * 100},
    ]

    selected = _select_history(history, token_budget=10)

    assert [message["role"] for message in selected] == ["user", "assistant"]
    assert sum(len(message["content"]) for message in selected) <= 40


def test_rag_prompt_caps_document_context_but_keeps_query():
    chunks = [
        {"source": "guide.pdf", "score": 0.9, "text": "document text " * 500}
    ]

    prompt = build_prompt(
        chunks,
        "What is the approval process?",
        max_context_tokens=50,
    )

    assert "What is the approval process?" in prompt
    assert "Document context truncated" in prompt


def test_rag_prompt_uses_documents_as_internal_knowledge_for_direct_support():
    prompt = build_prompt(
        [{"source": "guide.pdf", "score": 0.9, "text": "Click Settings, then Members."}],
        "How do I add a member?",
    )

    assert "synthesize the relevant information" in prompt
    assert "give the necessary steps" in prompt
    assert "do not mention document names" in prompt
    assert "Do not invent instructions" in prompt
    assert "support@msucorp.com" not in prompt
    assert "According to Support Doc" not in prompt


def test_followup_email_anchors_above_to_the_previous_question(monkeypatch):
    call = {}

    def fake_ask_llm(prompt, **kwargs):
        call["prompt"] = prompt
        call.update(kwargs)
        return "Subject: About NABARD\n\n..."

    monkeypatch.setattr("core.pipeline.ask_llm", fake_ask_llm)
    history = [
        {"role": "user", "content": "How do I add a member?"},
        {"role": "assistant", "content": "Open Settings, then Members."},
        {"role": "user", "content": "what is nabard"},
        {
            "role": "assistant",
            "content": "NABARD is an apex development bank in India. "
            "It created the Rural Tech Innovation Platform.",
        },
    ]

    result = query_department(
        "make an email for above to send",
        department="it",
        model="mistral",
        history=history,
    )

    assert result["answer"].startswith("Subject: About NABARD")
    assert "Prior user question:\nwhat is nabard" in call["prompt"]
    assert "Prior assistant answer:\nNABARD is an apex development bank" in call["prompt"]
    assert "not only a platform mentioned" in call["prompt"]
    assert "Never imply an email has already been sent" in call["prompt"]
    assert "neutral informational email" in call["prompt"]
    assert "Do not infer a request for collaboration" in call["prompt"]
    assert "omit the related platform, Hackathon, and Sandbox" in call["prompt"]
    assert "without embellishing them" in call["prompt"]
    assert call["history"] is None


def test_ask_llm_uses_selected_context_window_and_chat_history(monkeypatch):
    class FakeClient:
        call = None

        def chat(self, **kwargs):
            self.call = kwargs
            return {"message": {"content": "answer"}}

    fake_client = FakeClient()
    monkeypatch.setattr("core.llm._client", fake_client)
    history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]

    answer = ask_llm(
        "Current question",
        model="test-model",
        history=history,
        num_ctx=4096,
    )

    assert answer == "answer"
    assert fake_client.call["options"]["num_ctx"] == 4096
    assert fake_client.call["messages"] == [
        *history,
        {"role": "user", "content": "Current question"},
    ]
