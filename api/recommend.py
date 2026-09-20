import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler

from google import genai
from google.genai import types

GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_TIMEOUT_SECONDS = 20
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1.5
EMPTY_INGREDIENTS_MESSAGE = "재료를 1개 이상 입력해주세요"
GEMINI_FAIL_MESSAGE = "잠시 후 다시 시도해주세요"
GEMINI_BUSY_MESSAGE = "지금 요청이 많아 AI가 바빠요. 잠시 후 다시 시도해주세요"
NO_VALID_INGREDIENTS_MESSAGE = "입력하신 내용에서 사용할 수 있는 식재료를 찾지 못했어요. 재료를 다시 확인해 주세요"


def _json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _read_json_body(handler):
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b""
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _normalize_ingredients(value):
    if isinstance(value, str):
        items = re.split(r"[,/\n]", value)
    elif isinstance(value, list):
        items = value
    else:
        items = []

    cleaned = []
    for item in items:
        name = str(item).strip()
        if name and name not in cleaned:
            cleaned.append(name)
    return cleaned


def _extract_json(text):
    if not text or not str(text).strip():
        raise RuntimeError("empty gemini response")

    stripped = str(text).strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if fenced:
        stripped = fenced.group(1).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            raise RuntimeError("invalid gemini json")
        return json.loads(stripped[start : end + 1])


def _recipe_ingredients(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _normalize_recipes(data):
    recipes = data.get("recipes") if isinstance(data, dict) else None
    if not isinstance(recipes, list):
        raise RuntimeError("invalid recipes payload")

    normalized = []
    for recipe in recipes:
        if not isinstance(recipe, dict):
            continue
        name = str(
            recipe.get("name") or recipe.get("title") or recipe.get("이름") or ""
        ).strip()
        ingredients = _recipe_ingredients(
            recipe.get("ingredients") or recipe.get("재료")
        )
        method = str(
            recipe.get("method")
            or recipe.get("steps")
            or recipe.get("조리법")
            or recipe.get("간단 조리법")
            or ""
        ).strip()
        if not name:
            continue
        normalized.append(
            {
                "name": name,
                "ingredients": ingredients,
                "method": method,
            }
        )

    if not normalized:
        raise ValueError(NO_VALID_INGREDIENTS_MESSAGE)
    return normalized[:3]


def _build_prompt(ingredients, servings, time, taste):
    ingredient_text = ", ".join(ingredients)
    return f"""당신은 한국 집밥을 추천하는 요리사입니다.

먼저 아래 입력 목록의 단어를 하나씩 확인하세요.
입력: {ingredient_text}

각 단어가 실제로 먹을 수 있는 식재료(채소, 고기, 해산물, 곡물, 유제품, 조미료 등)인지
엄격하게 판단하세요. 전자제품, 자동차, 사물, 동물(반려동물 등 식재료가 아닌 것),
추상적 단어는 식재료가 아닙니다.

판단 결과 실제 식재료가 하나도 없다면, 절대로 레시피를 만들지 말고
그 단어를 요리 이름/모양/비유/재료로 절대 사용하지 말고, 다음과 같이만 응답하세요:
{{"recipes": []}}

예시 (반드시 이렇게 처리):
- 입력이 "전기차, 컴퓨터, 마우스" 인 경우 -> {{"recipes": []}}
- 입력이 "컴퓨터" 인 경우 -> {{"recipes": []}}
- 입력이 "강아지" 인 경우 -> {{"recipes": []}}

실제 식재료가 1개 이상 있을 때만 아래 조건대로 레시피를 만드세요.
그 경우 주어진 식재료를 최대한 쓰고, 꼭 필요한 재료만 추가하며,
식재료가 아닌 단어는 완전히 무시하고 레시피에 절대 포함하지 마세요.

인분: {servings}
조리시간: {time}분 이내
입맛: {taste}

JSON만 반환하세요. 설명 문장이나 마크다운은 넣지 마세요.
형식:
{{
  "recipes": [
    {{
      "name": "메뉴 이름",
      "ingredients": ["재료1", "재료2"],
      "method": "간단한 조리 순서 3~5문장"
    }}
  ]
}}
"""


def _is_rate_limited(error):
    text = str(error)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


def _call_gemini_with_retry(client, prompt):
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            return client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    response_mime_type="application/json",
                ),
            )
        except Exception as error:
            last_error = error
            if _is_rate_limited(error) and attempt < MAX_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                continue
            raise
    raise last_error


def _recommend(payload):
    ingredients = _normalize_ingredients(payload.get("ingredients"))
    if not ingredients:
        raise ValueError(EMPTY_INGREDIENTS_MESSAGE)

    servings = str(payload.get("servings") or "2").strip()
    time = str(payload.get("time") or payload.get("cookTime") or "30").strip()
    taste = str(payload.get("taste") or "담백").strip()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("missing GEMINI_API_KEY")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_SECONDS * 1000),
    )
    prompt = _build_prompt(ingredients, servings, time, taste)
    response = _call_gemini_with_retry(client, prompt)
    text = getattr(response, "text", "") or ""
    return _normalize_recipes(_extract_json(text))


class handler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send_json(self, status, payload):
        self._set_headers(status)
        self.wfile.write(_json_bytes(payload))

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_POST(self):
        try:
            payload = _read_json_body(self)
            recipes = _recommend(payload)
            self._send_json(200, {"recipes": recipes})
        except json.JSONDecodeError:
            self._send_json(400, {"error": "요청 JSON이 올바르지 않습니다"})
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
        except Exception as error:
            print("recommend failed:", error)
            message = GEMINI_BUSY_MESSAGE if _is_rate_limited(error) else GEMINI_FAIL_MESSAGE
            self._send_json(500, {"error": message})

    def log_message(self, format, *args):
        return