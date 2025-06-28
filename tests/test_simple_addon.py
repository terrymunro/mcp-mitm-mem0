#!/usr/bin/env python3
"""Test script for the simple mitmproxy addon."""

import subprocess
import time

import requests

# Sample Claude request payload
CLAUDE_REQUEST = {
    "model": "claude-sonnet-3.5",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Hello Claude! I am working on a Python project involving machine learning.",
                }
            ],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "Hello! That sounds interesting. What specific aspects of machine learning are you working on?",
                }
            ],
        },
    ],
}


def test_simple_addon():
    """Test the simple mitmproxy addon."""
    print("Starting mitmproxy with simple test addon...")

    # Start mitmproxy with the simple addon
    mitm_process = subprocess.Popen(
        ["mitmdump", "-s", "./simple_test_addon.py", "--listen-port", "8889"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Give it time to start
        time.sleep(3)

        print("Sending test request through proxy...")

        # Configure proxy
        proxies = {"http": "http://127.0.0.1:8889", "https": "http://127.0.0.1:8889"}

        headers = {
            "Content-Type": "application/json",
            "X-User-Id": "test-simple-user",
            "anthropic-beta": "claude-code",
        }

        # Send request through the proxy
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                json=CLAUDE_REQUEST,
                headers=headers,
                proxies=proxies,
                verify=False,
                timeout=10,
            )
            print(f"Request sent. Status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Request failed (expected): {e}")

        # Wait for processing
        time.sleep(2)

    finally:
        print("Terminating mitmproxy...")
        mitm_process.terminate()

        # Capture output
        stdout, stderr = mitm_process.communicate(timeout=10)

        print("\\n=== MITMPROXY OUTPUT ===")
        print(stdout)
        if stderr:
            print("\\n=== MITMPROXY STDERR ===")
            print(stderr)


if __name__ == "__main__":
    test_simple_addon()
