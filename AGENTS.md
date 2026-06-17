# AGENTS.md

## Repo Shape

- This repo stores reusable AI skills; each skill lives in its own directory with a `SKILL.md` file.
- `SKILL.md` files must start with YAML frontmatter containing `name` and `description`.
- Use lowercase, hyphen-separated skill names, matching the directory name when possible.
- Keep descriptions specific and include trigger words or filenames that should cause an agent to load the skill.

## Setup Quirks

- opencode can discover this repo when symlinked under `~/.config/opencode/skills/`, for example as `~/.config/opencode/skills/shared`.
- Claude Code can discover it when symlinked under `~/.claude/skills/`.
- Restart opencode after adding or changing skills; skills are loaded at startup.

## Editing Guidance

- Keep skills tool-neutral unless a workflow genuinely depends on one agent or tool.
- Prefer precise executable checklists over broad advice.
- Include verification steps for workflows that modify files, publish packages, or deploy.
- Do not include secrets, private tokens, or machine-specific credentials.

## Verification

- There is no build, test, lint, or formatter config in this repo.
- For skill changes, manually verify Markdown readability and YAML frontmatter before finishing.
