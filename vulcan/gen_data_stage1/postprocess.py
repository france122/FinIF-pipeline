import json


def _parse_json_if_possible(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    if text[0] not in "[{":
        return value
    try:
        return json.loads(text)
    except Exception:
        return value


def _get_field(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _coerce_input_object(data):
    input_obj = _get_field(data, "input", {})
    input_obj = _parse_json_if_possible(input_obj)
    if isinstance(input_obj, dict):
        return input_obj
    return {}


def _get_step_output(data, step_name):
    steps = _get_field(data, "steps", {})
    if isinstance(steps, dict):
        step = steps.get(step_name, {})
        output = _get_field(step, "output")
        if output is not None:
            return output
    if steps:
        step = _get_field(steps, step_name, {})
        output = _get_field(step, "output")
        if output is not None:
            return output

    step_results = _get_field(data, "step_results", [])
    if isinstance(step_results, list):
        for step in step_results:
            step = _parse_json_if_possible(step)
            if isinstance(step, dict) and step.get("name") == step_name:
                return step.get("output")
    return None


def _content_to_text(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                if item.strip():
                    parts.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text).strip())
        return "\n".join([part for part in parts if part]).strip()
    return str(content).strip()


def _extract_model_text(output):
    if output is None:
        return ""

    if isinstance(output, dict):
        output_text = output.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        choices = output.get("choices")
        if isinstance(choices, list) and choices:
            choice0 = choices[0] or {}
            message = choice0.get("message") or {}
            content = message.get("content")
            text = _content_to_text(content)
            if text:
                return text

            choice_text = choice0.get("text")
            if isinstance(choice_text, str) and choice_text.strip():
                return choice_text.strip()

        content = output.get("content")
        text = _content_to_text(content)
        if text:
            return text

    return str(output).strip()


def _extract_finish_reason(output):
    if not isinstance(output, dict):
        return None
    choices = output.get("choices")
    if isinstance(choices, list) and choices:
        return choices[0].get("finish_reason")
    return output.get("finish_reason")


def _extract_usage(output):
    if isinstance(output, dict):
        return output.get("usage")
    return None


def handler(data):
    input_obj = _coerce_input_object(data)
    metadata = _parse_json_if_possible(input_obj.get("metadata", {}))
    if not isinstance(metadata, dict):
        metadata = {}
    output = _get_step_output(data, "model_request")
    output = _parse_json_if_possible(output)

    response_text = _extract_model_text(output)

    return {
        "task_name": metadata.get("task_name"),
        "target_model": metadata.get("target_model"),
        "data_version": metadata.get("data_version"),
        "sample_id": metadata.get("sample_id"),
        "query_id": metadata.get("query_id"),
        "split": metadata.get("split"),
        "track": metadata.get("track"),
        "source_type": metadata.get("source_type"),
        "origin_task": metadata.get("origin_task"),
        "template_id": metadata.get("template_id"),
        "template_name": metadata.get("template_name"),
        "role_mode": metadata.get("role_mode"),
        "role": metadata.get("role"),
        "title": metadata.get("title"),
        "material_type": metadata.get("material_type"),
        "query_input": metadata.get("query_input"),
        "rendered_prompt": metadata.get("rendered_prompt"),
        "constraint_ids": metadata.get("constraint_ids", []),
        "parametric_constraint_ids": metadata.get("parametric_constraint_ids", []),
        "constraints": metadata.get("constraints", []),
        "quality_review": metadata.get("quality_review"),
        "response_text": response_text,
        "response_char_count": len(response_text),
        "response_nonempty": bool(response_text.strip()),
        "finish_reason": _extract_finish_reason(output),
        "usage": _extract_usage(output),
        "raw_model_output": output,
    }
