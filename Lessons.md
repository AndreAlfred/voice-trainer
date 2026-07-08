# Lessons — Voice Trainer

A running reliquary of wrong turns, mistakes, and hard-won corrections, so we
don't repeat them.

**Rules for this file**
- Add an entry whenever something goes wrong, surprises us, or we course-correct.
- Prune entries once they go stale or stop being relevant.
- When a lesson proves durable and general, **promote** it into
  [CLAUDE.md](CLAUDE.md) as a standing rule and trim it back here.

Format — `### YYYY-MM-DD — Short title`, then: what happened / why it bit us /
the fix.

---

### 2026-07-07 — Deleting a word doesn't remove it from git history
**What happened:** Before the first public push we needed to remove a product
name from a design doc. Editing the current file wasn't enough — the word lived
in every past commit's snapshot and would have stayed world-readable via
`git checkout <old-commit>`.
**Fix:** Rewrote all history with `git filter-repo --replace-text` *before*
pushing, then verified across the working tree, commit messages, and full history.
**Rule:** Scrub sensitive strings BEFORE the first push. Afterward the same fix
needs a force-push and may already be cached upstream.

### 2026-07-07 — Git invents a leaky author email from your machine
**What happened:** With no `user.email` configured, git authored commits as
`username@hostname.local`, exposing the local username and machine name in
public commit metadata.
**Fix:** Set a repo-local git identity using the GitHub `noreply` email, so new
commits are clean.
**Open item:** Commits made before this fix still carry the old `.local` email;
scrubbing those needs a history rewrite + force-push (optional, low urgency —
it's a non-deliverable address).
