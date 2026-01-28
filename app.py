from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.post("/add")
def add():
    print("요청 들어옴")
    print(request.get_json())

    data = request.get_json(silent=True) or {}
    a = data.get("a")
    b = data.get("b")

    if a is None or b is None:
        return jsonify(error="a와 b가 필요합니다."), 400

    return jsonify(result=a + b)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
