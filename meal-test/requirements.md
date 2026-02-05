## 🚀 프로젝트 개요
- **목표**: 해커톤 참가자들의 식단을 공유하는 초간단 API 서버 구축
- **핵심 가치**: 빠른 구현(MVP), 가독성 좋은 코드, 프론트엔드와의 원활한 통신

## 🛠 기술 스택 (Tech Stack)
- **Language**: Python 3.x
- **Framework**: Flask
- **Database**: 우선순위 1(In-memory List), 우선순위 2(SQLite)
- **Extension**: Flask-CORS (프론트엔드 연동 필수)

## 📐 설계 대원칙
1. **RESTful API**: 리소스 명칭은 명사로, 행위는 HTTP Method(GET, POST)로 구분한다.
2. **Stateless**: 별도의 세션 관리 없이 API 요청만으로 데이터가 처리되게 한다.
3. **Error Handling**: 데이터 누락 시 400 Bad Request와 에러 메시지를 JSON으로 반환한다.
4. **CORS 허용**: 모든 도메인(`*`)에서의 요청을 허용하여 프론트엔드 작업에 차질이 없게 한다.

## 🔗 API 명세 (Specification)
1. **식단 목록 조회**
   - Endpoint: `GET /api/meals`
   - Response: `[{"id": 1, "menu": "제육볶음", "user": "백민수"}, ...]`
2. **식단 등록**
   - Endpoint: `POST /api/meals`
   - Request Body: `{"menu": "string", "user": "string"}`
   - Response: `{"message": "Success", "id": 2}`

## 🤖 Claude에게 내리는 지시사항
- 위 명세에 맞춰 `app.py` 단일 파일로 실행 가능한 코드를 작성해줘.
- 데이터베이스는 재시작하면 초기화되어도 괜찮으니 리스트(List) 변수를 사용해줘.
- 각 함수에는 이 코드가 무엇을 하는지 한 줄 주석을 달아줘.