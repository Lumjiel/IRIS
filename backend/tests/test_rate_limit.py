"""RateLimiter（滑窗 + 日配额）单元测试。"""
import sqlite3
import time
from unittest.mock import patch

import pytest

from app.api.routes import RateLimiter


@pytest.fixture
def limiter_db(tmp_path):
    return str(tmp_path / "rate_test.db")


def test_allows_under_limit(limiter_db):
    rl = RateLimiter(db_path=limiter_db, max_requests=3, window_seconds=60)
    assert rl.is_allowed("ip1") is True
    assert rl.is_allowed("ip1") is True
    assert rl.is_allowed("ip1") is True


def test_blocks_over_limit(limiter_db):
    rl = RateLimiter(db_path=limiter_db, max_requests=2, window_seconds=60)
    assert rl.is_allowed("ip1") is True
    assert rl.is_allowed("ip1") is True
    assert rl.is_allowed("ip1") is False
    # 其他 IP 不受影响
    assert rl.is_allowed("ip2") is True


def test_window_expiry_allows_again(limiter_db):
    rl = RateLimiter(db_path=limiter_db, max_requests=1, window_seconds=60)
    assert rl.is_allowed("ip1") is True
    assert rl.is_allowed("ip1") is False
    # 把已记录时间戳回拨到窗口外 → 再次放行
    conn = sqlite3.connect(limiter_db)
    conn.execute("UPDATE rate_limits SET ts = ?", (time.time() - 120,))
    conn.commit()
    conn.close()
    assert rl.is_allowed("ip1") is True


def test_key_prefix_isolates_minute_and_daily(limiter_db):
    """分钟窗口与日配额共用同一张表，靠 key 前缀隔离计数。"""
    minute_rl = RateLimiter(db_path=limiter_db, max_requests=1, window_seconds=60)
    daily_rl = RateLimiter(db_path=limiter_db, max_requests=1, window_seconds=86400)
    assert minute_rl.is_allowed("ip1") is True
    assert minute_rl.is_allowed("ip1") is False
    # daily:ip1 是独立计数，不受分钟窗口占满影响
    assert daily_rl.is_allowed("daily:ip1") is True


def test_fail_closed_on_storage_error(limiter_db):
    rl = RateLimiter(db_path=limiter_db, max_requests=5, window_seconds=60)
    with patch("sqlite3.connect", side_effect=sqlite3.OperationalError("db locked")):
        assert rl.is_allowed("ip1") is False
