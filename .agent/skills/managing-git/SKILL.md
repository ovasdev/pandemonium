---
name: managing-git
description: "Manages git operations in the project: status, commits, branches, diffs, logs, PRs, stashing, rebasing, merging. Triggers when the user asks to commit, push, create a branch, check status, view log/history, create a PR, stash, rebase, merge, cherry-pick, or any other git-related action. Also triggers on: 'закоммить', 'запуши', 'создай ветку', 'создай PR', 'покажи лог', 'покажи историю', 'покажи статус', 'покажи диф', 'стэшни', 'замерджи', 'ребейзни'. Does NOT trigger for bot lifecycle management (restart/stop) or code writing tasks."
---

# Managing Git

Git operations for the Pandemonium bot project.

## Safety Rules

These rules prevent data loss and maintain clean history:

- **Never force-push to main/master.** Force-push to feature branches only with explicit user confirmation.
- **Never run destructive commands** (`reset --hard`, `clean -f`, `checkout .`, `branch -D`) without user confirmation — these discard work that may not be recoverable.
- **Never skip hooks** (`--no-verify`, `--no-gpg-sign`) unless the user explicitly requests it. If a hook fails, investigate the root cause.
- **Prefer new commits over amending.** Amending rewrites history and can destroy the previous commit's content if something was staged incorrectly.
- **Stage files explicitly** (`git add <file>`) rather than `git add -A` or `git add .` — avoids accidentally committing secrets, logs, or IDE files.

## Decision Tree

```
What does the user want?
├─ View state (status/diff/log)     → Status & Inspection
├─ Commit changes                   → Committing
├─ Create/switch branch             → Branch Management
├─ Push to remote                   → Pushing
├─ Create a pull request            → Pull Requests
├─ Stash changes                    → Stashing
├─ Merge/rebase                     → Merging & Rebasing
├─ Undo something                   → Undoing (confirm with user first!)
└─ Other git operation              → Run the command, apply safety rules
```

## Status & Inspection

```bash
# Current state
git status

# Diff of working tree (unstaged)
git diff

# Diff of staged changes
git diff --cached

# Recent history (compact)
git log --oneline -20

# Detailed history with diffs
git log -p -5

# What changed between branches
git diff main...HEAD

# Blame a specific file
git blame <file>
```

Never use `git status -uall` — it causes memory issues on large repos.

## Committing

Follow this sequence:

1. **Review** what will be committed:
   ```bash
   git status
   git diff
   git diff --cached
   ```

2. **Check recent commit style** to match conventions:
   ```bash
   git log --oneline -10
   ```

3. **Stage specific files** (not `git add .`):
   ```bash
   git add src/pandemonium/tgbot/file.py tests/test_file.py
   ```

4. **Commit with HEREDOC** for proper formatting:
   ```bash
   git commit -m "$(cat <<'EOF'
   sprint 3: add token budget tracking

   Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

Project convention for sprint work: `sprint N: краткое описание`.

Never commit files that likely contain secrets (`.env`, `credentials.json`, `config.yaml` with tokens). Warn the user if they request it.

## Branch Management

```bash
# List branches
git branch -a

# Create and switch to new branch
git checkout -b feature/branch-name

# Switch to existing branch
git checkout branch-name

# Delete local branch (safe — refuses if unmerged)
git branch -d branch-name

# Delete local branch (force — confirm with user!)
git branch -D branch-name
```

## Pushing

```bash
# Push current branch, set upstream
git push -u origin branch-name

# Push (upstream already set)
git push
```

Always confirm before pushing — it affects the remote and is visible to others.

Never force-push to main/master. For feature branches, confirm before `--force-with-lease`.

## Pull Requests

Use `gh` CLI for all GitHub operations:

```bash
# Create PR
gh pr create --title "Title" --body "$(cat <<'EOF'
## Summary
- Change 1
- Change 2

## Test plan
- [ ] Tests pass
- [ ] Manual verification

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"

# View PR
gh pr view <number>

# List PRs
gh pr list

# Check PR status/checks
gh pr checks <number>

# View PR comments
gh api repos/{owner}/{repo}/pulls/{number}/comments
```

Before creating a PR:
1. Check `git status` and `git diff` for uncommitted changes
2. Review all commits with `git log main...HEAD` and `git diff main...HEAD`
3. Push to remote if needed

## Stashing

```bash
# Stash working changes
git stash

# Stash with description
git stash push -m "description"

# List stashes
git stash list

# Apply most recent stash (keep in stash list)
git stash apply

# Pop most recent stash (remove from stash list)
git stash pop

# Apply specific stash
git stash apply stash@{2}
```

## Merging & Rebasing

```bash
# Merge branch into current
git merge branch-name

# Rebase current branch onto main
git rebase main
```

Never use `git rebase -i` or `git add -i` — interactive mode is not supported in this environment.

Never use `--no-edit` with rebase — it is not a valid rebase option.

If merge conflicts arise, investigate and resolve them rather than discarding changes.

## Undoing

All undo operations require user confirmation — they can destroy work.

```bash
# Undo last commit, keep changes staged
git reset --soft HEAD~1

# Undo last commit, keep changes unstaged
git reset HEAD~1

# Discard all changes (DESTRUCTIVE — confirm first!)
git reset --hard HEAD

# Revert a specific commit (safe — creates new commit)
git revert <commit-hash>
```

Prefer `git revert` over `git reset` when the commit has been pushed — revert is safe and doesn't rewrite history.

## Debugging

| Symptom | Cause | Fix |
|---|---|---|
| `git status -uall` hangs | Large repo with many untracked files | Use `git status` without `-uall` |
| Hook failure on commit | Pre-commit hook found issues | Fix the issue, stage again, create a **new** commit (don't amend) |
| Merge conflict during rebase | Divergent changes | Resolve conflicts file by file, `git add`, `git rebase --continue` |
| `push` rejected | Remote has new commits | `git pull --rebase` then push again |
