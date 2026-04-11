from verifier.rules._shared import check_no_percent

CONSTRAINT_ID = "FH-8"
PARAM_NAMES = []

def check(response_text, params, context=None, meta=None):
    return check_no_percent(CONSTRAINT_ID, response_text, params)
