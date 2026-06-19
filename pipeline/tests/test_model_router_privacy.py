from unittest.mock import patch

from agent import model_router


def test_chat_completion_redacts_pii_before_provider_and_log(tmp_path):
    messages = [
        {
            "role": "user",
            "content": "Liên hệ 0912345678, xe 30A-12345, email khach@gmail.com",
        }
    ]

    with (
        patch.object(model_router, "resolve_provider_chain", return_value=["openai"]),
        patch.object(model_router, "provider_model", return_value="test-model"),
        patch.object(
            model_router,
            "_call_provider",
            return_value=({"role": "assistant", "content": "ok"}, {}),
        ) as provider,
        patch.object(model_router, "write_agent_log") as write_log,
    ):
        model_router.chat_completion(messages)

    outbound = provider.call_args.args[1][0]["content"]
    assert "0912345678" not in outbound
    assert "30A-12345" not in outbound
    assert "khach@gmail.com" not in outbound
    assert "[SĐT_ĐÃ_ẨN]" in outbound
    assert "[BIỂN_SỐ_ĐÃ_ẨN]" in outbound
    assert "[EMAIL_ĐÃ_ẨN]" in outbound

    preview = write_log.call_args.args[0]["prompt_preview"]
    assert "0912345678" not in preview
    assert "30A-12345" not in preview
    assert "khach@gmail.com" not in preview

    # Hàm không được sửa lịch sử chat mà API đang giữ trong request hiện tại.
    assert "0912345678" in messages[0]["content"]
