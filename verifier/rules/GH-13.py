from verifier.rules._shared import check_code_or_formula
CONSTRAINT_ID = "GH-13"
PARAM_NAMES = []
def check(response_text, params, context=None, meta=None):
    return check_code_or_formula(CONSTRAINT_ID, response_text, params)
