import json
import logging
from datetime import datetime
from typing import Optional

from openai import AzureOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты оцениваешь ежедневный отчет.

Критерии:

1. Format (0-1)
Есть ли структура done / problems / plan

2. Clarity (0-1)
Насколько конкретно описано

3. Execution (0-1)
Насколько выполнен вчерашний план

4. Discipline (0-1)
1 если отчет отправлен до 23:59 текущего дня (Asia/Almaty), иначе 0

Не завышай оценки. Если сомневаешься - ставь ниже.

Ответ строго JSON:

{
  "format_score": 0-1,
  "clarity_score": 0-1,
  "execution_score": 0-1,
  "discipline_score": 0-1,
  "total_score": 0-1,
  "comment": "короткий комментарий"
}"""


def _build_client() -> AzureOpenAI:
    """Build Azure OpenAI client from settings."""
    # Extract base URL without deployment path
    # AZURE_OPENAI_ENDPOINT contains full deployment URL like:
    # https://xxx.cognitiveservices.azure.com/openai/deployments/gpt-5.4
    # We need just the base: https://xxx.cognitiveservices.azure.com
    endpoint = settings.AZURE_OPENAI_ENDPOINT
    # Strip /openai/deployments/... suffix to get base azure_endpoint
    base_url = endpoint.split("/openai/deployments")[0] if "/openai/deployments" in endpoint else endpoint

    return AzureOpenAI(
        azure_endpoint=base_url,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


def score_report(raw_text: str, yesterday_plan: Optional[str] = None, submitted_at: Optional[datetime] = None) -> dict:
    """
    Score a report using Azure OpenAI LLM.

    Args:
        raw_text: The full report text
        yesterday_plan: Previous day's plan text (if available)
        submitted_at: Datetime of report submission in Asia/Almaty timezone

    Returns:
        Dict with format_score, clarity_score, execution_score,
        discipline_score, total_score, comment
    """
    user_content = f"Текущий отчёт:\n{raw_text}"
    if yesterday_plan:
        user_content += f"\n\nВчерашний план:\n{yesterday_plan}"
    else:
        user_content += "\n\nВчерашний план: отсутствует (оцени execution по содержанию текущего отчёта)"

    if submitted_at:
        time_str = submitted_at.strftime("%H:%M")
        user_content += f"\n\nВремя отправки отчёта (Asia/Almaty): {time_str}. Если до 23:59 — discipline_score = 1, иначе 0."

    try:
        client = _build_client()
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_completion_tokens=500,
        )

        content = response.choices[0].message.content.strip()
        # Try to extract JSON from the response
        # Sometimes LLM wraps it in ```json ... ```
        if "```" in content:
            json_match = content.split("```")[1]
            if json_match.startswith("json"):
                json_match = json_match[4:]
            content = json_match.strip()

        result = json.loads(content)

        # Validate and clamp scores
        for key in ["format_score", "clarity_score", "execution_score", "discipline_score", "total_score"]:
            if key in result:
                result[key] = max(0.0, min(1.0, float(result[key])))
            else:
                result[key] = 0.0

        if "comment" not in result:
            result["comment"] = ""

        return result

    except Exception as e:
        logger.error(f"LLM scoring failed: {e}")
        return {
            "format_score": 0.0,
            "clarity_score": 0.0,
            "execution_score": 0.0,
            "discipline_score": 0.0,
            "total_score": 0.0,
            "comment": f"LLM error: {str(e)}",
        }
