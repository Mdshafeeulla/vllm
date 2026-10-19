# core/llm.py
import os
import ollama
from core.config import cfg
from utils.logger import log

_client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))


def _select_history(history: list[dict] | None, token_budget: int) -> list[dict]:
    """Keep the newest complete chat turns that fit a rough token budget."""
    valid_messages = [
        {"role": message["role"], "content": message["content"]}
        for message in (history or [])
        if message.get("role") in {"user", "assistant"}
        and isinstance(message.get("content"), str)
    ]
    turns = []
    for index in range(0, len(valid_messages) - 1, 2):
        user_message, assistant_message = valid_messages[index:index + 2]
        if user_message["role"] == "user" and assistant_message["role"] == "assistant":
            turns.append((user_message, assistant_message))

    remaining_chars = max(0, token_budget) * 4
    selected_turns = []
    for user_message, assistant_message in reversed(turns):
        turn_size = len(user_message["content"]) + len(assistant_message["content"])
        if turn_size <= remaining_chars:
            selected_turns.append((user_message, assistant_message))
            remaining_chars -= turn_size
            continue

        if not selected_turns and remaining_chars:
            user_chars = min(len(user_message["content"]), remaining_chars // 2)
            trimmed_user = {
                **user_message,
                "content": user_message["content"][:user_chars],
            }
            assistant_chars = remaining_chars - user_chars
            trimmed_assistant = {
                **assistant_message,
                "content": assistant_message["content"][:assistant_chars],
            }
            selected_turns.append((trimmed_user, trimmed_assistant))
        break

    return [
        message
        for turn in reversed(selected_turns)
        for message in turn
    ]


def ask_llm(
    prompt: str,
    model: str = None,
    stream: bool = False,
    history: list[dict] = None,
    num_ctx: int = None,
):
    """
    Send a prompt to an Ollama model.

    Args:
        prompt : the full prompt string
        model  : Ollama model name (defaults to cfg.ollama_model)
        stream : if True, returns a generator yielding token chunks

    Returns:
        str (if stream=False) or generator (if stream=True)
    """
    model = model or cfg.ollama_model
    num_ctx = num_ctx or cfg.ollama_num_ctx
    messages = _select_history(history, token_budget=num_ctx * 15 // 100)
    messages.append({"role": "user", "content": prompt})
    options = {"num_ctx": num_ctx}

    try:
        if stream:
            return _stream_response(model, messages, options)
        response = _client.chat(
            model=model,
            messages=messages,
            options=options,
            keep_alive="24h",
        )
    except Exception as e:
        log.error(f"LLM call failed (model={model}): {e}")
        raise RuntimeError(
            f"Could not reach Ollama model '{model}'. "
            f"Is Ollama running? Have you pulled the model?\n"
            f"Try: ollama pull {model}"
        ) from e
    return response["message"]["content"]


def _stream_response(model: str, messages: list[dict], options: dict):
    try:
        response = _client.chat(
            model=model,
            messages=messages,
            stream=True,
            options=options,
            keep_alive="24h",
        )
        for chunk in response:
            yield chunk["message"]["content"]
    except Exception as e:
        log.error(f"LLM call failed (model={model}): {e}")
        raise RuntimeError(
            f"Could not reach Ollama model '{model}'. "
            f"Is Ollama running? Have you pulled the model?\n"
            f"Try: ollama pull {model}"
        ) from e


def prewarm_model(model: str = None, num_ctx: int = None):
    """
    Pre-load model weights into VRAM/RAM so the user doesn't wait on cold-start.
    """
    model = model or cfg.ollama_model
    num_ctx = num_ctx or cfg.ollama_num_ctx
    try:
        log.info(f"[LLM] Pre-warming model '{model}' in VRAM/RAM...")
        _client.chat(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            options={"num_ctx": num_ctx},
            keep_alive="24h",
        )
        log.info(f"[LLM] Model '{model}' pre-warmed ✓")
    except Exception as e:
        log.warning(f"[LLM] Could not pre-warm model '{model}': {e}")
