from verifier.rules._shared import check_first_person_no_third

CONSTRAINT_ID = "GH-20"
PARAM_NAMES = []

def check(response_text, params, context=None, meta=None):
    return check_first_person_no_third(CONSTRAINT_ID, response_text, params)
