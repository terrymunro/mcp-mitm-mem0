#!/usr/bin/env python3
"""Test script to test the mitmproxy addon with a sample Claude request."""

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
                {"type": "text", "text": "Hello Claude! I am working on a Python project involving machine learning."}
            ],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "Hello! That sounds interesting. What specific aspects of machine learning are you working on? Are you focusing on data preprocessing, model training, or something else?",
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "I'm working on natural language processing, specifically sentiment analysis of customer reviews.",
                }
            ],
        },
    ],
}


def start_mitm_proxy():
    """Start mitmproxy with our addon."""
    print("Starting mitmproxy with memory addon...")

    # Start mitmproxy with the addon
    cmd = ["mitmdump", "-s", "./memory_addon.py", "--listen-port", "8888", "--set", "confdir=~/.mitmproxy"]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Give it time to start
    time.sleep(3)
    return process


def send_test_request():
    """Send a test request through the proxy."""
    print("Sending test Claude request through proxy...")

    # Configure proxy
    proxies = {"http": "http://127.0.0.1:8888", "https": "http://127.0.0.1:8888"}

    headers = {"Content-Type": "application/json", "X-User-Id": "test-mitm-user", "anthropic-beta": "claude-code"}

    try:
        # Send request through the proxy
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            json=CLAUDE_REQUEST,
            headers=headers,
            proxies=proxies,
            verify=False,  # Disable SSL verification for the proxy
            timeout=10,
        )
        print(f"Request sent. Status code: {response.status_code}")
        return True
    except requests.RequestException as e:
        print(f"Request failed (expected): {e}")
        return False


def test_addon():
    """Test the mitmproxy addon."""
    mitm_process = None

    try:
        # Start mitmproxy
        mitm_process = start_mitm_proxy()

        print("Waiting for mitmproxy to be ready...")
        time.sleep(5)

        # Send test request
        send_test_request()

        # Wait a bit for processing
        time.sleep(3)

        print("\\nChecking mitmproxy output...")

    except Exception as e:
        print(f"Error during testing: {e}")

    finally:
        if mitm_process:
            print("Terminating mitmproxy...")
            mitm_process.terminate()

            # Wait for termination and capture output
            stdout, stderr = mitm_process.communicate(timeout=10)

            print("\\n=== MITMPROXY STDOUT ===")
            print(stdout)
            print("\\n=== MITMPROXY STDERR ===")
            print(stderr)


if __name__ == "__main__":
    test_addon()
