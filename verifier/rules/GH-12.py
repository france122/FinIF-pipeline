from verifier.rules._shared import check_checkbox
CONSTRAINT_ID = "GH-12"
PARAM_NAMES = []
def check(response_text, params, context=None, meta=None):
    return check_checkbox(CONSTRAINT_ID, response_text, params)
