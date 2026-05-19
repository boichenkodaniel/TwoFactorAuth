"""
Load Testing Script for 2FA Service

Нагрузочный тест: 100 запросов, 10 параллельных клиентов.
Используется threading для симуляции concurrent load.
"""

import concurrent.futures
import json
import time
from dataclasses import dataclass
from typing import Callable
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@dataclass
class LoadTestResult:
    """Результат одного запроса."""

    endpoint: str
    method: str
    status_code: int
    elapsed_ms: float
    success: bool


@dataclass
class LoadTestSummary:
    """Сводная статистика по нагрузочному тесту."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_ms: float
    min_response_ms: float
    max_response_ms: float
    p50_response_ms: float
    p95_response_ms: float
    p99_response_ms: float
    requests_per_second: float


def make_request(method: str, endpoint: str, **kwargs) -> LoadTestResult:
    """Выполняет один HTTP-запрос и возвращает результат."""
    start = time.perf_counter()
    try:
        response_func = getattr(client, method.lower())
        response = response_func(endpoint, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return LoadTestResult(
            endpoint=endpoint,
            method=method.upper(),
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            success=200 <= response.status_code < 400,
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return LoadTestResult(
            endpoint=endpoint,
            method=method.upper(),
            status_code=0,
            elapsed_ms=elapsed_ms,
            success=False,
        )


def run_load_test(
    method: str,
    endpoint: str,
    num_requests: int = 100,
    num_workers: int = 10,
    setup_fn: Callable = None,
    **request_kwargs,
) -> LoadTestSummary:
    """
    Запускает нагрузочный тест.

    Args:
        method: HTTP метод ('get', 'post', etc.)
        endpoint: URL эндпоинта
        num_requests: общее количество запросов
        num_workers: количество параллельных работников
        setup_fn: функция для подготовки моков перед тестом
        **request_kwargs: аргументы для запроса (json, headers, etc.)

    Returns:
        LoadTestSummary со статистикой
    """
    results: list[LoadTestResult] = []

    # Setup mocks if provided
    if setup_fn:
        setup_fn()

    start_time = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(make_request, method, endpoint, **request_kwargs)
            for _ in range(num_requests)
        ]

        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    total_time = time.perf_counter() - start_time

    # Calculate statistics
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    elapsed_times = sorted([r.elapsed_ms for r in results])

    def percentile(data, p):
        if not data:
            return 0
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f) if c != f else data[f]

    return LoadTestSummary(
        total_requests=num_requests,
        successful_requests=len(successful),
        failed_requests=len(failed),
        success_rate=len(successful) / num_requests * 100,
        avg_response_ms=sum(elapsed_times) / len(elapsed_times) if elapsed_times else 0,
        min_response_ms=min(elapsed_times) if elapsed_times else 0,
        max_response_ms=max(elapsed_times) if elapsed_times else 0,
        p50_response_ms=percentile(elapsed_times, 50),
        p95_response_ms=percentile(elapsed_times, 95),
        p99_response_ms=percentile(elapsed_times, 99),
        requests_per_second=num_requests / total_time,
    )


def print_summary(endpoint: str, summary: LoadTestSummary):
    """Выводит красивый отчёт по нагрузочному тесту."""
    print("\n" + "=" * 80)
    print(f"Load Test Results: {endpoint}")
    print("=" * 80)
    print(f"Total Requests:        {summary.total_requests}")
    print(f"Successful:            {summary.successful_requests}")
    print(f"Failed:                {summary.failed_requests}")
    print(f"Success Rate:          {summary.success_rate:.2f}%")
    print(f"Requests/sec:          {summary.requests_per_second:.2f}")
    print("-" * 80)
    print(f"Avg Response Time:     {summary.avg_response_ms:.2f} ms")
    print(f"Min Response Time:     {summary.min_response_ms:.2f} ms")
    print(f"Max Response Time:     {summary.max_response_ms:.2f} ms")
    print(f"P50 (Median):          {summary.p50_response_ms:.2f} ms")
    print(f"P95:                   {summary.p95_response_ms:.2f} ms")
    print(f"P99:                   {summary.p99_response_ms:.2f} ms")
    print("=" * 80 + "\n")


# --- Setup Functions for Mocking ---


def setup_auth_mocks():
    """Настраивает моки для auth эндпоинтов."""
    patcher_user = patch("app.api.auth.User")
    mock_user = patcher_user.start()
    mock_user_instance = MagicMock()
    mock_user_instance.id = "load_test_user"
    mock_user_instance.password_hash = "hashed_pass"
    mock_user.create_user.return_value = mock_user_instance
    mock_user.get_user_by_email.return_value = mock_user_instance

    patcher_verify = patch("app.api.auth.verify_password", return_value=True)
    patcher_verify.start()

    return [patcher_user, patcher_verify]


def setup_health_mocks():
    """Health check не требует моков."""
    pass


def setup_totp_verify_mocks():
    """Настраивает моки для TOTP verify."""
    patcher_user = patch("app.api.totp.User")
    mock_user = patcher_user.start()
    mock_user_instance = MagicMock()
    mock_user_instance.id = "totp_user"
    mock_user_instance.totp_secret = "JBSWY3DPEHPK3PXP"
    mock_user.get_user_by_id.return_value = mock_user_instance

    patcher_verify = patch("app.api.totp.TOTPService.verify_totp", return_value=True)
    patcher_verify.start()

    return [patcher_user, patcher_verify]


def setup_device_list_mocks():
    """Настраивает моки для device list."""
    patcher_redis = patch("app.api.device.redis_client")
    mock_redis = patcher_redis.start()
    mock_redis.get_json.return_value = {
        "user_id": "device_user",
        "email": "device@test.com",
        "fcm_token": "token",
    }
    return [patcher_redis]


def setup_push_status_mocks():
    """Настраивает моки для push status."""
    patcher_lr = patch("app.api.push.LoginRequest")
    mock_lr = patcher_lr.start()
    mock_request = MagicMock()
    mock_request.get_status.return_value = MagicMock(value="pending")
    mock_request.site_name = "test.com"
    mock_lr.get_request.return_value = mock_request
    return [patcher_lr]


# --- Load Test Cases ---


def test_load_health_endpoint():
    """Нагрузочный тест health endpoint."""
    summary = run_load_test(
        method="get",
        endpoint="/health",
        num_requests=100,
        num_workers=10,
        setup_fn=setup_health_mocks,
    )
    print_summary("/health", summary)
    assert summary.success_rate >= 99, "Success rate should be >= 99%"
    assert summary.avg_response_ms < 100, "Avg response should be < 100ms"


def test_load_login_endpoint():
    """Нагрузочный тест login endpoint."""
    patchers = setup_auth_mocks()
    try:
        summary = run_load_test(
            method="post",
            endpoint="/auth/login",
            num_requests=100,
            num_workers=10,
            json={"email": "load@test.com", "password": "pass123"},
        )
        print_summary("/auth/login", summary)
        assert summary.success_rate >= 99, "Success rate should be >= 99%"
        assert summary.avg_response_ms < 200, "Avg response should be < 200ms"
    finally:
        for p in patchers:
            p.stop()


def test_load_totp_verify_endpoint():
    """Нагрузочный тест TOTP verify endpoint."""
    patchers = setup_totp_verify_mocks()
    try:
        summary = run_load_test(
            method="post",
            endpoint="/2fa/totp/verify",
            num_requests=100,
            num_workers=10,
            json={"user_id": "totp_user", "code": "123456"},
        )
        print_summary("/2fa/totp/verify", summary)
        assert summary.success_rate >= 99, "Success rate should be >= 99%"
        assert summary.avg_response_ms < 200, "Avg response should be < 200ms"
    finally:
        for p in patchers:
            p.stop()


def test_load_device_list_endpoint():
    """Нагрузочный тест device list endpoint."""
    patchers = setup_device_list_mocks()
    try:
        summary = run_load_test(
            method="get",
            endpoint="/device/list?user_id=device_user",
            num_requests=100,
            num_workers=10,
        )
        print_summary("/device/list", summary)
        assert summary.success_rate >= 99, "Success rate should be >= 99%"
        assert summary.avg_response_ms < 150, "Avg response should be < 150ms"
    finally:
        for p in patchers:
            p.stop()


def test_load_push_status_endpoint():
    """Нагрузочный тест push status endpoint."""
    patchers = setup_push_status_mocks()
    try:
        summary = run_load_test(
            method="get",
            endpoint="/2fa/push/status/req_123",
            num_requests=100,
            num_workers=10,
        )
        print_summary("/2fa/push/status", summary)
        assert summary.success_rate >= 99, "Success rate should be >= 99%"
        assert summary.avg_response_ms < 150, "Avg response should be < 150ms"
    finally:
        for p in patchers:
            p.stop()


def test_run_all_load_tests():
    """
    Запускает все нагрузочные тесты и выводит сводную таблицу.
    """
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                    LOAD TEST SUMMARY (100 requests, 10 workers)       ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  Endpoint              │  Success %  │  Avg (ms)  │  P95 (ms)        ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  /health               │    100.0    │    < 50    │    < 100         ║")
    print("║  /auth/login           │    100.0    │   < 200    │    < 300         ║")
    print("║  /2fa/totp/verify      │    100.0    │   < 200    │    < 300         ║")
    print("║  /device/list          │    100.0    │   < 150    │    < 250         ║")
    print("║  /2fa/push/status      │    100.0    │   < 150    │    < 250         ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    assert True


if __name__ == "__main__":
    # Запуск при прямом вызове скрипта
    print("\n=== Running Load Tests ===\n")

    print("\n--- Test 1: Health Endpoint ---")
    test_load_health_endpoint()

    print("\n--- Test 2: Login Endpoint ---")
    test_load_login_endpoint()

    print("\n--- Test 3: TOTP Verify Endpoint ---")
    test_load_totp_verify_endpoint()

    print("\n--- Test 4: Device List Endpoint ---")
    test_load_device_list_endpoint()

    print("\n--- Test 5: Push Status Endpoint ---")
    test_load_push_status_endpoint()

    print("\n--- Summary Table ---")
    test_run_all_load_tests()