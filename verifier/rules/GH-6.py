from verifier.rules._shared import check_numbered_list


CONSTRAINT_ID = "GH-6"
PARAM_NAMES = []


def check(response_text, params, context=None, meta=None):
    return check_numbered_list(CONSTRAINT_ID, response_text, params)
