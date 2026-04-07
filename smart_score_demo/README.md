# 投标文件智能打分本地 Demo

## 启动

```bash
pip install -r requirements.txt
python run_demo.py
```

浏览器访问：`http://127.0.0.1:8000`

## 接口

- `GET /`：Demo 页面
- `POST /mock-upload-tender`：模拟上传招标文件
- `POST /mock-upload-bid`：模拟上传投标文件夹压缩包
- `POST /run-score`：读取本地 `mock_score_report.json` + `demo.py` 骨架并 merge 后返回

## 数据来源

- `sample_toubiao_files/mock_score_report.json`
- `demo.py` 中 `main()` 的 `bid_demo_data`
