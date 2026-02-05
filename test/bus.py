# app.py
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

from hackathon.test.data import STOPS, ROUTES, SIGNALS

app = Flask(__name__)
CORS(app)  # 프론트(로컬/다른 포트)에서 호출 가능하게


def find_stop(stop_id: str):
    return next((s for s in STOPS if s["stop_id"] == stop_id), None)


def find_route(route_id: str):
    return next((r for r in ROUTES if r["route_id"] == route_id), None)


def routes_for_stop(stop_id: str):
    # 데모: stop_sequence에 포함되면 그 정류장 경유로 처리
    return [r for r in ROUTES if stop_id in r["stop_sequence"]]


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def score_probability(
    route, stop_id: str, now: datetime, eta_known: bool, eta_min: int | None
):
    """
    도착정보가 있으면(eta_known=True) 그 자체로 높은 확률.
    없으면(eta_known=False) '신호 + 배차 + 시간대'로 확률 스코어링.
    """
    headway = route["headway_min"]

    # 1) 도착정보가 있으면: ETA가 짧을수록 확률↑
    if eta_known and eta_min is not None:
        # 0~30분 범위로 단순 맵핑
        prob = clamp01(1.0 - (eta_min / 30.0))
        reason = f"도착정보가 제공됨(ETA {eta_min}분)"
        return prob, reason

    # 2) 도착정보가 없을 때: 신호 기반
    # 신호: 특정 노선이 '기점/이전 정류장 근처'에서 포착된 정보(가짜)
    signal = next((s for s in SIGNALS if s["route_id"] == route["route_id"]), None)

    prob = 0.15  # 기본 베이스 (없음이어도 아예 0은 아님)
    reasons = ["도착정보 없음(기본 확률)"]

    # 2-1) 운영 시간대 보정
    st = route["daytime"]["start"]
    en = route["daytime"]["end"]
    now_t = now.time()
    if not (st <= now_t <= en):
        prob *= 0.2
        reasons.append("운행시간 외/근접(확률 하향)")
    else:
        prob *= 1.2
        reasons.append("운행시간 내(확률 상향)")

    # 2-2) 배차 보정: 배차 짧을수록 확률↑
    # headway 10분이면 +, 25분이면 -
    headway_factor = clamp01((25 - headway) / 20)  # 0~0.75 정도
    prob += 0.25 * headway_factor
    reasons.append(f"배차 {headway}분 반영")

    # 2-3) 신호 보정: 최근에 근처에서 포착되었으면 확률↑
    if signal:
        minutes_ago = signal["minutes_ago"]
        near_stop = signal["near_stop_id"]

        # stop_sequence 상에서 near_stop가 stop_id '직전'에 가까울수록 가점
        seq = route["stop_sequence"]
        try:
            near_i = seq.index(near_stop)
            target_i = seq.index(stop_id)
            distance = abs(target_i - near_i)
        except ValueError:
            distance = 3  # 관계 없으면 멀다고 처리

        # 최근일수록 +, 가까울수록 +
        recency = clamp01(1.0 - (minutes_ago / 15.0))  # 0~1
        proximity = clamp01(1.0 - (distance / 4.0))  # 0~1
        boost = 0.45 * (0.6 * recency + 0.4 * proximity)
        prob += boost
        reasons.append(f"최근 신호({minutes_ago}분 전) 반영")

    prob = clamp01(prob)

    # 3) 레벨(초록/노랑/빨강) + 액션 추천
    if prob >= 0.7:
        action = "지금 정류장에서 대기 추천"
    elif prob >= 0.4:
        action = "5분 내 도착 가능성 있음(대기/이동 판단)"
    else:
        action = "잠시 후 다시 확인 권장"

    return prob, "; ".join(reasons) + f" | {action}"


@app.get("/health")
def health():
    return jsonify({"ok": True, "ts": datetime.now().isoformat()})


@app.get("/stops")
def list_stops():
    q = (request.args.get("q") or "").strip()
    items = STOPS
    if q:
        items = [s for s in STOPS if q.lower() in s["name"].lower()]
    return jsonify({"items": items})


@app.get("/routes")
def list_routes():
    stop_id = request.args.get("stop_id")
    if stop_id:
        items = routes_for_stop(stop_id)
    else:
        items = ROUTES

    # ✅ time 객체(daytime) 같은 JSON 불가 필드 제거/가공
    safe_items = [
        {
            "route_id": r["route_id"],
            "route_no": r["route_no"],
            "display_name": r["display_name"],
            "headway_min": r["headway_min"],
            "stop_sequence": r["stop_sequence"],
        }
        for r in items
    ]
    return jsonify({"items": safe_items})


