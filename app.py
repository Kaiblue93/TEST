from __future__ import annotations

import html
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "community.db"


def init_db() -> None:
    with sqlite3.connect(DATABASE) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            );
            """
        )


def layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <link rel=\"stylesheet\" href=\"/static/style.css\" />
</head>
<body>
  <header class=\"site-header\">
    <div class=\"container\">
      <h1><a href=\"/\">우리 동네 카페</a></h1>
      <p>네이버 카페 느낌의 간단한 게시판</p>
    </div>
  </header>
  <main class=\"container\">{body}</main>
</body>
</html>"""


def redirect(start_response, location: str):
    start_response("302 Found", [("Location", location)])
    return [b""]


def parse_post_data(environ) -> dict[str, str]:
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError:
        length = 0
    body = environ["wsgi.input"].read(length).decode("utf-8")
    parsed = parse_qs(body)
    return {k: v[0].strip() if v else "" for k, v in parsed.items()}


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")

    if path == "/static/style.css":
        css_file = BASE_DIR / "static" / "style.css"
        if css_file.exists():
            data = css_file.read_bytes()
            start_response("200 OK", [("Content-Type", "text/css; charset=utf-8")])
            return [data]
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return ["Not found".encode("utf-8")]

    with sqlite3.connect(DATABASE) as db:
        db.row_factory = sqlite3.Row

        if path == "/" and method == "GET":
            posts = db.execute(
                """
                SELECT p.id, p.title, p.author, p.created_at, COUNT(c.id) comment_count
                FROM posts p
                LEFT JOIN comments c ON c.post_id = p.id
                GROUP BY p.id
                ORDER BY p.id DESC
                """
            ).fetchall()

            if posts:
                items = "".join(
                    f"""
                    <li>
                      <a href=\"/posts/{row['id']}\">
                        <strong>{html.escape(row['title'])}</strong>
                        <span>작성자 {html.escape(row['author'])}</span>
                        <span>댓글 {row['comment_count']}</span>
                        <time>{row['created_at']}</time>
                      </a>
                    </li>
                    """
                    for row in posts
                )
                post_list = f"<ul class='post-list'>{items}</ul>"
            else:
                post_list = "<p class='empty'>아직 게시글이 없습니다. 첫 글을 작성해보세요!</p>"

            body = f"""
            <section class=\"panel\">
              <div class=\"panel-header\">
                <h2>게시글 목록</h2>
                <a class=\"button\" href=\"/posts/new\">글쓰기</a>
              </div>
              {post_list}
            </section>
            """
            page = layout("게시글 목록 - 우리 동네 카페", body)
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [page.encode("utf-8")]

        if path == "/posts/new" and method == "GET":
            body = """
            <section class=\"panel\">
              <h2>새 게시글 작성</h2>
              <form class=\"form\" method=\"post\" action=\"/posts/new\">
                <label>제목<input type=\"text\" name=\"title\" required /></label>
                <label>작성자<input type=\"text\" name=\"author\" placeholder=\"닉네임 (기본: 익명)\" /></label>
                <label>내용<textarea name=\"content\" rows=\"8\" required></textarea></label>
                <div class=\"actions\">
                  <button class=\"button\" type=\"submit\">등록</button>
                  <a class=\"button secondary\" href=\"/\">취소</a>
                </div>
              </form>
            </section>
            """
            page = layout("글쓰기 - 우리 동네 카페", body)
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [page.encode("utf-8")]

        if path == "/posts/new" and method == "POST":
            form = parse_post_data(environ)
            title = form.get("title", "")
            author = form.get("author", "") or "익명"
            content = form.get("content", "")
            if title and content:
                db.execute(
                    "INSERT INTO posts (title, author, content) VALUES (?, ?, ?)",
                    (title, author, content),
                )
                db.commit()
            return redirect(start_response, "/")

        if path.startswith("/posts/"):
            try:
                post_id = int(path.split("/")[2])
            except (IndexError, ValueError):
                post_id = -1

            post = db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
            if post is None:
                start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
                return ["게시글을 찾을 수 없습니다.".encode("utf-8")]

            if method == "POST":
                form = parse_post_data(environ)
                author = form.get("author", "") or "익명"
                content = form.get("content", "")
                if content:
                    db.execute(
                        "INSERT INTO comments (post_id, author, content) VALUES (?, ?, ?)",
                        (post_id, author, content),
                    )
                    db.commit()
                return redirect(start_response, f"/posts/{post_id}")

            comments = db.execute(
                "SELECT * FROM comments WHERE post_id = ? ORDER BY id DESC", (post_id,)
            ).fetchall()
            comment_items = "".join(
                f"<li><p>{html.escape(row['content'])}</p><small>{html.escape(row['author'])} · {row['created_at']}</small></li>"
                for row in comments
            ) or "<li class='empty'>아직 댓글이 없습니다.</li>"

            safe_content = html.escape(post["content"]).replace("\n", "<br>")
            body = f"""
            <article class=\"panel\">
              <h2>{html.escape(post['title'])}</h2>
              <p class=\"meta\">작성자 {html.escape(post['author'])} · {post['created_at']}</p>
              <div class=\"content\">{safe_content}</div>
            </article>
            <section class=\"panel\">
              <h3>댓글 {len(comments)}개</h3>
              <form class=\"form\" method=\"post\" action=\"/posts/{post_id}\">
                <label>작성자<input type=\"text\" name=\"author\" placeholder=\"닉네임 (기본: 익명)\" /></label>
                <label>댓글<textarea name=\"content\" rows=\"4\" required></textarea></label>
                <div class=\"actions\">
                  <button class=\"button\" type=\"submit\">댓글 등록</button>
                  <a class=\"button secondary\" href=\"/\">목록</a>
                </div>
              </form>
              <ul class=\"comment-list\">{comment_items}</ul>
            </section>
            """
            page = layout(f"{html.escape(post['title'])} - 우리 동네 카페", body)
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [page.encode("utf-8")]

    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return ["Not found".encode("utf-8")]


if __name__ == "__main__":
    init_db()
    with make_server("0.0.0.0", 5000, app) as httpd:
        print("Serving on http://0.0.0.0:5000")
        httpd.serve_forever()
