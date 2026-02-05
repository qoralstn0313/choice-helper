from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
# 모든 도메인에서의 요청을 허용 (CORS)
CORS(app)

# 데이터베이스 대용 리스트 (In-memory DB)
meals = []
next_id = 1


# 식단 목록 조회 API
@app.route("/api/meals", methods=["GET"])
def get_meals():
    """저장된 모든 식단 목록을 반환합니다."""
    return jsonify(meals), 200


# 식단 등록 API
@app.route("/api/meals", methods=["POST"])
def create_meal():
    """새로운 식단을 등록합니다."""
    global next_id
    data = request.get_json()

    # 데이터 유효성 검사
    if not data or "menu" not in data or "user" not in data:
        return jsonify({"error": "Menu and user are required"}), 400

    new_meal = {"id": next_id, "menu": data["menu"], "user": data["user"]}

    meals.append(new_meal)
    next_id += 1

    return jsonify({"message": "Success", "id": new_meal["id"]}), 201


if __name__ == "__main__":
    # 서버 실행 (디버그 모드 활성화)
    app.run(host="0.0.0.0", port=5001, debug=True)
