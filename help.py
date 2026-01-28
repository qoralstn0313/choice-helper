from flask import Flask, request, jsonify, render_template
import random
from datetime import datetime

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # 한글 이스케이프 방지(환경에 따라 유용)

# 메모리 저장소 (해커톤용)
HISTORY = []  # 최근 기록이 쌓임


@app.get("/health")
def health():
    return jsonify(ok=True)


def _clean_options(options):
    # options가 문자열로 들어오면 리스트로 바꿈
    if isinstance(options, str):
        options = [options]
    # 공백 제거 + 빈 값 제거
    return [str(o).strip() for o in options if str(o).strip()]


@app.post("/decide")
def decide():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()

    # 옵션(기본)
    options = _clean_options(data.get("options") or [])

    # 가중치(선택) - 예: weights: [1, 3, 2]
    weights = data.get("weights")

    # 다시뽑기 옵션(선택)
    avoid_last = bool(data.get("avoid_last", False))

    if not question:
        return jsonify(error="question이 필요합니다."), 400
    if len(options) < 2:
        return jsonify(error="options는 최소 2개가 필요합니다."), 400
    if len(options) > 5:
        return jsonify(error="options는 최대 5개까지 가능합니다."), 400

    # avoid_last 처리: 가장 최근 picked가 있으면 후보에서 제외
    last_picked = HISTORY[-1]["picked"] if HISTORY else None
    candidate_options = options[:]
    candidate_weights = None

    if avoid_last and last_picked in candidate_options and len(candidate_options) > 1:
        idx = candidate_options.index(last_picked)
        candidate_options.pop(idx)
        if isinstance(weights, list) and len(weights) == len(options):
            candidate_weights = weights[:]
            candidate_weights.pop(idx)

    # weights 검증 및 적용
    if candidate_weights is None:
        if weights is None:
            picked = random.choice(candidate_options)
        else:
            if not isinstance(weights, list) or len(weights) != len(options):
                return (
                    jsonify(error="weights는 options와 같은 길이의 리스트여야 합니다."),
                    400,
                )
            # 숫자 변환 + 음수/0 방지
            try:
                w = [float(x) for x in weights]
            except Exception:
                return jsonify(error="weights는 숫자 리스트여야 합니다."), 400
            if any(x <= 0 for x in w):
                return jsonify(error="weights는 모두 0보다 커야 합니다."), 400

            # avoid_last로 옵션이 빠졌다면 candidate_weights가 필요
            if avoid_last and last_picked in options and len(options) > 1:
                # 위에서 candidate_weights를 만들었어야 함
                if candidate_weights is None:
                    # 안전망(원칙상 도달 안 함)
                    candidate_weights = w
            else:
                candidate_weights = w

            picked = random.choices(candidate_options, weights=candidate_weights, k=1)[
                0
            ]

    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "options": options,
        "picked": picked,
    }
    HISTORY.append(record)

    return jsonify(record)


@app.get("/history")
def history():
    # /history?limit=10 형태 지원
    limit = request.args.get("limit", default="10")
    try:
        limit = int(limit)
    except ValueError:
        return jsonify(error="limit는 정수여야 합니다."), 400

    limit = max(1, min(limit, 50))  # 1~50으로 제한
    return jsonify(HISTORY[-limit:])


@app.post("/history/clear")
def clear_history():
    HISTORY.clear()
    return jsonify(ok=True)


# (선택) 간단 UI
@app.get("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
