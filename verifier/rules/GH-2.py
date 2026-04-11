from verifier.rules._shared import check_min_sentences


CONSTRAINT_ID = "GH-2"
PARAM_NAMES = ['n']


def check(response_text, params, context=None, meta=None):
    return check_min_sentences(CONSTRAINT_ID, response_text, params)
