#!/usr/bin/env python3
"""Flag added comment lines that assert something about a WHOLE.

    python3 comment-claims.py              # working tree and untracked files, vs HEAD
    python3 comment-claims.py <rev>        # one commit, merges included
    python3 comment-claims.py --base <ref> # everything since <ref>, untracked included
    python3 comment-claims.py --selftest   # run the cases at the bottom of this file

The scan always exits 0. This is a re-read list, not a gate: it says "you
asserted something about a whole here, go check it", and many hits are correct
sentences that simply use the word. Making it blocking would be wrong, because
the author is the only one who can tell a true "every" from a false one.
`--selftest` is the one mode that can exit non-zero, and only when a case below
stops behaving as documented.

Why the tokens are what they are: they were chosen against the false sentences
`/assess` graders actually quoted over two days of real grading rounds, not
from intuition. Several reach none of that sample; the list was left as chosen
rather than pruned against the same small sample.

How a line is judged: the tool asks git which line numbers each changed file
gained, reads that file as it stands at the point scanned (the working tree, or
the commit's own copy for the <rev> form), and works out from the top which of
its lines are comments. So a new line inside a comment that opened on an old,
unchanged line is seen as the comment line it is. Only ADDED lines are reported.
The bare form says what it compared the working tree with, and how many commits
the branch holds beyond the default branch, zero included, because committed
work is not in its view; `--base <the /assess start point>` is how to reach it.

Known blind spots. This is what has been found so far, not the whole set.
`--selftest` rather than this paragraph is what holds them on the record: every
entry here has a case there, and a blind spot that silently closes or opens
shows up as a failing case rather than as stale prose.
  - a false sentence with no quantifier in it ("rather than described twice",
    "the value is in the download rather than on the page"). Measured: some of
    the corpus is invisible to this and always will be.
  - a wrong file:line citation. A reference checker is the tool for that
    class; this one does not duplicate it.
  - an existing comment in a file the diff touches but does not edit. A comment
    made false by a code edit elsewhere in the same diff is invisible unless the
    comment line itself changed.
  - a comment already sitting in a commit, when the bare form is used. The bare
    form asks what is uncommitted, and says so; reach earlier work with
    `--base <the /assess start point>`. When those commits are already on the
    default branch, as a sweep can put them, the count it prints is zero and
    only `--base` reaches them.
  - prose inside a Python triple-quoted docstring, including this one. Only a
    line-start `#` is a comment in .py here, so a module docstring's own claims
    go unscanned. Tracking string state across a file would flag ordinary
    string literals, which costs more than it buys.
  - a comment beginning partway along a line, after code (`foo(); // every …`,
    or `x = 1; /*` with the comment running on below it: those continuation
    lines are unseen too). Comment openers are recognised at the start of a
    line only, deliberately: matching mid-line flags URLs and string literals.
    The token patterns are not anchored; they search anywhere within a line
    already taken as a comment.
  - a file of a type not in `BY_EXT` below (Markdown, TOML, anything else). Such
    a file is not read, and the output counts it, by type, on a NOT READ line
    rather than counting it as clean, so that line is what tells the two apart.
"""
import os
import re
import subprocess
import sys
from fnmatch import fnmatch

TOKENS = [
    ("every", r"\bevery\b"),
    ("all", r"\ball\b"),
    ("only", r"\bonly\b"),
    ("nothing", r"\bnothing\b"),
    ("none", r"\bnone\b"),
    ("never", r"\bnever\b"),
    ("always", r"\balways\b"),
    ("exactly", r"\bexactly\b"),
    ("each", r"\beach\b"),
    ("most", r"\bmost\b"),
    ("no other", r"\bno other\b"),
    ("exhaustive", r"\bexhaustive\b"),
    # A bare count of things, which is the other half of a completeness claim:
    # "six call sites across five files", "a hardcoded list of five filenames".
    ("count", r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
              r"(?:call ?sites?|files?|filenames?|prompts?|rules?|sites?|entries|"
              r"readers?|consumers?|callers?|schemas?|tests?)\b"),
]

