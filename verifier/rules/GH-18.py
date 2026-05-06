from verifier.rules._shared import check_no_table

CONSTRAINT_ID = "GH-18"
PARAM_NAMES = []

def check(response_text, params, context=None, meta=None):
    return check_no_table(CONSTRAINT_ID, response_text, params)
