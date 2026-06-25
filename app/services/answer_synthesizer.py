import json
from core.config import OPENAI_API_KEY, OPENAI_MODEL
from observability.logging_utils import log_event

_SYSTEM_PROMPT = """You are Atlas, an enterprise operations assistant.
Your job is to synthesise raw tool outputs into a clear, accurate, actionable response.

Style rules:
- Lead with the most operationally important finding.
- Use markdown: **bold** for names/severity/risk levels, bullet lists for items, inline code for IDs.
- Be concise but complete — no filler phrases like "Based on the data provided...".
- Never invent data; only reference what appears in tool_outputs.
- For portfolio queries (multiple clients): group by client, surface highest-risk items first.
- For single-client queries: profile → open issues → latest history note → risk assessment → next action.
- Always end with a clear recommended action if risk level is High or Critical.
- Tone: professional, direct, no jargon beyond what the data itself contains.
"""


def _build_context(user_query: str, tool_outputs: list, escalation: dict | None, next_action: dict | None) -> str:
    ctx = {
        'user_query': user_query,
        'tool_outputs': [],
    }

    for step in tool_outputs:
        tool = step.get('tool') or step.get('skill', '')
        output = step.get('output')

        # Truncate very large issue lists to avoid token blowout
        if tool == 'list_all_open_issues' and isinstance(output, list) and len(output) > 40:
            truncated = output[:40]
            ctx['tool_outputs'].append({
                'tool': tool,
                'output': truncated,
                'note': f'{len(output)} total issues — showing first 40 by severity',
            })
        else:
            ctx['tool_outputs'].append({'tool': tool, 'output': output})

    if escalation:
        ctx['escalation_assessment'] = escalation
    if next_action:
        ctx['next_action_created'] = next_action

    return json.dumps(ctx, default=str, ensure_ascii=False)


def synthesize_answer(
    user_query: str,
    tool_outputs: list,
    escalation: dict | None = None,
    next_action: dict | None = None,
) -> str | None:
    """
    Call GPT to generate a natural-language answer from structured tool outputs.
    Returns None on any failure so the caller can fall back to rule-based synthesis.
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'replace_me':
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        context = _build_context(user_query, tool_outputs, escalation, next_action)

        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            max_tokens=800,
            messages=[
                {'role': 'system', 'content': _SYSTEM_PROMPT},
                {'role': 'user', 'content': context},
            ],
        )
        answer = resp.choices[0].message.content.strip()
        log_event('synthesizer', {'via': 'llm', 'model': OPENAI_MODEL,
                                   'input_chars': len(context), 'output_chars': len(answer)})
        return answer
    except Exception as exc:
        log_event('synthesizer', {'via': 'llm', 'error': str(exc)})
        return None
