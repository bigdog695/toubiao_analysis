from smart_score_demo.app import create_app
from smart_score_demo.config import APP_HOST, APP_PORT

app = create_app()

if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=True)
