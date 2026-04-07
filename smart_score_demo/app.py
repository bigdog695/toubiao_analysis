from flask import Flask, jsonify, render_template

from .config import APP_HOST, APP_PORT, APP_TITLE, DEMO_PY_PATH, MOCK_SCORE_JSON_PATH
from .merge_service import load_mock_score, merge_score_data
from .skeleton_loader import load_demo_skeleton


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.get("/")
    def index():
        return render_template("index.html", app_title=APP_TITLE)

    @app.post("/mock-upload-tender")
    def mock_upload_tender():
        return jsonify(
            {
                "ok": True,
                "message": "招标文件已就绪（本地读取）",
                "source": str(DEMO_PY_PATH),
            }
        )

    @app.post("/mock-upload-bid")
    def mock_upload_bid():
        return jsonify(
            {
                "ok": True,
                "message": "投标文件已就绪（本地读取）",
                "source": str(MOCK_SCORE_JSON_PATH),
            }
        )

    @app.post("/run-score")
    def run_score():
        skeleton = load_demo_skeleton(DEMO_PY_PATH)
        mock_data = load_mock_score(MOCK_SCORE_JSON_PATH)
        mock_data["_mock_path"] = str(MOCK_SCORE_JSON_PATH)
        merged = merge_score_data(skeleton, mock_data)

        return jsonify(
            {
                "ok": True,
                "message": "智能打分完成（本地 mock 数据）",
                "data": merged,
            }
        )

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host=APP_HOST, port=APP_PORT, debug=True)
