from verifier.rules._shared import check_speaking_duration

CONSTRAINT_ID = "GH-16"
PARAM_NAMES = ['n']

def check(response_text, params, context=None, meta=None):
    return check_speaking_duration(CONSTRAINT_ID, response_text, params)