# What opens a comment at the start of a line, by language. `star` is the `*`
# continuation line of a block comment laid out in the C style; `jsx` is `{/*`,
# how a comment sits inside React markup. A `#` is a comment in Python and not
# in TypeScript, where it opens a private field, so the sets are per extension
# and the file list is derived from them rather than kept as a second list.
OPENERS = {
    "hash": r"#", "slash": r"//", "block": r"/\*", "jsx": r"\{\s*/\*",
    "star": r"\*(?!/)", "dash": r"--",
}
C_LIKE = ["slash", "block", "jsx", "star"]
BY_EXT = {
    ".py": ["hash"], ".sh": ["hash"], ".yml": ["hash"], ".yaml": ["hash"],
    ".ts": C_LIKE, ".tsx": C_LIKE, ".js": C_LIKE, ".jsx": C_LIKE,
    ".mjs": C_LIKE, ".cjs": C_LIKE,
    ".css": ["block", "star"], ".scss": ["slash", "block", "star"],
    ".sql": ["dash", "block", "star"],
}
PATHS = [f"*{ext}" for ext in BY_EXT]
BLOCK_OPENER = re.compile(r"^\s*(?:\{\s*)?/\*")


def opener_for(path):
    kinds = BY_EXT.get(os.path.splitext(path)[1])
    if not kinds:
        return None
    return re.compile(r"^\s*(?:" + "|".join(OPENERS[k] for k in kinds) + ")")


def token_hits(text):
    """The token names that match in one line."""
    return [t for t, pat in TOKENS if re.search(pat, text, re.I)]


def scanned(path):
    return any(fnmatch(path, g) for g in PATHS)


def opens_block(text):
    """True when a `/*` in this line is still unclosed at the end of it."""
    i = text.rfind("/*")
    return i != -1 and text.find("*/", i + 2) == -1


def comment_lines(lines, path):
    """1-based numbers of the lines that are comments, read top to bottom.

    One home for this rule: anything measuring comments should import it
    rather than re-derive it, so its figures cannot drift from what this counts.
    """
    opener = opener_for(path)
    out, in_block = set(), False
    if opener is None:
        return out
    blocks = "block" in BY_EXT[os.path.splitext(path)[1]]
    for n, text in enumerate(lines, 1):
        if in_block:
            out.add(n)
            if "*/" in text:
                in_block = False
        elif opener.match(text):
            out.add(n)
            if blocks and BLOCK_OPENER.match(text) and opens_block(text):
                in_block = True
    return out


# Pins the diff format git is asked for, so a repository or global setting for
# colour, path prefixes, an external diff tool, or a `-diff` attribute does not
# change what is parsed below. `--unified=0` asks for no context lines; each of
# the other flags answers one setting that was seen to change the output in a
# way the parser misread, most of them by emptying it under a clean report.
DIFF_FLAGS = ["--no-color", "--no-ext-diff", "--no-textconv", "--text", "--src-prefix=a/",
              "--dst-prefix=b/", "--unified=0", "--inter-hunk-context=0"]


def git(cmd, cwd=None):
    """Run git and return stdout, or None if it exited non-zero.

    Path quoting is off so a non-ASCII filename arrives as itself; bytes that
    are not UTF-8 are replaced rather than raised on, so a Latin-1 file cannot
    end the scan with a traceback.
    """
    env = {k: v for k, v in os.environ.items() if k != "GIT_DIFF_OPTS"}   # it can re-add context
    try:
        r = subprocess.run(["git", "-c", "core.quotepath=false"] + cmd, capture_output=True,
                           encoding="utf-8", errors="replace", cwd=cwd, env=env)
    except FileNotFoundError:
        print("comment-claims: git is not installed or not on PATH. NOTHING was scanned.")
        sys.exit(0)
    return None if r.returncode else r.stdout


HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def added_lines(diff_text):
    """path -> new-side line numbers of the `+` lines, walked from each hunk header.

    A context line advances the new-side counter without being recorded, so the
    result is the added lines even if something re-enables context.
    """
    path, new, out = None, None, {}
    for line in diff_text.split("\n"):
        if line.startswith("+++ "):
            # git appends a tab after a path that contains a space; /dev/null is a deletion
            path = line[6:].split("\t")[0] if line.startswith("+++ b/") else None
            new = None
        elif line.startswith("@@"):
            m = HUNK.match(line)
            new = int(m.group(1)) if m else None
        elif path and new is not None:
            if line.startswith("+"):
                out.setdefault(path, []).append(new)
                new += 1
            elif line.startswith(" ") or line == "":
                new += 1
            # a "-" line is old-side only and does not move the new-side counter
    return out


def read_tree(top, path):
    try:
        with open(os.path.join(top, path), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def collect(args, cwd=None, paths=None):
    """Changed files as [(path, added_line_numbers, file_lines)], the changed
    paths NOT read, and notes on what the bare form compared; or (None, None,
    None) after printing why git could not answer.

    `paths` narrows the git pathspec, for a caller that wants one file type.
    """
    paths = paths or PATHS
    if args and args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return None, None, None
    top = git(["rev-parse", "--show-toplevel"], cwd)
    if top is None:
        print("comment-claims: not inside a git repository. NOTHING was scanned, "
              "which is not the same as nothing to flag.")
        return None, None, None
    top = top.strip()
    notes = []

    rev, untracked = None, True
    if args and args[0] == "--base":
        if len(args) < 2:
            print("comment-claims: --base needs a ref, e.g. --base staging. "
                  "NOTHING was scanned.")
            return None, None, None
        target = args[1]
        diff_cmd = ["diff"] + DIFF_FLAGS + [target]
        names = ["diff", "--no-color", "--name-only", target]
    elif args:
        target = rev = args[0]
        if ".." in rev:
            print(f"comment-claims: '{rev}' is a range, and <rev> takes one commit. Use "
                  f"--base <ref> for everything since a ref. NOTHING was scanned.")
            return None, None, None
        untracked = False
        # --first-parent so a MERGE commit yields a diff. Without it `git show`
        # prints a merge's message and no changes.
        diff_cmd = ["show", "--first-parent", "--format="] + DIFF_FLAGS + [target]
        names = ["show", "--first-parent", "--no-color", "--name-only", "--format=", target]
    else:
        target = "HEAD"
        diff_cmd = ["diff"] + DIFF_FLAGS + ["HEAD"]
        names = ["diff", "--no-color", "--name-only", "HEAD"]
        head = (git(["rev-parse", "--short", "HEAD"], top) or "?").strip()
        notes.append(f"Compared the working tree with HEAD ({head}). Committed work is "
                     f"outside this view; --base <the /assess start point> reaches it.")
        base = default_branch(top)
        if base:
            n = (git(["rev-list", "--count", f"{base}..HEAD"], top) or "0").strip()
            notes.append(f"This branch holds {n} commit(s) beyond {base}, NOT scanned by this "
                         f"form; anything already on {base} is not counted here either.")
        else:
            notes.append("No default branch (origin/HEAD, main, staging) resolved, so commits "
                         "beyond it were not counted; they are NOT scanned by this form.")

    out = git(diff_cmd + ["--"] + paths, top)
    if out is None:
        print(f"comment-claims: git could not read '{target}'. NOTHING was scanned, "
              f"which is not the same as nothing to flag.")
        return None, None, None

    files = []
    for path, nums in added_lines(out).items():
        if not nums:
            continue
        body = git(["show", f"{rev}:{path}"], top) if rev else read_tree(top, path)
        if body is None:
            print(f"comment-claims: could not read {path}, so it was NOT scanned.")
            continue
        files.append((path, nums, body.split("\n")))

    changed = [n for n in (git(names, top) or "").split("\n") if n]
    if untracked:
        listing = git(["ls-files", "--others", "--exclude-standard"], top)
        if listing is None:
            print("comment-claims: could not list untracked files, so any NEW file "
                  "in this change went unscanned.")
        else:
            for name in [n for n in listing.split("\n") if n]:
                changed.append(name)
                if not any(fnmatch(name, g) for g in paths):
                    continue
                body = read_tree(top, name)
                if body is None:
                    print(f"comment-claims: could not read untracked {name}, so it was NOT scanned.")
                    continue
                lines = body.split("\n")
                files.append((name, list(range(1, len(lines) + 1)), lines))
    return files, [n for n in changed if not scanned(n)], notes


def default_branch(top):
    """origin/HEAD's target if set, else the first of main or staging that exists."""
    ref = git(["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"], top)
    for cand in ([ref.strip()] if ref else []) + ["main", "staging"]:
        if git(["rev-parse", "--verify", "-q", cand], top) is not None:
            return cand
    return None


def scan(args, cwd=None, paths=None):
    files, skipped, notes = collect(args, cwd, paths)
    if files is None:
        return None, None, None, None
    comments, hits = [], []
    for path, nums, lines in files:
        is_comment = comment_lines(lines, path)
        for n in nums:
            if n in is_comment and n <= len(lines):
                text = lines[n - 1]
                comments.append((path, text))
                found = token_hits(text)
                if found:
                    hits.append((path, found, text.strip()))
    return comments, hits, skipped, notes


def skipped_note(skipped, notes):
    if skipped:
        from collections import Counter
        exts = Counter(os.path.splitext(n)[1] or "(no extension)" for n in skipped)
        kinds = ", ".join(f"{e} x{c}" for e, c in sorted(exts.items()))
        print(f"\n  NOT READ: {len(skipped)} changed file(s) of types this tool does not scan "
              f"({kinds}). Their comments are unchecked, not clean.")
    for n in notes:
        print(f"\n  {n}")


def main():
    comments, hits, skipped, notes = scan([a for a in sys.argv[1:]])
    if comments is None:
        return
    if not hits:
        print(f"COMMENT CLAIMS: {len(comments)} added comment lines, none assert a whole.")
        skipped_note(skipped, notes)
        return
    print(f"COMMENT CLAIMS: {len(hits)} of {len(comments)} added comment lines assert "
          f"something about a whole. Re-read each against the finished code.\n")
    last = None
    for path, found, text in hits:
        if path != last:
            print(f"  {path}")
            last = path
        print(f"    [{','.join(found)}] {text[:150]}")
    print("\n  A claim about a whole is either true and worth the search that establishes")
    print("  it, or it is the sentence a grader will find. Advisory: nothing is blocked.")
    skipped_note(skipped, notes)


# ---------------------------------------------------------------- selftest ----
# A case returns the arguments and the directory to scan from, having built
# whatever state it needs first. `expect` is True for at least one hit, False
# for a scan that read the change and found none, "unscanned" for one that says
# it read nothing, "skipped" for no hits plus a changed file counted as NOT READ,
# ("path", name) for a hit attributed to that file, and ("cue", "<text>") for a
# scan that found no hits and printed a note containing that text. The rows whose name
# begins `blind:` are the documented blind spots above, held here so that one
# closing or opening shows up as a failing case rather than as stale prose; the
# other False rows check that a code line is not taken for a comment.

def _w(tmp, name, body):
    full = os.path.join(tmp, name)
    if os.path.dirname(name):
        os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(body)


def _repo(tmp):
    git(["init", "-q", "."], tmp)
    _w(tmp, "seed.txt", "seed\n")
    git(["add", "seed.txt"], tmp)
    git(["commit", "-q", "-m", "seed"], tmp)


def _commit(tmp, name, body, msg="c"):
    _w(tmp, name, body)
    git(["add", name], tmp)
    git(["commit", "-q", "-m", msg], tmp)


CLAIM = "// Every consumer of this list goes through the helper.\n"


def c_staged(tmp):
    _repo(tmp); _w(tmp, "a.ts", CLAIM + "export const a = 1;\n")
    git(["add", "a.ts"], tmp); return [], tmp


def c_unstaged(tmp):
    _repo(tmp); _commit(tmp, "a.ts", "export const a = 1;\n")
    _w(tmp, "a.ts", CLAIM + "export const a = 1;\n"); return [], tmp


def c_untracked(tmp):
    _repo(tmp); _w(tmp, "n.ts", CLAIM + "export const n = 1;\n"); return [], tmp


def c_jsx_one_line(tmp):
    _repo(tmp); _w(tmp, "C.tsx", "const C = () => (\n  <div>\n"
                  "    {/* Every render goes through the helper. */}\n  </div>\n);\n")
    git(["add", "C.tsx"], tmp); return [], tmp


def c_jsx_multi_line(tmp):
    _repo(tmp); _w(tmp, "M.tsx", "const M = () => (\n  <div>\n"
                  "    {/* The label helper is the single place this is built, so\n"
                  "        every render goes through it and nothing else\n"
                  "        formats it. */}\n  </div>\n);\n")
    git(["add", "M.tsx"], tmp); return [], tmp


def c_line_added_inside_old_css_block(tmp):
    _repo(tmp)
    _commit(tmp, "globals.css", "/*\n  Theme tokens.\n*/\n:root { --x: 1; }\n")
    _w(tmp, "globals.css", "/*\n  Theme tokens.\n"
       "  Every theme token used anywhere in the app is defined in this block.\n"
       "*/\n:root { --x: 1; }\n")
    return [], tmp


def c_line_added_inside_old_jsx_block(tmp):
    _repo(tmp)
    _commit(tmp, "L.tsx", "const L = () => (\n  <div>\n    {/* The label helper builds this,\n"
            "        so it is safe. */}\n  </div>\n);\n")
    _w(tmp, "L.tsx", "const L = () => (\n  <div>\n    {/* The label helper builds this,\n"
       "        every render goes through it and nothing else formats it,\n"
       "        so it is safe. */}\n  </div>\n);\n")
    return [], tmp


def c_line_added_after_old_opener(tmp):
    _repo(tmp)
    _commit(tmp, "o.ts", "/*\n  header\n*/\nexport const o = 1;\n")
    _w(tmp, "o.ts", "/*\n  Nothing else reads this list.\n  header\n*/\nexport const o = 1;\n")
    return [], tmp


def c_jsx_extension(tmp):
    _repo(tmp); _w(tmp, "B.jsx", CLAIM + "export const B = 1;\n")
    git(["add", "B.jsx"], tmp); return [], tmp


def c_subdirectory(tmp):
    _repo(tmp); _w(tmp, "src/c.ts", CLAIM + "export const c = 1;\n")
    git(["add", "src/c.ts"], tmp)
    os.makedirs(os.path.join(tmp, "tools"), exist_ok=True)
    return [], os.path.join(tmp, "tools")


def c_base_untracked(tmp):
    _repo(tmp); git(["tag", "marker"], tmp)
    _w(tmp, "f/new.ts", CLAIM + "export const f = 1;\n")
    return ["--base", "marker"], tmp


def c_merge(tmp):
    _repo(tmp)
    main = git(["rev-parse", "--abbrev-ref", "HEAD"], tmp).strip()
    git(["checkout", "-q", "-b", "side"], tmp)
    _commit(tmp, "s.ts", CLAIM + "export const s = 1;\n", "side")
    git(["checkout", "-q", main], tmp)
    _commit(tmp, "o.ts", "export const o = 1;\n", "other")
    git(["merge", "--no-ff", "-q", "-m", "merge side", "side"], tmp)
    return [git(["rev-parse", "HEAD"], tmp).strip()], tmp


def c_sql(tmp):
    _repo(tmp); _w(tmp, "001_init.sql", "-- Every row in this table carries a tenant id.\n"
                  "create table t (id int);\n")
    git(["add", "001_init.sql"], tmp); return [], tmp


def c_css(tmp):
    _repo(tmp); _w(tmp, "globals.css", "/* Every theme token is defined in this block. */\n"
                  ":root { --x: 1; }\n")
    git(["add", "globals.css"], tmp); return [], tmp


def c_yaml(tmp):
    _repo(tmp); _w(tmp, "ci.yml", "# Every job here runs on ubuntu-latest.\njobs: {}\n")
    git(["add", "ci.yml"], tmp); return [], tmp


def c_glob_in_line_comment(tmp):
    # `build/*` is a glob, not a block opener; the code line after it carries a
    # token and must NOT be flagged, which proves it was not taken as a comment.
    _repo(tmp); _w(tmp, "clean.sh", "#!/bin/sh\n# clean build/*\nexport MODE=every\n")
    git(["add", "clean.sh"], tmp); return [], tmp


def c_private_field_is_code(tmp):
    # `#count` opens a private field in TypeScript, not a comment.
    _repo(tmp); _w(tmp, "k.ts", "class K {\n  #every = 1;\n}\n")
    git(["add", "k.ts"], tmp); return [], tmp


def c_color_forced(tmp):
    _repo(tmp); git(["config", "color.ui", "always"], tmp)
    _w(tmp, "z.ts", CLAIM + "export const z = 1;\n")
    git(["add", "z.ts"], tmp); return [], tmp


def c_non_ascii_name(tmp):
    _repo(tmp); _w(tmp, "café.ts", CLAIM + "export const k = 1;\n")
    git(["add", "café.ts"], tmp); return [], tmp


def c_all_output_settings(tmp):
    # The five output settings the round-five grader named, switched on at once.
    _repo(tmp)
    for k, v in [("diff.noprefix", "true"), ("diff.mnemonicPrefix", "true"),
                 ("color.diff", "always"), ("diff.external", "/usr/bin/true")]:
        git(["config", k, v], tmp)
    _w(tmp, ".gitattributes", "*.ts -diff\n")
    _w(tmp, "a.ts", CLAIM + "export const a = 1;\n")
    git(["add", "a.ts"], tmp); return [], tmp


def c_non_utf8(tmp):
    _repo(tmp)
    with open(os.path.join(tmp, "l.ts"), "wb") as fh:
        fh.write(b"// Every caf\xe9 goes through the helper.\nexport const l = 1;\n")
    git(["add", "l.ts"], tmp); return [], tmp


def c_space_in_name(tmp):
    _repo(tmp); _w(tmp, "my file.ts", CLAIM + "export const m = 1;\n")
    git(["add", "my file.ts"], tmp); return [], tmp


def c_range_as_rev(tmp):
    _repo(tmp); _commit(tmp, "r.ts", CLAIM + "export const r = 1;\n")
    return ["HEAD~1..HEAD"], tmp


def c_textconv(tmp):
    _repo(tmp); git(["config", "diff.blank.textconv", "/usr/bin/true"], tmp)
    _w(tmp, ".gitattributes", "*.ts diff=blank\n")
    _w(tmp, "t.ts", CLAIM + "export const t = 1;\n")
    git(["add", "t.ts"], tmp); return [], tmp


def c_context_reenabled(tmp):
    # An OLD comment must not come back as added when context is forced on.
    _repo(tmp); _commit(tmp, "x.ts", "// Nothing else reads this list.\nexport const x = 1;\n")
    git(["config", "diff.interHunkContext", "10"], tmp)
    os.environ["GIT_DIFF_OPTS"] = "-u3"
    _w(tmp, "x.ts", "// Nothing else reads this list.\nexport const x = 1;\nexport const y = 2;\n")
    return [], tmp


def c_blind_block_after_code(tmp):
    _repo(tmp); _w(tmp, "b.ts", "export const b = 1; /*\n  Every consumer of this list goes through the helper.\n*/\n")
    git(["add", "b.ts"], tmp); return [], tmp


def c_skipped_type(tmp):
    _repo(tmp); _w(tmp, "NOTES.md", "Every rule here is enforced by a hook.\n")
    _w(tmp, "cfg.toml", "# every key below is required\nk = 1\n")
    git(["add", "NOTES.md", "cfg.toml"], tmp); return [], tmp


def c_blind_no_quantifier(tmp):
    _repo(tmp)
    _w(tmp, "q.ts", "// The value is in the download rather than on the page.\n"
                    "export const q = 1;\n")
    git(["add", "q.ts"], tmp); return [], tmp


def c_blind_citation(tmp):
    _repo(tmp)
    _w(tmp, "r.ts", "// See src/lib/does-not-exist.ts:9999 for the reason.\n"
                    "export const r = 1;\n")
    git(["add", "r.ts"], tmp); return [], tmp


def c_blind_untouched_comment(tmp):
    _repo(tmp); _commit(tmp, "u.ts", CLAIM + "export const u = 1;\n")
    _w(tmp, "u.ts", CLAIM + "export const u = 2;\n")   # code edited, comment not
    return [], tmp


def c_blind_committed(tmp):
    _repo(tmp); _commit(tmp, "d.ts", CLAIM + "export const d = 1;\n")
    return [], tmp


def c_swept_onto_main(tmp):
    # Work already on the default branch: the count is zero and must still print.
    _repo(tmp); git(["branch", "-M", "main"], tmp)
    _commit(tmp, "s.ts", CLAIM + "export const s = 1;\n", "swept")
    return [], tmp


def c_committed_on_branch(tmp):
    # The same blind spot, on a feature branch: the output must say the commit
    # exists and was not scanned.
    _repo(tmp)
    git(["branch", "-M", "main"], tmp)
    git(["checkout", "-q", "-b", "feat"], tmp)
    _commit(tmp, "w.ts", CLAIM + "export const w = 1;\n", "wip")
    return [], tmp


def c_blind_mid_line(tmp):
    _repo(tmp); _w(tmp, "m.ts", "export const m = 4; // every consumer reads this one\n")
    git(["add", "m.ts"], tmp); return [], tmp


def c_blind_docstring(tmp):
    _repo(tmp); _w(tmp, "p.py", '"""Every caller goes through this function."""\n\n\nX = 1\n')
    git(["add", "p.py"], tmp); return [], tmp


def c_not_a_repo(tmp):
    return [], "/"


def c_bad_rev(tmp):
    _repo(tmp); return ["deadbeef99"], tmp


def c_base_no_ref(tmp):
    _repo(tmp); return ["--base"], tmp


def c_help(tmp):
    _repo(tmp); return ["--help"], tmp


CASES = [
    ("staged comment", c_staged, True),
    ("unstaged edit to a tracked file", c_unstaged, True),
    ("untracked new file", c_untracked, True),
    ("JSX comment, one line", c_jsx_one_line, True),
    ("JSX comment, several lines", c_jsx_multi_line, True),
    ("line added inside an old CSS block", c_line_added_inside_old_css_block, True),
    ("line added inside an old JSX block", c_line_added_inside_old_jsx_block, True),
    ("line added right after an old /*", c_line_added_after_old_opener, True),
    (".jsx file", c_jsx_extension, True),
    ("run from a subdirectory", c_subdirectory, True),
    ("--base with an untracked file", c_base_untracked, True),
    ("a merge commit", c_merge, True),
    (".sql comment", c_sql, True),
    (".css comment", c_css, True),
    (".yml comment", c_yaml, True),
    ("glob in a # comment is not a block", c_glob_in_line_comment, False),
    ("#field in TypeScript is code", c_private_field_is_code, False),
    ("color.ui=always", c_color_forced, True),
    ("five output settings at once", c_all_output_settings, True),
    ("textconv driver", c_textconv, True),
    ("context forced back on", c_context_reenabled, False),
    ("non-UTF-8 file", c_non_utf8, True),
    ("non-ASCII filename", c_non_ascii_name, ("path", "café.ts")),
    ("filename with a space", c_space_in_name, ("path", "my file.ts")),
    ("skipped: .md and .toml counted", c_skipped_type, "skipped"),
    ("blind: no quantifier", c_blind_no_quantifier, False),
    ("blind: wrong file:line", c_blind_citation, False),
    ("blind: comment not edited", c_blind_untouched_comment, False),
    ("blind: already committed", c_blind_committed, False),
    ("committed on a branch: count printed", c_committed_on_branch, ("cue", "1 commit(s) beyond")),
    ("swept onto main: zero count printed", c_swept_onto_main, ("cue", "0 commit(s) beyond")),
    ("blind: comment after code", c_blind_mid_line, False),
    ("blind: block opened after code", c_blind_block_after_code, False),
    ("blind: python docstring", c_blind_docstring, False),
    ("loud: not a repository", c_not_a_repo, "unscanned"),
    ("loud: bad revision", c_bad_rev, "unscanned"),
    ("loud: --base with no ref", c_base_no_ref, "unscanned"),
    ("loud: --help", c_help, "unscanned"),
    ("loud: a range as <rev>", c_range_as_rev, "unscanned"),
]


def selftest():
    import io
    import shutil
    import tempfile
    from contextlib import redirect_stdout
    bad = 0
    for name, setup, expect in CASES:
        tmp = tempfile.mkdtemp()
        try:
            args, cwd = setup(tmp)
            with redirect_stdout(io.StringIO()):          # keep the case's own output out of the table
                comments, hits, skipped, notes = scan(args, cwd)
            if expect == "unscanned":
                ok = comments is None
                got = "no scan performed" if ok else f"scanned, {len(hits)} hit(s)"
            elif comments is None:
                ok, got = False, "no scan performed"
            elif expect == "skipped":
                ok = not hits and bool(skipped)
                got = f"{len(hits)} hit(s), {len(skipped)} file(s) counted as NOT READ"
            elif isinstance(expect, tuple) and expect[0] == "cue":
                cue = [n for n in notes if expect[1] in n]
                ok = not hits and bool(cue)
                got = cue[0][:60] + "…" if cue else f"{len(hits)} hit(s), no note with {expect[1]!r}"
            elif isinstance(expect, tuple) and expect[0] == "path":
                ok = bool(hits) and hits[0][0] == expect[1]
                got = f"hit attributed to {hits[0][0]!r}" if hits else "0 hit(s)"
            else:
                ok = bool(hits) == expect
                got = f"{len(hits)} hit(s) of {len(comments)} comment line(s)"
            bad += 0 if ok else 1
            want = {True: "flagged", False: "read, nothing flagged",
                    "unscanned": "no scan, and no clean message",
                    "skipped": "no hits and the unread files counted"}.get(
                        expect if not isinstance(expect, tuple) else None,
                        (f"a hit attributed to {expect[1]!r}" if expect[0] == "path"
                         else f"no hits and a note containing {expect[1]!r}")
                        if isinstance(expect, tuple) else "?")
            print(f"  {'ok  ' if ok else 'FAIL'}  {name:<36} expected {want}; {got}")
        finally:
            os.environ.pop("GIT_DIFF_OPTS", None)
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n  {len(CASES) - bad} of {len(CASES)} cases behaved as documented.")
    return bad


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)   # `| head` ends the output, not a traceback
    if "--selftest" in sys.argv:
        sys.exit(1 if selftest() else 0)
    main()
