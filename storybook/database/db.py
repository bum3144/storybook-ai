# storybook/database/db.py
import sqlite3
import os
from typing import List, Dict, Any

# 현재 파일(db.py)의 위치를 기준으로 data 폴더 경로를 찾습니다.
# 예: .../storybook/database/db.py -> .../storybook/data/storybook.db
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # storybook 폴더
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "storybook.db")


def get_connection():
    # 데이터 폴더가 없으면 생성 (에러 방지)
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능하게 설정
    return conn

# [추가] 동화 삭제 함수
def delete_story(story_id: int):
    conn = get_connection()
    cur = conn.cursor()
    # 1. 딸린 페이지들 먼저 삭제 (외래키 등 고려)
    cur.execute("DELETE FROM pages WHERE story_id = ?", (story_id,))
    # 2. 본문(스토리) 삭제
    cur.execute("DELETE FROM stories WHERE id = ?", (story_id,))
    conn.commit()
    conn.close()

def init_db():
    """데이터베이스 테이블 초기화"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 스토리 테이블 (동화책 기본 정보)
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS stories
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       title
                       TEXT
                       NOT
                       NULL,
                       genre
                       TEXT,
                       theme
                       TEXT,
                       hero
                       TEXT,
                       created_at
                       DATETIME
                       DEFAULT
                       CURRENT_TIMESTAMP,
                       is_finished
                       BOOLEAN
                       DEFAULT
                       0
                   )
                   ''')

    # 2. 페이지 테이블 (각 페이지의 글과 그림)
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS pages
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       story_id
                       INTEGER,
                       page_index
                       INTEGER,
                       text
                       TEXT,
                       image_url
                       TEXT,
                       FOREIGN
                       KEY
                   (
                       story_id
                   ) REFERENCES stories
                   (
                       id
                   )
                       )
                   ''')

    # 3. 표지 테이블 (표지 정보)
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS covers
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       story_id
                       INTEGER,
                       front_image_url
                       TEXT,
                       title_position
                       TEXT
                       DEFAULT
                       'middle',
                       author_name
                       TEXT,
                       back_color
                       TEXT
                       DEFAULT
                       '#ffffff',
                       FOREIGN
                       KEY
                   (
                       story_id
                   ) REFERENCES stories
                   (
                       id
                   )
                       )
                   ''')

    conn.commit()
    conn.close()
    print(f"✅ 데이터베이스 초기화 완료: {DB_PATH}")


# --- 헬퍼 함수들 (데이터 저장/조회용) ---

def create_story(title: str, genre: str, theme: str, hero: str = "") -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO stories (title, genre, theme, hero) VALUES (?, ?, ?, ?)",
                (title, genre, theme, hero))
    story_id = cur.lastrowid
    conn.commit()
    conn.close()
    return story_id


def save_pages(story_id: int, pages: List[Dict[str, Any]]):
    conn = get_connection()
    cur = conn.cursor()
    # 기존 페이지 삭제 후 다시 저장 (덮어쓰기)
    cur.execute("DELETE FROM pages WHERE story_id = ?", (story_id,))

    for p in pages:
        # 인덱스, 텍스트, 이미지 URL 저장
        idx = int(p.get('index', 0))
        txt = p.get('text', '')
        url = p.get('url', '')  # 이미지 URL이 있으면 저장

        cur.execute("INSERT INTO pages (story_id, page_index, text, image_url) VALUES (?, ?, ?, ?)",
                    (story_id, idx, txt, url))

    conn.commit()
    conn.close()


def get_all_stories():
    conn = get_connection()
    cur = conn.cursor()
    # 최신순 정렬
    cur.execute("SELECT * FROM stories ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_story_detail(story_id: int):
    conn = get_connection()
    cur = conn.cursor()

    # 스토리 정보
    cur.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
    story = cur.fetchone()

    if not story:
        conn.close()
        return None

    # 페이지 정보
    cur.execute("SELECT * FROM pages WHERE story_id = ? ORDER BY page_index", (story_id,))
    pages = cur.fetchall()

    conn.close()

    return {
        "id": story["id"],
        "title": story["title"],
        "genre": story["genre"],
        "theme": story["theme"],
        "hero": story["hero"],
        "created_at": story["created_at"],
        "pages": [dict(p) for p in pages]
    }


# 이 파일을 직접 실행할 때만 초기화 진행
if __name__ == "__main__":
    init_db()