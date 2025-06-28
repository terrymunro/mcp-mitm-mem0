#!/usr/bin/env python3
"""Simple test addon for mitmproxy that just logs Claude requests."""

import json

from mitmproxy import http


def request(flow: http.HTTPFlow) -> None:
    """
    This is a request hook that logs Claude requests.

    Args:
        flow: The HTTP flow.
    """
    print(f"[Simple Test Addon] Request to: {flow.request.pretty_url}")

    # Check if this looks like a Claude request
    if "anthropic.com" in flow.request.pretty_url and "application/json" in flow.request.headers.get(
        "content-type", ""
    ):
        print("[Simple Test Addon] Detected Claude API request")

        try:
            raw_text = flow.request.get_text()
            data = json.loads(str(raw_text))

            if "messages" in data:
                messages = data["messages"]
                print(f"[Simple Test Addon] Found {len(messages)} messages")

                for i, msg in enumerate(messages):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", [])

                    print(f"[Simple Test Addon] Message {i + 1}: role={role}")

                    # Extract text content
                    for content_item in content:
                        if content_item.get("type") == "text":
                            text = content_item.get("text", "")[:100]  # First 100 chars
                            print(f"[Simple Test Addon]   Text: {text}...")

                print("[Simple Test Addon] ✓ Successfully parsed and logged Claude request")

        except json.JSONDecodeError as e:
            print(f"[Simple Test Addon] JSON decode error: {e}")
        except Exception as e:
            print(f"[Simple Test Addon] Error processing request: {e}")
    else:
        print("[Simple Test Addon] Not a Claude request, skipping")
