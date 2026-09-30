---
name: send-slack-message
description: Send Slack messages with a bot token. Use when asked to post, send, or reply to a Slack channel, Slack DM, Slack thread, or chat.postMessage using SLACK_BOT_TOKEN.
---

# Send Slack Message

Use this workflow when sending a Slack message from an installed bot.

## Requirements

- Use the bot token from `SLACK_BOT_TOKEN` unless the user explicitly names another environment variable.
- Never print, log, echo, summarize, or expose Slack tokens.
- Prefer Slack channel IDs such as `C01LA1HJV8F` when available, but resolve channel names automatically.
- Ask for the destination and message text if either is missing.
- Ask for a thread timestamp only when the user wants a threaded reply and has not provided one.
- Treat posting to Slack as an external side effect; only send when the user clearly asks to send/post/reply.
- Prefer a readable Slack-native style with concise icons or emoji for status and sections, such as `✅`, `🚨`, `🔎`, `🛠️`, `📌`, and `➡️`, unless the user asks for plain text.
- Do not send literal `\n` text in Slack messages. Use real newline characters in the message body, or keep the message as a single paragraph if newlines are not needed.

## Workflow

1. Select the token environment variable.

Set `token_env=SLACK_BOT_TOKEN`, or set it to the environment variable name explicitly provided by the user. Pass the same `--token-env "$token_env"` to both helpers. This variable contains only a name, never the token itself. Both helpers check that the selected variable is nonempty without printing its value.

If the token is missing, ask the user to make the selected environment variable available in the shell. Do not ask them to paste the token into chat.

2. Identify the destination.

Use a channel ID, user ID, or conversation ID directly when available. If the user gives a channel name such as `#team-updates` or `team-updates`, resolve it to an ID before posting.

Channel name resolution requires Python 3.9+ and Slack read scopes. Run the bundled resolver using its absolute path, resolved relative to this `SKILL.md` file (not the current project directory):

```bash
token_env=SLACK_BOT_TOKEN  # Replace only with the user-selected environment variable name.
python3 "/absolute/path/to/send-slack-message/scripts/resolve-channel.py" \
  '#team-updates' --token-env "$token_env"
```

The resolver reads `SLACK_BOT_TOKEN` from the environment and prints only the channel ID on success. If the user names another token environment variable, pass `--token-env VARIABLE_NAME`; never pass the token itself as an argument. It uses only Python's standard library, follows `response_metadata.next_cursor` even through short or empty pages, and stops as soon as it finds an exact channel-name match. HTTP `429` responses are retried up to three times per page after waiting for `Retry-After`.

On failure, it prints a diagnostic to stderr and exits nonzero. Do not post after a failed lookup. Handle API or transport errors explicitly; do not treat them as "channel not found." Only ask for an ID or a bot invitation after the resolver reports that all accessible pages have been searched, or explains an access limitation. Public lookup requires `channels:read`; private lookup requires `groups:read` and bot membership. The resolver requests both channel types, so the token needs both read scopes.

3. Post using the bundled Python helper.

`post-message.py` requires Python 3.9+ and uses only the standard library. It reads the selected token internally, builds JSON safely, and calls `chat.postMessage`. Never pass a token or expanded Authorization header as a command-line argument (including `curl -H`), because process inspection can expose arguments.

Use the same `token_env` selected above, including when the destination ID was provided directly. Supply the message on stdin. A quoted heredoc preserves quotes, backslashes, emoji, and real newlines without shell expansion:

```bash
python3 "/absolute/path/to/send-slack-message/scripts/post-message.py" \
  '<channel-id>' --token-env "$token_env" <<'MESSAGE'
🛠️ Short title

✅ Key point with real line breaks
📌 Final status
MESSAGE
```

For a threaded reply, add `--thread-ts` with the parent message timestamp:

```bash
python3 "/absolute/path/to/send-slack-message/scripts/post-message.py" \
  '<channel-id>' --token-env "$token_env" --thread-ts '<thread-ts>' <<'MESSAGE'
Reply text goes here.
MESSAGE
```

Use absolute helper paths resolved relative to this `SKILL.md`, not the current project directory. Before posting, ensure the message contains actual line breaks, not visible `\n` sequences.

4. Verify the response.

The helper exits successfully only after Slack returns `"ok": true` with a channel and timestamp. It prints only that receipt; report success using it. On failure, it exits nonzero with a diagnostic. Do not include the token or authorization header.

The helper does not retry posting automatically. A connection error, timeout, or malformed response may occur after Slack accepted the message. Check the destination before retrying to avoid duplicate posts. For HTTP 429 rate limits, the helper reports the `Retry-After` delay in seconds; wait at least that long before an explicit retry. If Slack omits the header or returns an invalid delay, the helper reports that the retry window is unknown; do not assume an immediate retry is safe.

5. Handle common errors clearly.

- `channel_not_found`: the channel name or ID is wrong, the bot is not in the private channel, the bot lacks access, or the token belongs to a different workspace. Ask for a channel ID or bot invite.
- `missing_scope` during channel lookup: report the missing read scope. Common scopes are `channels:read` for public channels and `groups:read` for private channels.
- `not_in_channel`: ask the user to invite the bot to the channel, or use a channel where the bot is a member.
- `missing_scope`: report the missing scope. Common scopes are `chat:write` and sometimes `chat:write.public`.
- `invalid_auth` or `not_authed`: the token is absent, invalid, revoked, or from the wrong environment.
- `is_archived`: the destination channel is archived and cannot receive messages.

## Safety Notes

- Do not use `xapp-` app-level tokens for `chat.postMessage`; use an `xoxb-` bot token.
- Do not store tokens in files, command definitions, skill files, shell history snippets, or repository content.
- Do not send to broad channels like company-wide announcements unless the user explicitly names that destination and message.
- If the user asks for a preview, show the destination and message text but do not send until they confirm.
