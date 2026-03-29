"""Local web frontend for the biosignal analysis pipeline."""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", message=".*cgi.*", category=DeprecationWarning)

import cgi
import contextlib
import io
import json
import mimetypes
import os
import re
import shutil
import threading
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

os.environ.setdefault("HOME", "/tmp")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/mplconfig")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")
os.environ.setdefault("MPLBACKEND", "Agg")

from nm_config import nm_config
from utils.Analysis import run_analysis
from utils.LoadDataset import load_dataset
from utils.Preprocess import preprocess_dataset
from utils.ui import make_result_caption


ROOT = Path(__file__).resolve().parent
WEBUI_DIR = ROOT / "webui"
WORKSPACE_DIR = ROOT / ".frontend_workspace" / "sessions"
HOST = "127.0.0.1"
PORT = 8765

MODALITY_META = {
    "eeg": {
        "label": "脑电 EEG",
        "description": "单个 EDF 文件内包含五通道脑电数据，自动聚合后执行频带功率与专注/放松分析。",
        "channel_hint": "上传 1 个 EDF 文件，文件内直接包含 5 个脑电通道。",
        "expected_files": 1,
        "modules": [
            {"key": "band", "label": "频带功率分析", "detail": "Theta / Alpha / Beta / Gamma 频带功率与相对功率"},
        ],
    },
    "ecg": {
        "label": "心电 ECG",
        "description": "支持单通道或多通道 EDF 心电，若为多通道则默认分析第 3 通道。",
        "channel_hint": "上传 1 个 EDF 文件；若文件内存在多通道心电，默认读取第 3 通道。",
        "expected_files": 1,
        "modules": [
            {"key": "heart_rate", "label": "心率与 HRV 分析", "detail": "R 波检测、RR 间期、SDNN、RMSSD"},
        ],
    },
    "emg": {
        "label": "肌电 EMG",
        "description": "EDF 肌电数据，自动执行频谱、时频和滑动窗口频域分析。",
        "channel_hint": "上传 1 个 EDF 文件；当前样例为单通道肌电。",
        "expected_files": 1,
        "modules": [
            {"key": "fft", "label": "FFT 频谱分析", "detail": "整体频谱分布与主频结构"},
            {"key": "stft", "label": "STFT 时频分析", "detail": "短时傅里叶变换与时频图"},
            {"key": "freq_analysis", "label": "频域指标分析", "detail": "RMS、MPF、MDF 滑动窗口分析"},
        ],
    },
}


def _slugify_filename(name: str) -> str:
    safe = re.sub(r"[^\w.\-]+", "_", Path(name).name, flags=re.UNICODE)
    return safe.strip("._") or "upload.edf"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_workspace() -> None:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def _list_result_images(result_dir: Path, session_id: str) -> list[dict[str, str]]:
    if not result_dir.exists():
        return []

    images = []
    for file_path in sorted(result_dir.rglob("*.png")):
        rel_path = file_path.relative_to(result_dir).as_posix()
        caption = make_result_caption(file_path.stem)
        images.append(
            {
                "name": caption,
                "url": f"/session-files/{session_id}/results/{rel_path}",
            }
        )
    return images


