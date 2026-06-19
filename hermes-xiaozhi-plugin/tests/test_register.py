from unittest.mock import MagicMock

from hermes_xiaozhi import register


def test_register_calls_ctx_register_platform():
    ctx = MagicMock()

    register(ctx)

    ctx.register_platform.assert_called_once()
    kw = ctx.register_platform.call_args.kwargs
    assert kw["name"] == "xiaozhi"
    assert kw["label"] == "XiaoZhi"
    assert callable(kw["adapter_factory"])
    assert kw["check_fn"]() is True
    assert "XIAOZHI_WEBHOOK_PORT" in kw["required_env"]
    assert "XIAOZHI_WEBHOOK_SECRET" in kw["required_env"]
