# BudakGPT Organization Infrastructure

This is the organization's special `.github` repository. It does two things:

1. **`profile/README.md`** renders as the public landing page at
   `github.com/BudakGPT`. It is a status dashboard built automatically from every
   competition tracker.
2. **Operational tooling** in `ops/` creates competitions and publishes code.

## How the dashboard works

`scripts/rollup.py`, run daily and on demand by `.github/workflows/rollup.yml`:

1. Lists every repository in the org tagged with the `competition` topic.
2. Reads each repository's `competition.yml`.
3. Regenerates the dashboard, grouped by status (Active, Submitted, Upcoming,
   Awarded, Archive), with the active group sorted by nearest deadline.

Discovery is by topic, not by name, so trackers can be named freely.

## Tooling

```powershell
# Create a competition: a public tracker plus an optional private code repo.
./ops/new-competition.ps1 -Name "AI Innovation Challenge" -Repo "aiic-compfest18" -Organizer "COMPFEST 18" -WithCode

# After judging, flip the code repository to public.
./ops/publish-code.ps1 -Repo "aiic-compfest18-app"
```

## The model

| Layer | Repository | Visibility | Source of truth |
| :--- | :--- | :--- | :--- |
| Context and dashboard | tracker (from `competition-template`) | Public | `competition.yml` |
| Project code | separate code repo | Private during, public after | the code itself |

The dashboard region of every tracker is identical, which is what makes the
rollup possible. The narrative sections beneath it are free-form per
competition, and the per-competition accent and banner give each one its own
identity.

## Notes

- Self-updating commits are authored by `github-actions[bot]`, the standard
  GitHub automation actor, as expected for a README that refreshes itself.
- The rollup reads only public trackers, so private code repositories require no
  special tokens.