@dataclass
class SessionLogWriter:
    session_id: str

    def write(self, text: str) -> int:
        if not text:
            return 0
        SESSION_STORE.append_log(self.session_id, text)
        return len(text)

    def flush(self) -> None:
        return None


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, dict[str, Any]] = {}

    def create(self, user_info: dict[str, Any]) -> dict[str, Any]:
        session_id = uuid.uuid4().hex[:10]
        session_root = WORKSPACE_DIR / session_id
        session_root.mkdir(parents=True, exist_ok=True)
        record = {
            "id": session_id,
            "created_at": _now(),
            "updated_at": _now(),
            "status": "draft",
            "user": user_info,
            "modality": None,
            "files": [],
            "modules": [],
            "allowed_modules": [],
            "log": "",
            "result_images": [],
            "error": None,
            "session_root": str(session_root),
            "upload_dir": None,
            "result_dir": str(session_root / "results"),
        }
        with self._lock:
            self._sessions[session_id] = record
        return self.snapshot(session_id)

    def get(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            if session_id not in self._sessions:
                raise KeyError(session_id)
            return self._sessions[session_id]

    def snapshot(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            record = dict(self._sessions[session_id])
        record.pop("session_root", None)
        record.pop("upload_dir", None)
        record.pop("result_dir", None)
        return record

    def update(self, session_id: str, **values: Any) -> dict[str, Any]:
        with self._lock:
            record = self._sessions[session_id]
            record.update(values)
            record["updated_at"] = _now()
        return self.snapshot(session_id)

    def append_log(self, session_id: str, text: str) -> None:
        with self._lock:
            self._sessions[session_id]["log"] += text
            self._sessions[session_id]["updated_at"] = _now()

    def set_upload(self, session_id: str, modality: str, saved_files: list[str], upload_dir: Path) -> dict[str, Any]:
        modules = [item["key"] for item in MODALITY_META[modality]["modules"]]
        return self.update(
            session_id,
            modality=modality,
            files=saved_files,
            modules=modules,
            allowed_modules=modules,
            upload_dir=str(upload_dir),
            status="uploaded",
            error=None,
            log="",
            result_images=[],
        )


SESSION_STORE = SessionStore()


def _prepare_upload_dir(session_id: str, modality: str) -> Path:
    session = SESSION_STORE.get(session_id)
    upload_dir = Path(session["session_root"]) / "uploads" / f"{modality}_data"
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _parse_json_body(handler: "FrontendHandler") -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(content_length) if content_length else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _save_uploaded_files(form: cgi.FieldStorage, upload_dir: Path) -> list[str]:
    field = form["files"] if "files" in form else []
    items = field if isinstance(field, list) else [field]
    saved_files = []
    for item in items:
        if not getattr(item, "filename", None):
            continue
        safe_name = _slugify_filename(item.filename)
        target = upload_dir / safe_name
        with target.open("wb") as handle:
            shutil.copyfileobj(item.file, handle)
        saved_files.append(safe_name)
    return saved_files


def _validate_upload(modality: str, saved_files: list[str]) -> None:
    if modality not in MODALITY_META:
        raise ValueError("请选择有效的模态。")
    if not saved_files:
        raise ValueError("请至少上传一个 EDF 文件。")
    if any(not file_name.lower().endswith(".edf") for file_name in saved_files):
        raise ValueError("系统当前只支持 EDF 文件。")

    expected = MODALITY_META[modality]["expected_files"]
    if len(saved_files) != expected:
        raise ValueError(f"{MODALITY_META[modality]['label']} 需要上传 {expected} 个 EDF 文件。")


def _run_session_analysis(session_id: str, selected_modules: list[str]) -> None:
    session = SESSION_STORE.get(session_id)
    upload_dir = Path(session["upload_dir"])
    result_dir = Path(session["result_dir"])
    if result_dir.exists():
        shutil.rmtree(result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    SESSION_STORE.update(session_id, status="running", error=None, log="", result_images=[])
    log_writer = SessionLogWriter(session_id)

    try:
        config = nm_config()
        config["fileinfo"]["fullpath"] = str(upload_dir)
        config["fileinfo"]["result_dir"] = str(result_dir)
        config["output"]["save_figures"] = True
        for key in list(config["display"].keys()):
            config["display"][key] = False

        with contextlib.redirect_stdout(log_writer), contextlib.redirect_stderr(log_writer):
            dataset, config = load_dataset(config)
            config["analysis"]["enabled_modules"] = list(selected_modules)
            filtered_dataset = preprocess_dataset(config, dataset)
            run_analysis(filtered_dataset, None, config)

        SESSION_STORE.update(
            session_id,
            status="completed",
            result_images=_list_result_images(result_dir, session_id),
            error=None,
        )
    except Exception:
        traceback_buffer = io.StringIO()
        traceback.print_exc(file=traceback_buffer)
        SESSION_STORE.append_log(session_id, "\n" + traceback_buffer.getvalue())
        SESSION_STORE.update(session_id, status="error", error="分析执行失败，请检查上传的 EDF 数据格式是否正确。")


class FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEBUI_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        return None

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path) -> None:
        mime_type, _ = mimetypes.guess_type(str(file_path))
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_api_error(self, message: str, status: int = 400) -> None:
        self._send_json({"ok": False, "error": message}, status=status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/config":
            payload = {
                "ok": True,
                "software_name": "用于多模态生理信号的分析系统",
                "modalities": MODALITY_META,
            }
            self._send_json(payload)
            return

        if parsed.path == "/api/session":
            query = parse_qs(parsed.query)
            session_id = query.get("id", [""])[0]
            if not session_id:
                self._handle_api_error("缺少会话编号。")
                return
            try:
                self._send_json({"ok": True, "session": SESSION_STORE.snapshot(session_id)})
            except KeyError:
                self._handle_api_error("未找到对应会话。", status=404)
            return

        if parsed.path.startswith("/preview-assets/"):
            file_name = Path(unquote(parsed.path.replace("/preview-assets/", "", 1))).name
            preview_root = (ROOT / "著作权材料" / "截图").resolve()
            target = (preview_root / file_name).resolve()
            if not str(target).startswith(str(preview_root)) or not target.exists():
                self._handle_api_error("预览资源不存在。", status=404)
                return
            self._send_file(target)
            return

        if parsed.path.startswith("/session-files/"):
            parts = parsed.path.split("/", 3)
            if len(parts) < 4:
                self._handle_api_error("无效的文件路径。", status=404)
                return
            session_id = parts[2]
            relative_path = parts[3]
            try:
                session = SESSION_STORE.get(session_id)
            except KeyError:
                self._handle_api_error("未找到对应会话。", status=404)
                return

            session_root = Path(session["session_root"]).resolve()
            target = (session_root / relative_path).resolve()
            if not str(target).startswith(str(session_root)) or not target.exists():
                self._handle_api_error("文件不存在。", status=404)
                return
            self._send_file(target)
            return

        if parsed.path in {"/", "/index.html"}:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/session":
                payload = _parse_json_body(self)
                name = str(payload.get("name", "")).strip()
                gender = str(payload.get("gender", "")).strip()
                age = str(payload.get("age", "")).strip()
                if not name or not gender or not age:
                    self._handle_api_error("请完整填写姓名、性别和年龄。")
                    return
                record = SESSION_STORE.create({"name": name, "gender": gender, "age": age})
                self._send_json({"ok": True, "session": record}, status=201)
                return

            if parsed.path == "/api/upload":
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={
                        "REQUEST_METHOD": "POST",
                        "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    },
                )
                session_id = form.getfirst("session_id", "").strip()
                modality = form.getfirst("modality", "").strip()
                if not session_id:
                    self._handle_api_error("缺少会话编号。")
                    return
                try:
                    upload_dir = _prepare_upload_dir(session_id, modality)
                    saved_files = _save_uploaded_files(form, upload_dir)
                    _validate_upload(modality, saved_files)
                    session = SESSION_STORE.set_upload(session_id, modality, saved_files, upload_dir)
                    self._send_json({"ok": True, "session": session})
                except KeyError:
                    self._handle_api_error("未找到对应会话。", status=404)
                except ValueError as exc:
                    self._handle_api_error(str(exc))
                return

            if parsed.path == "/api/run":
                payload = _parse_json_body(self)
                session_id = str(payload.get("session_id", "")).strip()
                modules = payload.get("modules", [])
                if not session_id:
                    self._handle_api_error("缺少会话编号。")
                    return
                session = SESSION_STORE.get(session_id)
                allowed_modules = set(session.get("allowed_modules", []))
                selected_modules = [module for module in modules if module in allowed_modules] or list(allowed_modules)
                SESSION_STORE.update(session_id, status="running", error=None, result_images=[], log="")
                worker = threading.Thread(
                    target=_run_session_analysis,
                    args=(session_id, selected_modules),
                    daemon=True,
                )
                worker.start()
                self._send_json({"ok": True, "session": SESSION_STORE.snapshot(session_id)})
                return

            self._handle_api_error("未知接口。", status=404)
        except json.JSONDecodeError:
            self._handle_api_error("请求数据格式错误。")
        except Exception as exc:
            self._handle_api_error(f"服务端错误：{exc}", status=500)


def run_server(host: str = HOST, port: int = PORT) -> None:
    _ensure_workspace()
    server = ThreadingHTTPServer((host, port), FrontendHandler)
    print("=" * 80)
    print("用于多模态生理信号的分析系统（EDF版）- 前端已启动")
    print(f"访问地址: http://{host}:{port}")
    print("按 Ctrl+C 可停止服务。")
    print("=" * 80)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n前端服务已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
