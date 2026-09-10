import base64
import json
import os
import random
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from Crypto.Cipher import AES

import main as mimotion
from util import push_util


BEIJING_TZ = mimotion.pytz.timezone("Asia/Shanghai")
DEFAULT_SETTINGS = {
    "USER": "",
    "PWD": "",
    "MIN_STEP": 18000,
    "MAX_STEP": 25000,
    "SLEEP_GAP": 5,
    "USE_CONCURRENT": False,
    "TIME_SCALE": True,
    "SCHEDULE_ENABLED": True,
    "SCHEDULE_HOURS": [7, 9, 12, 15, 18, 20, 22],
    "PUSH_PLUS_TOKEN": "",
    "PUSH_PLUS_HOUR": "",
    "PUSH_PLUS_MAX": 30,
    "PUSH_WECHAT_WEBHOOK_KEY": "",
    "TELEGRAM_BOT_TOKEN": "",
    "TELEGRAM_CHAT_ID": "",
}
SECRET_FIELDS = {
    "PWD",
    "PUSH_PLUS_TOKEN",
    "PUSH_WECHAT_WEBHOOK_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
}


def data_dir() -> Path:
    path = Path(os.environ.get("MIMOTION_DATA_DIR", ".mimotion")).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _master_key() -> bytes:
    raw = os.environ.get("MIMOTION_MASTER_KEY", "").strip()
    if not raw:
        raise RuntimeError("MIMOTION_MASTER_KEY 未配置")
    try:
        key = bytes.fromhex(raw)
    except ValueError:
        try:
            key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        except Exception as exc:
            raise RuntimeError("MIMOTION_MASTER_KEY 格式无效") from exc
    if len(key) != 32:
        raise RuntimeError("MIMOTION_MASTER_KEY 必须是 32 字节密钥")
    return key


def _encrypt(payload: dict) -> bytes:
    cipher = AES.new(_master_key(), AES.MODE_GCM)
    plaintext = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return b"MIM1" + cipher.nonce + tag + ciphertext