@app.post("/predict")
def predict():
    """
    요청 예시:
    {
      "stop_id": "S100",
      "route_id": "R10",
      "arrival_info": {"available": false}
    }

    또는 도착정보가 있을 때:
    {
      "stop_id": "S100",
      "route_id": "R10",
      "arrival_info": {"available": true, "eta_min": 6}
    }
    """
    body = request.get_json(force=True, silent=True) or {}
    stop_id = body.get("stop_id")
    route_id = body.get("route_id")
    arrival_info = body.get("arrival_info") or {}

    if not stop_id or not route_id:
        return jsonify({"error": "stop_id와 route_id는 필수입니다."}), 400

    stop = find_stop(stop_id)
    route = find_route(route_id)
    if not stop:
        return jsonify({"error": f"stop_id '{stop_id}'를 찾을 수 없습니다."}), 404
    if not route:
        return jsonify({"error": f"route_id '{route_id}'를 찾을 수 없습니다."}), 404

    eta_known = bool(arrival_info.get("available"))
    eta_min = arrival_info.get("eta_min")
    if eta_known and (eta_min is None or not isinstance(eta_min, int)):
        return (
            jsonify(
                {"error": "arrival_info.available=true면 eta_min(int)이 필요합니다."}
            ),
            400,
        )

    now = datetime.now()
    prob, reason = score_probability(route, stop_id, now, eta_known, eta_min)

    # 프론트가 바로 쓰기 쉽게 등급도 같이
    if prob >= 0.7:
        level = "HIGH"
        badge = "🟢"
    elif prob >= 0.4:
        level = "MEDIUM"
        badge = "🟡"
    else:
        level = "LOW"
        badge = "🔴"

    percent = int(round(prob * 100))

    return jsonify(
        {
            "stop": stop,
            "route": {
                "route_id": route["route_id"],
                "route_no": route["route_no"],
                "display_name": route["display_name"],
            },
            "result": {
                "probability_percent": percent,  # ← 77
                "level": level,  # HIGH / MEDIUM / LOW
                "badge": badge,  # 🟢🟡🔴
                "message": reason,  # 행동 추천 포함
            },
        }
    )


DEMO_HTML = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BusMaybe Demo</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; margin: 24px; max-width: 720px; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; }
    select, input, button { padding: 10px; font-size: 14px; }
    button { cursor: pointer; }
    .card { margin-top: 16px; padding: 14px; border: 1px solid #ddd; border-radius: 12px; }
    .big { font-size: 22px; font-weight: 700; }
    .muted { color: #666; }
    .badge { font-size: 20px; }
  </style>
</head>
<body>
  <h2>🚌 BusMaybe (도착정보 없음 대응) 데모</h2>
  <p class="muted">정류장/노선 선택 → "예측" 클릭</p>

  <div class="row">
    <div>
      <div class="muted">정류장</div>
      <select id="stop"></select>
    </div>
    <div>
      <div class="muted">노선</div>
      <select id="route"></select>
    </div>
    <div>
      <div class="muted">도착정보</div>
      <select id="avail">
        <option value="false">없음</option>
        <option value="true">있음</option>
      </select>
    </div>
    <div>
      <div class="muted">ETA(분)</div>
      <input id="eta" type="number" min="0" placeholder="예: 6" style="width:120px" />
    </div>
    <div style="align-self:end">
      <button id="btn">예측</button>
    </div>
  </div>

  <div id="out" class="card" style="display:none"></div>

<script>
async function loadStops() {
  const res = await fetch('/stops');
  const data = await res.json();
  const sel = document.getElementById('stop');
  sel.innerHTML = data.items.map(s => `<option value="${s.stop_id}">${s.name}</option>`).join('');
}
async function loadRoutes(stopId) {
  const res = await fetch('/routes?stop_id=' + encodeURIComponent(stopId));
  const data = await res.json();
  const sel = document.getElementById('route');
  sel.innerHTML = data.items.map(r => `<option value="${r.route_id}">${r.display_name}</option>`).join('');
}
async function predict() {
  const stopId = document.getElementById('stop').value;
  const routeId = document.getElementById('route').value;
  const available = document.getElementById('avail').value === 'true';
  const etaVal = document.getElementById('eta').value;

  const payload = {
    stop_id: stopId,
    route_id: routeId,
    arrival_info: available ? { available: true, eta_min: parseInt(etaVal || "0", 10) } : { available: false }
  };

  if (available && (!etaVal || isNaN(parseInt(etaVal,10)))) {
    alert("도착정보가 '있음'이면 ETA(분)를 입력해줘!");
    return;
  }

  const res = await fetch('/predict', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await res.json();

  const out = document.getElementById('out');
  out.style.display = 'block';
  if (data.error) {
    out.innerHTML = `<div class="big">에러</div><div>${data.error}</div>`;
    return;
  }
  out.innerHTML = `
    <div class="big">
    <span class="badge">${data.result.badge}</span>
    ${data.result.level} · ${data.result.probability_percent}%
    </div>

    <div style="margin-top:10px">${data.result.message}</div>
  `;
}

document.getElementById('stop').addEventListener('change', (e) => loadRoutes(e.target.value));
document.getElementById('btn').addEventListener('click', predict);

(async () => {
  await loadStops();
  await loadRoutes(document.getElementById('stop').value);
})();
</script>
</body>
</html>
"""


@app.get("/")
def home():
    return render_template_string(DEMO_HTML)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
