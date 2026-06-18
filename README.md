# ai-skills

Personal AI skills for opencode, Claude Code, and other agent tools that understand the `SKILL.md` format.

## Layout

Each skill lives in its own directory:

```text
ai-skills/
  update-aur-package/
    SKILL.md
  send-slack-message/
    SKILL.md
```

Every `SKILL.md` starts with YAML frontmatter:

```markdown
---
name: update-aur-package
description: Update Arch/AUR PKGBUILD packages. Use when bumping pkgver, refreshing checksums, regenerating .SRCINFO, verifying sources, committing, or pushing AUR package updates.
---
```

Use lowercase, hyphen-separated skill names. Keep descriptions specific and include the words or filenames that should trigger the skill.

## Available Skills

- `update-aur-package`: repeatable workflow for updating Arch/AUR packages that use `PKGBUILD` and `.SRCINFO`.
- `send-slack-message`: safe workflow for sending Slack bot messages with `SLACK_BOT_TOKEN` and `chat.postMessage`.

## opencode Setup

The recommended setup is to make this repository discoverable from opencode's global skills directory:

```bash
mkdir -p ~/.config/opencode/skills
ln -s ~/code/ai-skills ~/.config/opencode/skills/shared
```

With that symlink, opencode scans skills like:

```text
~/.config/opencode/skills/shared/update-aur-package/SKILL.md
```

Restart opencode after adding or changing skills. opencode loads skills at startup.

## Claude Code Setup

Claude Code can use the same repository through a symlink:

```bash
mkdir -p ~/.claude/skills
ln -s ~/code/ai-skills ~/.claude/skills/shared
```

## Maintenance

- Keep skills tool-neutral unless a workflow needs a specific agent.
- Prefer precise checklists over vague guidance.
- Include verification steps for workflows that modify files, publish packages, or run deployments.
- Avoid secrets, private tokens, or machine-specific credentials in skills.
