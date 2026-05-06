from verifier.rules._shared import check_no_list

CONSTRAINT_ID = "GH-19"
PARAM_NAMES = []

def check(response_text, params, context=None, meta=None):
    return check_no_list(CONSTRAINT_ID, response_text, params)
