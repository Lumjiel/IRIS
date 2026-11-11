# 环境安装记录（一行一条：装了什么 / 为什么 / 怎么卸）

- 2026-11-11 `backend/.venv`：重建测试 venv（`python3 -m venv .venv` + `pip install -r requirements.txt -r requirements-dev.txt -i 清华源`）；requirements-dev 补齐 pytest-cov / pytest-timeout / pytest-env（原清单缺，venv 重建后测试曾收集失败）。卸载：`rm -rf backend/.venv`
- 2026-11-11 `pytest-env` + `pytest.ini` env 段：engine.py import 期就需要 DASHSCOPE_API_KEY，conftest monkeypatch 来不及，让测试自包含。卸载：`.venv/bin/pip uninstall pytest-env` + 删 pytest.ini env 段
- 2026-11-11 `playwright`（backend/.venv）+ chromium-headless-shell（~/.cache/ms-playwright）：前端无头走查截图。卸载：`.venv/bin/pip uninstall playwright; rm -rf ~/.cache/ms-playwright`
- 2026-11-11 `dnf install mesa-libgbm`：chromium 运行依赖 libgbm.so.1。卸载：`dnf remove mesa-libgbm`
- 2026-11-11 `dnf install google-noto-sans-cjk-ttc-fonts`：服务器无中文字体，headless 截图中文全是豆腐块（服务器端截图验收的前提；真机用户不受影响）。卸载：`dnf remove google-noto-sans-cjk-ttc-fonts`
