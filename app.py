# app.py
from storybook import create_app

app = create_app()

if __name__ == "__main__":
    # 포트를 5000 -> 8000으로 변경!
    app.run(debug=True, port=8000)