from verifier.rules._shared import check_contains_phrase


CONSTRAINT_ID = "FH-1"
PARAM_NAMES = ['risk_line']


def check(response_text, params, context=None, meta=None):
    # 检查 response 末尾部分是否包含风险提示声明
    # 取最后 200 字检查，避免声明在中间出现也算通过
    tail = response_text[-200:] if len(response_text) > 200 else response_text
    phrase = params.get("risk_line", "")
    if phrase and phrase in tail:
        from verifier.base import result_pass
        return result_pass(CONSTRAINT_ID, f"末尾包含风险提示: {phrase[:30]}...")
    from verifier.base import result_fail
    return result_fail(CONSTRAINT_ID, "末尾未包含风险提示声明")
