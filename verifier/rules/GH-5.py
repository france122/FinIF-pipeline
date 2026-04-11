from verifier.rules._shared import check_heading_levels
CONSTRAINT_ID = "GH-5"
PARAM_NAMES = ['n']
def check(response_text, params, context=None, meta=None):
    return check_heading_levels(CONSTRAINT_ID, response_text, params)
