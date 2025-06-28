#!/usr/bin/env python3
"""
Demonstration of observability features in the MCP MITM Mem0 API.

This script demonstrates:
1. Structured JSON logging with correlation IDs
2. Prometheus metrics collection
3. Health monitoring
4. Request tracing
"""

import json
import time
import uuid

import requests


def demo_correlation_ids():
    """Demonstrate correlation ID usage."""
    print("🔗 Correlation ID Demo")
    print("=" * 50)

    base_url = "http://localhost:8000"

    # Generate a unique correlation ID for this request chain
    correlation_id = str(uuid.uuid4())

    print(f"Generated correlation ID: {correlation_id}")

    # Make multiple requests with the same correlation ID
    endpoints = ["/health", "/metrics"]

    for endpoint in endpoints:
        print(f"\n📍 Making request to {endpoint}")

        headers = {"X-Request-ID": correlation_id}

        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers)

            # Check if correlation ID is returned in response
            response_correlation_id = response.headers.get("X-Request-ID")

            if response_correlation_id == correlation_id:
                print(f"✅ Correlation ID maintained: {response_correlation_id}")
            else:
                print("❌ Correlation ID mismatch")

            print(f"   Status: {response.status_code}")

        except Exception as e:
            print(f"❌ Request failed: {e}")

    print(
        f"\n💡 All requests with correlation ID {correlation_id} can be traced in logs"
    )


def demo_health_monitoring():
    """Demonstrate health endpoint capabilities."""
    print("\n🏥 Health Monitoring Demo")
    print("=" * 50)

    base_url = "http://localhost:8000"

    try:
        response = requests.get(f"{base_url}/health")

        if response.status_code == 200:
            health_data = response.json()

            print("Health Status:")
            print(f"  Overall Status: {health_data.get('status', 'unknown')}")
            print(
                f"  Memory Service: {'✅ Available' if health_data.get('memory_service_available') else '❌ Unavailable'}"
            )
            print(f"  Version: {health_data.get('version', 'unknown')}")
            print(f"  Timestamp: {health_data.get('timestamp', 'unknown')}")
            print(f"  Correlation ID: {health_data.get('correlation_id', 'none')}")

        elif response.status_code == 503:
            print("⚠️  Service is in degraded state")
            try:
                error_data = response.json()
                print(f"Details: {error_data}")
            except:
                print(f"Response: {response.text}")
        else:
            print(f"❌ Health check failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Health check request failed: {e}")


def demo_prometheus_metrics():
    """Demonstrate Prometheus metrics."""
    print("\n📊 Prometheus Metrics Demo")
    print("=" * 50)

    base_url = "http://localhost:8000"

    try:
        response = requests.get(f"{base_url}/metrics")

        if response.status_code == 200:
            metrics_data = response.text

            print("Available Metrics:")

            # Parse and display key metrics
            key_metrics = [
                "http_requests_total",
                "http_request_duration_seconds",
                "memory_operations_total",
                "active_connections",
                "memory_service_available",
            ]

            for metric in key_metrics:
                if metric in metrics_data:
                    print(f"  ✅ {metric}")

                    # Extract metric lines for display
                    lines = [
                        line
                        for line in metrics_data.split("\n")
                        if metric in line and not line.startswith("#")
                    ]
                    for line in lines[:3]:  # Show first 3 instances
                        if line.strip():
                            print(f"     {line.strip()}")
                    if len(lines) > 3:
                        print(f"     ... and {len(lines) - 3} more")
                else:
                    print(f"  ❌ {metric} (not found)")

            print(f"\n📈 Total metrics response size: {len(metrics_data)} bytes")

        else:
            print(f"❌ Metrics endpoint failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Metrics request failed: {e}")


def demo_request_tracing():
    """Demonstrate request tracing across multiple operations."""
    print("\n🔍 Request Tracing Demo")
    print("=" * 50)

    base_url = "http://localhost:8000"
    trace_id = str(uuid.uuid4())

    print(f"Trace ID: {trace_id}")
    print("\nSimulating a user session with multiple requests...")

    # Simulate a sequence of requests that a user might make
    requests_sequence = [
        ("Health Check", "GET", "/health"),
        ("Check Metrics", "GET", "/metrics"),
        ("Another Health Check", "GET", "/health"),
    ]

    for i, (description, method, endpoint) in enumerate(requests_sequence, 1):
        print(f"\n{i}. {description}")

        headers = {"X-Request-ID": trace_id}

        try:
            if method == "GET":
                response = requests.get(f"{base_url}{endpoint}", headers=headers)
            else:
                print(f"   Method {method} not implemented in demo")
                continue

            print(f"   Status: {response.status_code}")
            print(
                f"   Correlation ID: {response.headers.get('X-Request-ID', 'missing')}"
            )

            # Small delay to simulate real usage
            time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Request failed: {e}")

    print(f"\n💡 All requests in this session can be traced using trace ID: {trace_id}")
    print("   Check server logs for JSON entries containing this correlation_id")


def demo_json_logging():
    """Demonstrate JSON logging capabilities."""
    print("\n📋 JSON Logging Demo")
    print("=" * 50)

    print(
        "The application now uses structured JSON logging with the following features:"
    )
    print("  ✅ All log entries are in JSON format")
    print("  ✅ Correlation IDs are included in log context")
    print("  ✅ Request metadata (method, URL, user ID) is logged")
    print("  ✅ Memory operations are tracked with detailed context")
    print("  ✅ Error logs include correlation IDs for debugging")

    print("\nExample log entry structure:")
    example_log = {
        "timestamp": "2024-01-01T12:00:00.000Z",
        "logger": "mcp_mitm_mem0.api",
        "level": "INFO",
        "message": "Health check performed",
        "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "healthy",
        "memory_service_available": True,
        "version": "1.0.0",
    }

    print(json.dumps(example_log, indent=2))

    print("\n💡 Check your server logs to see actual JSON formatted entries!")


def main():
    """Run all observability demos."""
    print("🚀 MCP MITM Mem0 - Observability Features Demo")
    print("=" * 60)

    print("This demo showcases the observability features implemented in Phase 5:")
    print("  • Structured JSON logging with correlation IDs")
    print("  • Prometheus metrics collection")
    print("  • Enhanced health monitoring")
    print("  • Request tracing capabilities")

    print("\n⚠️  Make sure the API server is running on http://localhost:8000")
    input("Press Enter to continue...")

    # Run all demos
    try:
        demo_correlation_ids()
        demo_health_monitoring()
        demo_prometheus_metrics()
        demo_request_tracing()
        demo_json_logging()

        print("\n" + "=" * 60)
        print("🎉 Observability Demo Complete!")
        print("=" * 60)

        print("\nNext Steps:")
        print("  1. Check server logs for JSON formatted entries")
        print("  2. Monitor Prometheus metrics at /metrics")
        print("  3. Use correlation IDs for request tracing")
        print("  4. Set up log aggregation (ELK, Fluentd, etc.)")
        print("  5. Configure Prometheus scraping")

    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")


if __name__ == "__main__":
    main()
