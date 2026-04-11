from verifier.rules._shared import check_first_word
CONSTRAINT_ID = "GH-11"
PARAM_NAMES = ['word']
def check(response_text, params, context=None, meta=None):
    return check_first_word(CONSTRAINT_ID, response_text, params)
