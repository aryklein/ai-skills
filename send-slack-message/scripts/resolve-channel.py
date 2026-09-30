#!/usr/bin/env python3
"""Resolve a Slack channel name using the bot token in the environment."""

import argparse
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def fetch_page(token, cursor):
    query = urlencode({
        "types": "public_channel,private_channel",
        "limit": 200,
        "cursor": cursor,
    })
    request = Request(
        f"https://slack.com/api/conversations.list?{query}",
        headers={"Authorization": f"Bearer {token}"},
    )
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                page = json.load(response)
        except HTTPError as error:
            retry_after = error.headers.get("Retry-After", "1")
            status = error.code
            error.close()
            if status == 429 and attempt < 3:
                try:
                    delay = max(1, int(retry_after))
                except ValueError:
                    raise RuntimeError("Slack returned an invalid Retry-After header.") from None
                time.sleep(delay)
                continue
            raise RuntimeError(f"Slack lookup failed: HTTP {status}.") from None
        except (URLError, TimeoutError, OSError):
            raise RuntimeError("Slack lookup failed: connection error or timeout.") from None
        except (ValueError, UnicodeError):
            raise RuntimeError("Slack returned invalid JSON.") from None

        if not isinstance(page, dict):
            raise RuntimeError("Slack returned an invalid response.")
        if page.get("ok") is not True:
            error = page.get("error", "unknown_error")
            needed = page.get("needed")
            detail = f" (required scopes: {needed})" if needed else ""
            raise RuntimeError(f"Slack lookup failed: {error}{detail}.")
        return page
    raise RuntimeError("Slack rate-limit retries exhausted.")


def resolve_channel(token, name):
    cursor = ""
    seen_cursors = set()
    while True:
        page = fetch_page(token, cursor)
        for channel in page.get("channels", []):
            if channel.get("name") == name:
                return channel["id"]
        cursor = (page.get("response_metadata") or {}).get("next_cursor", "").strip()
        if not cursor:
            raise RuntimeError(
                f"Channel #{name} was not found after searching all accessible pages. "
                "Confirm the channel name/workspace, provide an ID, or invite the bot."
            )
        if cursor in seen_cursors:
            raise RuntimeError("Slack returned a repeated pagination cursor.")
        seen_cursors.add(cursor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channel", help="Channel name, with or without a leading #")
    parser.add_argument("--token-env", default="SLACK_BOT_TOKEN",
                        help="Environment variable containing the bot token")
    args = parser.parse_args()
    name = args.channel.removeprefix("#")
    if not name:
        parser.error("a nonempty channel name is required")
    token = os.environ.get(args.token_env)
    if not token:
        print(f"Set {args.token_env} before resolving a channel.", file=sys.stderr)
        return 1
    try:
        channel_id = resolve_channel(token, name)
    except RuntimeError as error:
        print(str(error).replace(token, "[REDACTED]"), file=sys.stderr)
        return 1
    print(channel_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
