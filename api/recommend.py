import json
import os
import re
from http.server import BaseHTTPRequestHandler

import google.generativeai as genai

GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_TIMEOUT_SECONDS = 20
EMPTY_INGREDIENTS_MESSAGE = "재료를 1개 이상 입력해주세요"
GEMINI_FAIL_MESSAGE = "잠시 후 다시 시도해주세요"
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
    if len(normalized) < 2:
        raise RuntimeError("not enough recipes")
    return normalized[:3]


def _build_prompt(ingredients, servings, time, taste):
    ingredient_text = ", ".join(ingredients)
    return f"""당신은 한국 집밥을 추천하는 요리사입니다.
아래 조건에 맞는 레시피를 2개 또는 3개 추천하세요.
주어진 재료를 최대한 쓰고, 꼭 필요한 재료만 추가하세요.

재료: {ingredient_text}
인분: {servings}
조리시간: {time}분 이내
입맛: {taste}

주의: 위 재료 중 실제 요리에 쓸 수 있는 식재료가 하나도 없다면
(예: 전자제품, 자동차 등 음식과 무관한 단어만 있는 경우)
억지로 요리를 만들어내지 말고 recipes를 빈 배열 []로 반환하세요.

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

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config={
            "temperature": 0.7,
            "response_mime_type": "application/json",
        },
    )
    response = model.generate_content(
        _build_prompt(ingredients, servings, time, taste),
        request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
    )
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
            print("recommend