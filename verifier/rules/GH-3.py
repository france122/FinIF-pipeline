from verifier.rules._shared import check_paragraphs


CONSTRAINT_ID = "GH-3"
PARAM_NAMES = ['n']


def check(response_text, params, context=None, meta=None):
    return check_paragraphs(CONSTRAINT_ID, response_text, params)
