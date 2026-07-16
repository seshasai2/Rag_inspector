"""HTTP RED metrics recording + exposition."""

from app.core.http_metrics import (
    record_http_request,
    render_http_metrics_lines,
    reset_http_metrics_for_tests,
)


def test_http_metrics_record_and_render():
    reset_http_metrics_for_tests()
    record_http_request("GET", "/api/v1/ops/live", 200, 0.012)
    record_http_request("GET", "/api/v1/ops/live", 200, 0.008)
    record_http_request("POST", "/api/v1/auth/login", 401, 0.05)
    lines = "\n".join(render_http_metrics_lines())
    assert "raginspector_http_requests_total" in lines
    assert 'method="GET"' in lines
    assert 'status="200"' in lines
    assert "raginspector_http_request_duration_seconds_bucket" in lines
    assert "raginspector_http_request_duration_seconds_sum" in lines
    reset_http_metrics_for_tests()


def test_http_metrics_normalizes_uuid_paths():
    reset_http_metrics_for_tests()
    record_http_request(
        "GET",
        "/api/v1/pipelines/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        200,
        0.02,
    )
    lines = "\n".join(render_http_metrics_lines())
    assert "{id}" in lines
    assert "aaaaaaaa-bbbb" not in lines
    reset_http_metrics_for_tests()
