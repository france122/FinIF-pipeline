from verifier.rules._shared import check_no_arabic_digits

CONSTRAINT_ID = "FH-9"
PARAM_NAMES = []

def check(response_text, params, context=None, meta=None):
    return check_no_arabic_digits(CONSTRAINT_ID, response_text, params)
