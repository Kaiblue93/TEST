# TEST

Rocky Linux 8에서 바로 실행 가능한 **카페형 웹 게시판** 예제입니다.
게시글 작성/목록 조회/상세 조회와 댓글 작성 기능을 제공합니다.

## 기능

- 게시글 목록 보기
- 게시글 작성
- 게시글 상세 보기
- 댓글 작성 및 목록 보기
- SQLite 기반 저장(별도 DB 서버 불필요)

## 실행 방법 (Rocky 8)

```bash
# (필요 시) Python 3 설치
sudo dnf install -y python3

# 서버 실행
python3 app.py
```

브라우저에서 아래 주소로 접속하세요.

```text
http://localhost:5000
```

## 파일 구조

- `app.py`: 웹 서버(WSGI) + 라우팅 + DB 처리
- `static/style.css`: 스타일
- `community.db`: 실행 시 자동 생성되는 SQLite DB 파일