def _decrypt(blob: bytes) -> dict:
    if not blob.startswith(b"MIM1") or len(blob) < 36:
        raise RuntimeError("配置文件格式无效")
    nonce, tag, ciphertext = blob[4:20], blob[20:36], blob[36:]
    cipher = AES.new(_master_key(), AES.MODE_GCM, nonce=nonce)
    return json.loads(cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8"))


def load_settings() -> dict:
    path = data_dir() / "settings.enc"
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    stored = _decrypt(path.read_bytes())
    merged = dict(DEFAULT_SETTINGS)
    merged.update(stored)
    return normalize_settings(merged)


def save_settings(settings: dict) -> dict:
    normalized = normalize_settings(settings)
    path = data_dir() / "settings.enc"
    temp = path.with_suffix(".tmp")
    temp.write_bytes(_encrypt(normalized))
    try:
        os.chmod(temp, 0o600)
    except OSError:
        pass
    os.replace(temp, path)
    return normalized


def normalize_settings(settings: dict) -> dict:
    clean = dict(DEFAULT_SETTINGS)
    for key in clean:
        if key in settings:
            clean[key] = settings[key]
    clean["MIN_STEP"] = max(1, int(clean["MIN_STEP"]))
    clean["MAX_STEP"] = max(1, int(clean["MAX_STEP"]))
    clean["SLEEP_GAP"] = max(0.0, min(float(clean["SLEEP_GAP"]), 120.0))
    clean["PUSH_PLUS_MAX"] = max(1, int(clean["PUSH_PLUS_MAX"]))
    clean["USE_CONCURRENT"] = bool(clean["USE_CONCURRENT"])
    clean["TIME_SCALE"] = bool(clean["TIME_SCALE"])
    clean["SCHEDULE_ENABLED"] = bool(clean["SCHEDULE_ENABLED"])
    hours = sorted({int(hour) for hour in clean.get("SCHEDULE_HOURS", []) if 0 <= int(hour) <= 23})
    clean["SCHEDULE_HOURS"] = hours
    return clean


def split_values(value: str) -> list[str]:
    return [item.strip() for item in value.replace("\r", "").replace("\n", "#").split("#") if item.strip()]


def accounts_from_settings(settings: dict) -> list[tuple[str, str]]:
    users = split_values(str(settings.get("USER", "")))
    passwords = split_values(str(settings.get("PWD", "")))
    if not users:
        raise ValueError("尚未保存账号")
    if len(users) != len(passwords):
        raise ValueError(f"账号数量（{len(users)}）与密码数量（{len(passwords)}）不一致")
    return list(zip(users, passwords))


def mask_account(account: str) -> str:
    return mimotion.desensitize_user_name(account)


def account_summary(settings: dict) -> list[str]:
    try:
        return [mask_account(user) for user, _ in accounts_from_settings(settings)]
    except ValueError:
        return []


def effective_step_range(settings: dict, now: datetime | None = None, scheduled: bool = False) -> tuple[int, int]:
    minimum = int(settings["MIN_STEP"])
    maximum = int(settings["MAX_STEP"])
    if maximum < minimum:
        raise ValueError("最大步数必须大于或等于最小步数")
    if not scheduled or not settings.get("TIME_SCALE", True):
        return minimum, maximum
    current = now or datetime.now(BEIJING_TZ)
    rate = min((current.hour * 60 + current.minute) / (22 * 60), 1)
    return max(1, int(minimum * rate)), max(1, int(maximum * rate))


def _load_token_cache() -> None:
    token_key = os.environ.get("MIMOTION_TOKEN_AES_KEY", "")
    if len(token_key.encode("utf-8")) != 16:
        mimotion.user_tokens = {}
        return
    mimotion.aes_key = token_key.encode("utf-8")
    mimotion.user_tokens = mimotion.prepare_user_tokens()


def _persist_token_cache() -> None:
    token_key = os.environ.get("MIMOTION_TOKEN_AES_KEY", "")
    if len(token_key.encode("utf-8")) == 16:
        mimotion.aes_key = token_key.encode("utf-8")
        mimotion.persist_user_tokens()


def _push_config(settings: dict) -> push_util.PushConfig:
    return push_util.PushConfig(
        push_plus_token=settings.get("PUSH_PLUS_TOKEN"),
        push_plus_hour=settings.get("PUSH_PLUS_HOUR"),
        push_plus_max=int(settings.get("PUSH_PLUS_MAX", 30)),
        push_wechat_webhook_key=settings.get("PUSH_WECHAT_WEBHOOK_KEY"),
        telegram_bot_token=settings.get("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=settings.get("TELEGRAM_CHAT_ID"),
    )


def _write_history(record: dict) -> None:
    path = data_dir() / "history.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_history(limit: int = 50) -> list[dict]:
    path = data_dir() / "history.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    rows = []
    for line in reversed(lines):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def run_accounts(settings: dict, source: str, on_progress: Callable[[int, int, dict], None] | None = None) -> dict:
    accounts = accounts_from_settings(settings)
    minimum, maximum = effective_step_range(settings, scheduled=source == "schedule")
    _load_token_cache()
    results = []
    started = time.monotonic()
    for index, (user, password) in enumerate(accounts, start=1):
        try:
            runner = mimotion.MiMotionRunner(user, password)
            message, success = runner.login_and_post_step(minimum, maximum)
        except Exception as exc:
            success = False
            message = f"执行异常：{type(exc).__name__}"
        result = {"user": mask_account(user), "success": bool(success), "msg": message}
        results.append(result)
        if on_progress:
            on_progress(index, len(accounts), result)
        if index < len(accounts) and not settings.get("USE_CONCURRENT"):
            time.sleep(float(settings.get("SLEEP_GAP", 5)))
    _persist_token_cache()
    success_count = sum(1 for item in results if item["success"])
    summary = f"执行账号总数 {len(results)}，成功 {success_count}，失败 {len(results) - success_count}"
    if any(settings.get(key) for key in ("PUSH_PLUS_TOKEN", "PUSH_WECHAT_WEBHOOK_KEY", "TELEGRAM_BOT_TOKEN")):
        push_util.push_results(results, summary, _push_config(settings))
    record = {
        "time": datetime.now(BEIJING_TZ).isoformat(timespec="seconds"),
        "source": source,
        "success": success_count,
        "failed": len(results) - success_count,
        "duration_seconds": round(time.monotonic() - started, 1),
        "range": [minimum, maximum],
        "results": results,
    }
    _write_history(record)
    return record


def _schedule_state_path() -> Path:
    return data_dir() / "schedule-state.json"


def _read_schedule_state() -> dict:
    path = _schedule_state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_schedule_state(state: dict) -> None:
    path = _schedule_state_path()
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def ensure_day_plan(settings: dict, now: datetime | None = None) -> dict:
    current = now or datetime.now(BEIJING_TZ)
    day = current.strftime("%Y-%m-%d")
    state = _read_schedule_state()
    configured_hours = [int(hour) for hour in settings.get("SCHEDULE_HOURS", [])]
    existing_hours = sorted(int(hour) for hour in state.get("minutes", {}).keys())
    if state.get("day") != day or existing_hours != configured_hours:
        generator = random.SystemRandom()
        state = {
            "day": day,
            "minutes": {str(hour): generator.randint(2, 52) for hour in configured_hours},
            "completed": [],
        }
        _write_schedule_state(state)
    return state


def next_scheduled_run(settings: dict, now: datetime | None = None) -> datetime | None:
    if not settings.get("SCHEDULE_ENABLED") or not settings.get("SCHEDULE_HOURS"):
        return None
    current = now or datetime.now(BEIJING_TZ)
    state = ensure_day_plan(settings, current)
    completed = set(state.get("completed", []))
    candidates = []
    for hour, minute in state.get("minutes", {}).items():
        key = f"{state['day']}T{int(hour):02d}"
        candidate = current.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        if key not in completed and candidate >= current:
            candidates.append(candidate)
    if candidates:
        return min(candidates)
    tomorrow = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    generator = random.SystemRandom()
    return tomorrow.replace(hour=min(settings["SCHEDULE_HOURS"]), minute=generator.randint(2, 52))


def scheduler_tick() -> str:
    settings = load_settings()
    if not settings.get("SCHEDULE_ENABLED"):
        return "schedule disabled"
    try:
        accounts_from_settings(settings)
    except ValueError:
        return "not configured"
    now = datetime.now(BEIJING_TZ)
    state = ensure_day_plan(settings, now)
    planned_minute = state.get("minutes", {}).get(str(now.hour))
    run_key = f"{state['day']}T{now.hour:02d}"
    if planned_minute is None or now.minute < int(planned_minute) or run_key in state.get("completed", []):
        return "not due"
    lock_path = data_dir() / "scheduler.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    except FileExistsError:
        if time.time() - lock_path.stat().st_mtime < 7200:
            return "already running"
        lock_path.unlink(missing_ok=True)
        return scheduler_tick()
    try:
        record = run_accounts(settings, source="schedule")
        state = ensure_day_plan(settings, now)
        state.setdefault("completed", []).append(run_key)
        state["last_result"] = {"time": record["time"], "success": record["success"], "failed": record["failed"]}
        _write_schedule_state(state)
        return "completed"
    finally:
        lock_path.unlink(missing_ok=True)


def settings_health(settings: dict) -> dict:
    accounts = account_summary(settings)
    return {
        "configured": bool(accounts),
        "account_count": len(accounts),
        "accounts": accounts,
        "has_notifications": any(settings.get(key) for key in SECRET_FIELDS - {"PWD"}),
    }


def generate_master_key() -> str:
    return secrets.token_hex(32)


def generate_token_key() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(16))
