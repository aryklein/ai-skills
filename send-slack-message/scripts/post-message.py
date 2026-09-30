#!/usr/bin/env python3
"""Post a Slack message from stdin using a bot token read from the environment."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def post_message(token, channel, text, thread_ts=None):
    payload = {"channel": channel, "text": text}
    if thread_ts is not None:
        payload["thread_ts"] = thread_ts
    request = Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    # Do not retry a write automatically: a lost response may hide a successful post.
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except HTTPError as error:
        status = error.code
        retry_after = error.headers.get("Retry-After") if error.headers else None
        error.close()
        if status == 429:
            try:
                delay = int(retry_after)
                if delay < 0:
                    raise ValueError
            except (TypeError, ValueError):
                detail = "Slack did not provide a valid Retry-After delay; the retry window is unknown."
            else:
                detail = f"Wait at least {delay} seconds before explicitly retrying."
            raise RuntimeError(
                f"Slack rate limit reached (HTTP 429). {detail} "
                "No automatic retry was attempted. Check the destination before retrying."
            ) from None
        raise RuntimeError(
            f"Slack posting returned HTTP {status}. Check the destination before retrying."
        ) from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError(
            "Slack posting failed: connection error or timeout. "
            "Delivery is uncertain; check the destination before retrying."
        ) from None
    except (ValueError, UnicodeError):
        raise RuntimeError(
            "Slack returned invalid JSON. Check the destination before retrying."
        ) from None
    if not isinstance(result, dict):
        raise RuntimeError("Slack returned an invalid response. Check the destination before retrying.")
    if result.get("ok") is not True:
        error = result.get("error", "unknown_error")
        needed = result.get("needed")
        detail = f" (required scopes: {needed})" if needed else ""
        raise RuntimeError(f"Slack posting failed: {error}{detail}.")
    if not all(isinstance(result.get(key), str) and result[key] for key in ("channel", "ts")):
        raise RuntimeError("Slack omitted the message receipt. Check the destination before retrying.")
    return {"ok": True, "channel": result["channel"], "ts": result["ts"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channel", help="Resolved channel ID, user ID, or conversation ID")
    parser.add_argument("--thread-ts", help="Parent message timestamp for a threaded reply")
    parser.add_argument("--token-env", default="SLACK_BOT_TOKEN",
                        help="Environment variable containing the bot token")
    args = parser.parse_args()
    token = os.environ.get(args.token_env)
    if not token:
        print(f"Set {args.token_env} before posting a message.", file=sys.stderr)
        return 1
    text = sys.stdin.read()
    if not text.strip():
        print("Provide a nonempty message on stdin.", file=sys.stderr)
        return 1
    try:
        result = post_message(token, args.channel, text, args.thread_ts)
    except RuntimeError as error:
        print(str(error).replace(token, "[REDACTED]"), file=sys.stderr)
        return 1
    print(json.dumps(result).replace(token, "[REDACTED]"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
