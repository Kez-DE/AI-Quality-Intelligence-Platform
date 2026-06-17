from .model_router import chat_completion, get_agent_status


def run_chat_agent(*args, **kwargs):
    # Lazy import avoids a circular import when worker modules load
    # agents.common -> agent.model_router.
    from .chat_agent import run_chat_agent as _run_chat_agent

    return _run_chat_agent(*args, **kwargs)

__all__ = ["chat_completion", "get_agent_status", "run_chat_agent"]
