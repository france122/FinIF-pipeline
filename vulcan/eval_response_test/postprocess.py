def _parse_if_json_string(obj):
    if isinstance(obj, str) and obj.strip():
        try:
            import json
            return json.loads(obj)
        except (json.JSONDecodeError, ValueError):
            pass
    return obj


def _get_model_output(data):
    steps = getattr(data, "steps", None)
    if steps is not None:
        if isinstance(steps, dict):
            step = steps.get("model_request")
            if step is not None:
                return getattr(step, "output", None) or (step.get("output") if isinstance(step, dict) else None)
        elif isinstance(steps, list):
            for s in steps:
                name = getattr(s, "name", None) or (s.get("name") if isinstance(s, dict) else None)
                if name == "model_request":
                    return getattr(s, "output", None) or (s.get("output") if isinstance(s, dict) else None)

    step_results = getattr(data, "step_results", None)
    if isinstance(step_results, list):
        for s in step_results:
            name = getattr(s, "name", None) or (s.get("name") if isinstance(s, dict) else None)
            if name == "model_request":
                return getattr(s, "output", None) or (s.get("output") if isinstance(s, dict) else None)

    return None


def _extract_response_text(output):
    if not output or not isinstance(output, dict):
        return ""

    for item in output.get("output", []):
        if isinstance(item, dict) and item.get("type") == "message":
            for part in item.get("content", []):
                if isinstance(part, dict) and part.get("type") == "output_text":
                    return part.get("text", "")

    choices = output.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")

    return ""


def handler(data):
    import json

    raw_input = data.input
    if isinstance(raw_input, str):
        raw_input = json.loads(raw_input)
    metadata = raw_input.get("metadata", {}) if isinstance(raw_input, dict) else {}

    raw = _get_model_output(data)
    raw = _parse_if_json_string(raw)
    response_text = _extract_response_text(raw)

    return {
        **metadata,
        "response_text": response_text,
        "response_nonempty": bool(response_text.strip()),
    }
