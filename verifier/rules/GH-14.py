from verifier.rules._shared import check_first_last_line
CONSTRAINT_ID = "GH-14"
PARAM_NAMES = ['first_line', 'last_line']
def check(response_text, params, context=None, meta=None):
    return check_first_last_line(CONSTRAINT_ID, response_text, params)
