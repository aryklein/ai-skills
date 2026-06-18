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

## Workflow

1. Confirm token availability without printing it.

Run a quiet environment check such as:

```bash
test -n "$SLACK_BOT_TOKEN"
```

If the token is missing, ask the user to make `SLACK_BOT_TOKEN` available in the shell. Do not ask them to paste the token into chat unless there is no safer option.

2. Identify the destination.

Use a channel ID, user ID, or conversation ID directly when available. If the user gives a channel name such as `#team-updates` or `team-updates`, resolve it to an ID before posting.

Channel name resolution requires `jq` and Slack read scopes. Use `conversations.list` and do not print the token:

```bash
channel_name="${CHANNEL_NAME#\#}"
channel_id=$(
  curl -sS https://slack.com/api/conversations.list \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    --get \
    --data-urlencode "types=public_channel,private_channel" \
    --data-urlencode "limit=1000" |
  jq -r --arg name "$channel_name" '.channels[] | select(.name == $name) | .id' |
  head -n 1
)
```

If `channel_id` is empty, ask for the channel ID or ask the user to invite the bot to the channel. Public channel lookup commonly requires `channels:read`; private channel lookup commonly requires `groups:read` and bot membership.

3. Build the Slack API request safely.

Use `chat.postMessage` for normal messages:

```bash
curl -sS -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data '{"channel":"<channel-id>","text":"<message>"}'
```

For a threaded reply, include `thread_ts`:

```bash
curl -sS -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data '{"channel":"<channel-id>","text":"<message>","thread_ts":"<thread-ts>"}'
```

When the message contains quotes, newlines, backslashes, or other JSON-sensitive characters, use a JSON-safe construction method instead of hand-written JSON. For example, if `jq` is available:

```bash
payload=$(jq -n --arg channel "<channel-id>" --arg text "<message>" '{channel: $channel, text: $text}')
curl -sS -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  --data "$payload"
```

4. Verify the response.

Check the Slack JSON response for `"ok": true`. Report success with the channel and timestamp when available. Do not include the token or authorization header.

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
