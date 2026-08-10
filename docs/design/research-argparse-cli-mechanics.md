# Research: argparse mechanics for global flags and usage meta-pattern

Wayfinder research asset for [#388](https://github.com/plocher/jBOM/issues/388)
(map: [#385](https://github.com/plocher/jBOM/issues/385)).

**Question**: What can stock argparse express cleanly for the target CLI shape,
and where are the seams?

All behaviors below were verified empirically on Python 3.14.3 (the current dev
interpreter). Nothing here requires a third-party library; stock argparse covers
all four needs, with one small formatter subclass as the only workaround.

## Summary of recommendations

1. **Global decorator flags before and after the subcommand** — define the flags
   on both the root parser and every subparser, with `default=argparse.SUPPRESS`
   on the subparser copies. Clean; no workaround needed.
2. **Usage meta-pattern** — pass `usage="jbom [global flags] COMMAND [ARGS] [PROJECT]"`
   to the root parser and `metavar="COMMAND"` to `add_subparsers()`. The one wart
   (a stray `COMMAND` header row in the commands listing) is removed by a
   ~6-line `HelpFormatter` subclass.
3. **Option-group rendering and ordering** — `add_argument_group()` renders groups
   in creation order with titles and descriptions. Fully sufficient; the only
   discipline required is that every argument be added through a group.
4. **Single-source option groups with per-command varying membership** — use
   **builder functions**, not `parents=`. `parents=` shares live `Action` objects
   across subparsers and cannot vary membership; builder functions do both
   naturally and jBOM already has the pattern (`cli/supplier_args.py`).

## 1. Global decorator flags (`-q`/`-v`/`--debug`/`--show-config`) before and after the subcommand

**Mechanism**: argparse subparsers parse the post-command argv remainder into the
*same* `Namespace` the root parser already populated. So a flag defined only on
the root parser is a syntax error after the command, and a flag defined on both
parsers gets **clobbered** by the subparser's default (verified: `jbom -q bom`
yields `quiet=False` when the subparser also defines `-q` with a normal default —
the subparser's `store_true` default of `False` overwrites the root's `True`).

The fix is the standard SUPPRESS pattern:

- Define each decorator flag on the **root parser** with its real default.
- Define the same flag on **every subparser** with `default=argparse.SUPPRESS`.
  A SUPPRESS'd argument writes to the namespace only when actually present on
  the command line, so the root parser's value survives unless the user repeats
  the flag after the command.

Verified matrix (`quiet`):

- `jbom -q bom proj` → `quiet=True`
- `jbom bom -q proj` → `quiet=True`
- `jbom -v bom -q proj` → `verbose=True, quiet=True` (both positions mix freely)
- `jbom bom proj` → `quiet=False` (root default survives)

Wrap the pair of `add_argument` calls in one **decorator-group builder function**
(see §4) so the flag definitions exist in exactly one place; the builder takes
the parser and a `suppress_defaults: bool` (or infers root vs. sub).

**Cost**: each subparser's `--help` also lists the decorator flags. That is
arguably a feature (the flags *are* valid there); putting them in a titled
`decorators` group (§3) keeps them visually separated from command-specific
options.

**Dead end noted for the record**: `parse_intermixed_args()` does not support
subparsers at all (raises `TypeError`, verified) — it is not a path to
position-independent globals.

## 2. Usage meta-pattern and de-duplicated command listing

**Mechanism**: two independent knobs, plus one small formatter.

- `ArgumentParser(usage="jbom [global flags] COMMAND [ARGS] [PROJECT]")`
  replaces the entire auto-generated usage line. Static string; no fighting.
- `add_subparsers(metavar="COMMAND", title="commands")` replaces the
  `{bom,pos,config,…}` brace-list everywhere it would appear (usage line and
  commands-section header), eliminating the duplicated command listing in
  top-level help. The individual `name  help` rows under the `commands:` title
  remain — that is the single, desired listing.
- **Remaining wart**: the subparsers action still prints its own metavar as a
  header row (`COMMAND`) above the command rows. Verified fix is a minimal
  `HelpFormatter` subclass that flattens the subparsers action to just its
  subactions:

```python
class JbomHelpFormatter(argparse.HelpFormatter):
    def _format_action(self, action):
        if isinstance(action, argparse._SubParsersAction):
            return "".join(self._format_action(sa) for sa in action._get_subactions())
        return super()._format_action(action)
```

  Verified output:

```text
usage: jbom [global flags] COMMAND [ARGS] [PROJECT]

commands:
  bom         Generate a BOM
  pos         Generate placement files
```

**Cost**: the formatter touches two private names (`_SubParsersAction`,
`_get_subactions`). These have been stable across every Python 3.x release and
are the community-standard way to customize subcommand listings, but they are
technically private API — pin a unit test on the rendered help text so an
upstream change is caught by CI rather than by users. Per-command `usage=`
strings can be hand-written the same way where the auto-generated one is noisy.

Note: the current code already uses `RawDescriptionHelpFormatter`; the subclass
should inherit from that if raw description text is still wanted.

## 3. Option-group rendering and ordering in `--help`

**Mechanism**: `parser.add_argument_group(title, description)` — groups render
in **creation order**, each with its title and indented description (verified).
This directly expresses the taxonomy (pseudo-commands / decorators / selectors /
outputs) as visible, ordered sections in every command's help.

Two ordering caveats, both manageable:

- The default `positional arguments` and `options` groups are created at parser
  construction, so they always render **first**. Any argument added directly on
  the parser (not through a group) lands in `options`. Discipline: route every
  argument through a taxonomy group. If `-h/--help` itself should live inside a
  `decorators` group, construct parsers with `add_help=False` and add `-h`
  manually in the group; otherwise it stays in a small leading `options` group.
- Nested argument groups and nesting mutually-exclusive groups inside groups are
  deprecated (3.11+) / disallowed — keep the taxonomy flat, which matches the
  intended one-level design anyway. A mutually exclusive constraint *within* a
  group is fine via `group.add_mutually_exclusive_group()`.

**Cost**: none beyond the discipline above. Groups are purely presentational —
they impose no parsing semantics — which is exactly what the taxonomy needs.

## 4. Single-source option-group builders vs. `parents=`

**Recommendation: builder functions. Do not use `parents=`.**

Verified pitfalls of `parents=`:

- `parents=` copies **references to the same live `Action` objects** into every
  child parser (verified: the action in child-1 *is* the action in child-2 *is*
  the action in the parent). Any post-hoc mutation (changing `help`, `required`,
  defaults) silently affects all commands. This is a well-known argparse trap.
- Membership cannot vary per command: the parent contributes a fixed set with
  fixed settings. The stated requirement — `--inventory` repeatable
  (`action="append"`) for some commands, single-valued for others — is exactly
  the case `parents=` cannot express. You would need one parent per variant,
  defeating single-sourcing.
- Group titles *do* carry over (verified), but this is the only thing `parents=`
  buys over a builder, and builders get it too.

**Builder-function pattern** (single source, per-command variation):

```python
def add_selector_group(parser, *, repeatable_inventory: bool = False):
    g = parser.add_argument_group("selectors", "what design data to act on")
    if repeatable_inventory:
        g.add_argument("-i", "--inventory", action="append", metavar="FILE", ...)
    else:
        g.add_argument("-i", "--inventory", metavar="FILE", ...)
    ...
    return g
```

Each taxonomy group gets one builder module-level function; each command's
`register_command()` calls the builders it needs with the variation flags it
needs. Flag names, metavars, and help text live in exactly one place; membership
and cardinality vary at the call site. Fresh `Action` objects per parser — no
shared-state hazard. jBOM already has a proto-version of this pattern in
`src/jbom/cli/supplier_args.py`, so this is an extension of existing practice,
not a new idiom.

**Cost**: builders are invoked per command, so a command that forgets to call
one simply lacks the group — there is no automatic enforcement. A cheap guard is
a unit test that iterates `subparsers.choices` and asserts each parser exposes
the mandatory groups (e.g., every command must have `decorators`).

## Where argparse fights the design (recap)

- **Position-independent globals**: not native; the SUPPRESS double-definition
  pattern is the workaround. Cost: one builder call per subparser (small,
  single-sourced).
- **Subcommand listing header**: the `COMMAND` metavar row requires a ~6-line
  formatter subclass touching private API. Cost: one help-text regression test.
- **Default group ordering**: the built-in `options` group always renders before
  custom groups. Cost: route all arguments through taxonomy groups (and
  optionally `add_help=False` + manual `-h`).
- **Everything else** (custom usage string, titled/ordered groups, per-command
  group membership) is native argparse used as intended.

## Verification transcript

Probe script exercised on Python 3.14.3, 2026-08-10: SUPPRESS matrix (1a–1d),
clobber counter-example (1e), usage/metavar rendering, formatter-subclass
rendering, group ordering, `parents=` action-identity check, and
`parse_intermixed_args` failure with subparsers. Reproducible by re-creating the
probes from the code fragments above.
