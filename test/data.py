# bus.py
from datetime import time

# 데모용 정류장/노선 데이터
STOPS = [
    {"stop_id": "S100", "name": "강남대학교 정문"},
    {"stop_id": "S200", "name": "기흥역"},
    {"stop_id": "S300", "name": "수지구청"},
]

ROUTES = [
    {
        "route_id": "R10",
        "route_no": "10",
        "display_name": "10번 (강남대 ↔ 기흥역)",
        "headway_min": 12,  # 평균 배차(분)
        "daytime": {"start": time(6, 0), "end": time(22, 30)},
        # 정류장 순서 (도착정보 없을 때도 '전 정류장 통과' 같은 신호를 흉내낼 수 있음)
        "stop_sequence": ["S200", "S100"],
    },
    {
        "route_id": "R55",
        "route_no": "55",
        "display_name": "55번 (수지구청 ↔ 강남대)",
        "headway_min": 18,
        "daytime": {"start": time(6, 30), "end": time(23, 0)},
        "stop_sequence": ["S300", "S100"],
    },
]

# "도착정보 없음" 상황을 만들기 위한 데모 이벤트(가짜 실시간 신호)
# - 예: 특정 노선이 특정 정류장 직전에 포착되었다(=곧 올 가능성 높음)
# 실제 서비스에선 공공데이터/차량위치/이전 정류장 통과 등을 쓰겠지만,
# 해커톤 데모에선 이 정도만 있어도 설득 가능.
SIGNALS = [
    {
        "route_id": "R10",
        "near_stop_id": "S200",
        "minutes_ago": 1,
    },  # 1분 전에 기흥역 근처
    {
        "route_id": "R55",
        "near_stop_id": "S300",
        "minutes_ago": 6,
    },  # 6분 전에 수지구청 근처
]
