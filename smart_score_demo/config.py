from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOCK_SCORE_JSON_PATH = PROJECT_ROOT / "sample_toubiao_files" / "mock_score_report.json"
DEMO_PY_PATH = PROJECT_ROOT / "demo.py"

APP_TITLE = "投标文件智能打分 Demo"
APP_HOST = "0.0.0.0"
APP_PORT = 8000
