# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Wayfinding operations

How the `/wayfinder` skill expresses maps, tickets, blocking, and the frontier in this repo. (This tracker lacks `gh`-accessible native issue dependencies, so blocking uses the body convention below.)

### Labels

- The **map** is a GitHub issue labelled `wayfinder:map`.
- Each **ticket** is a GitHub issue labelled `wayfinder:<type>`, one of: `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, `wayfinder:task`.

(All five labels already exist in this repo.)

### Parent / child

A ticket declares its map with a first-line body reference:

```
Map: #<map-number>
```

List a map's children: `gh issue list --state all --search "Map: #<map-number> in:body" --json number,title,state,labels,assignees`

### Blocking

A ticket declares its blockers with a body line (comma/space separated issue refs):

```
Blocked by: #<n>, #<m>
```

A ticket is **unblocked** when every issue it lists as `Blocked by:` is closed. Update the body line (`gh issue edit <number> --body ...`) if edges change; do not track blocking in comments.

### Frontier

The frontier = open children of the map that are **unblocked** and **unclaimed**. Compute it by listing the map's open children, then filtering out any whose `Blocked by:` references an open issue and any with an assignee.

### Claiming

A session claims a ticket by assigning it before any work: `gh issue edit <number> --add-assignee @me`. An open, unassigned ticket is unclaimed.

### Resolving

Post the answer as a resolution comment and close in one step: `gh issue close <number> --comment "Resolution: ..."`. Then append a one-line entry to the map's `## Decisions so far` section (`gh issue edit <map-number> --body ...`), linking the closed ticket by title.

### Assets

Link assets (research summaries, prototypes) from the ticket — as URLs or repo paths in the resolution comment — rather than pasting their content into the issue body.
