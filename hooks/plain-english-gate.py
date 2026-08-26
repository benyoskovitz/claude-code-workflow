#!/usr/bin/env python3
"""plain-english-gate.py — Stop hook. The mechanical half of the Plain English style.

Why this exists
---------------
`output-styles/plain-english.md` is loaded into context on every session and
ends with a nine-question checklist the agent is supposed to run on its own draft. It does
not hold. Measured over every main-session reply since 2026-08-17 that does not relay a
grader report, 32% contain an em dash in the agent's own prose, against a rule stated four
separate times in loaded context that requires no judgment at all. Rates are quoted here
rather than counts, because the corpus grows every session and only the rates are stable.
The measurement script that recomputes all of it ships alongside this hook.

The rule that follows: a rule phrased as always/never, whose violation is detectable
from the text, should be a check rather than a sentence.

Two checks, both chosen because a machine can settle them and a self-check demonstrably
cannot:

  1. EM DASH in the agent's own prose. Zero judgment.
  2. A COINED LABEL in the closing question: a hyphen-compound noun phrase
     ("the self-disarming problem") that appears nowhere else in the reply. This is the
     2026-08-26 failure exactly: `self-disarm` appeared once in 2,362 words, inside the
     closing question, and the reader had to spend a turn asking what it meant.

Known limits, stated because the alternative is false confidence
----------------------------------------------------------------
* The reply is streamed to the user BEFORE Stop runs. This hook cannot suppress a bad reply.
  It forces the correction to arrive immediately and unprompted, which removes the round
  trip, not the reader seeing the sentence once. So a false block is not free: they read
  the original and then the correction. It costs one confusing sentence and one
  regenerated reply. That is cheaper than the turn they would otherwise spend asking,
  which is the whole trade, but it is not nothing.
* It fires at most once per turn (`stop_hook_active`), so it does not verify the fix.
* Verbatim relays inside <details> are skipped on purpose: a sub-agent's report pasted
  as an audit record is not the main session's prose to rewrite. In the measured history
  93% of those relays carry an em dash, and this hook covers none of them.
* Check 2 catches hyphen-compounds only. "The org-context feature" is caught; a coined
  label made of ordinary separate words ("the pending question") is not, because a wide
  enough pattern fires on every legitimate noun phrase and a check that cries wolf gets
  ignored. Measured at about 1 reply in 70, at roughly 80% precision. Absolute counts
  are not quoted here on purpose: the corpus grows every session, and a count copied into
  four files is a count that disagrees with itself within a week. The measurement script
  shipped alongside this hook prints the current one. The residue is ordinary
  compound adjectives in a long reply
  ("the root-cause report", "the better long-term answer"). A false block costs one
  reworded sentence, though the reader still sees the first version.
* Check 2 only looks for a hyphen-compound sitting in front of one of the head nouns in
  `_HEADS`. That list is long but closed, and nothing outside it is seen.
* Text inside <details> or a fenced code block is skipped, which is what lets a verbatim
  sub-agent report through. Do not rely on that escape being automatic: whatever step of
  your workflow pastes such a report has to require the fence. Measured on one real
  history, only 39% of those relays were fenced, and this hook would have blocked 93% of
  them while the workflow forbade editing a word of the record.

Fails open. Any error, any missing field, any unparseable input exits 0.
"""

import json
import os
import re
import sys

# --- prose extraction ------------------------------------------------------------

_DETAILS = re.compile(r"<details>.*?</details>", re.S | re.I)
_FENCE = re.compile(r"```.*?```", re.S)
_INLINE = re.compile(r"`[^`\n]*`")


def prose_only(msg: str) -> str:
    """Everything that is the agent's own sentences to the user, and nothing else.

    Dropped: <details> blocks (verbatim relays), fenced and inline code, blockquote
    lines (quoted material), markdown table rows, and indented blocks.
    """
    msg = _DETAILS.sub(" ", msg)
    msg = _FENCE.sub(" ", msg)
    msg = _INLINE.sub(" ", msg)
    out = []
    for line in msg.split("\n"):
        s = line.strip()
        if s.startswith(">") or s.startswith("|"):
            continue
        if re.match(r"^\s{4,}\S", line):
            continue
        if s.startswith("<") and s.endswith(">"):
            continue
        out.append(line)
    return "\n".join(out)


# --- check 1: em dashes ----------------------------------------------------------


def find_em_dashes(prose: str):
    """Return up to three quoted contexts around em dashes in the agent's own prose."""
    hits = []
    for m in re.finditer("—", prose):
        ctx = prose[max(0, m.start() - 55):m.start() + 55].replace("\n", " ").strip()
        hits.append(ctx)
        if len(hits) == 3:
            break
    return hits


# --- check 2: a coined label in the closing ask ----------------------------------

# Head nouns that turn a modifier into a NAME for something rather than describing it.
# This is a closed list, which is a real limit and not a hidden one: "the frozen-window
# problem" is caught and "the frozen-window handoff" was not until `handoff` was added
# here. Widening it from 43 entries to 65 changed nothing on the real corpus, so entries
# are cheap; the list will still never be complete.
_HEADS = (
    r"(problem|issue|thing|case|version|approach|fix|gap|rule|check|split|question|"
    r"point|option|path|feature|flow|handler|guard|loop|report|piece|half|side|part|"
    r"mode|state|story|angle|shape|trap|risk|effect|pattern|mismatch|failure|concern|"
    r"call|answer|test|step|behaviour|behavior|handoff|handshake|cutover|rollout|"
    r"ordering|sequencing|tradeoff|wrinkle|subtlety|nuance|distinction|boundary|"
    r"contract|invariant|assumption|edge|window|branch|route|hook|gate|pass)"
)
# A modifier built by joining whole words with hyphens is a coinage, not an adjective.
# Each part >= 3 chars: keeps "re-run" and issue keys like "candor-p" out.
_COMPOUND = re.compile(r"^[a-z]{3,}(?:-[a-z]{3,})+$")
# A label that explains itself in the same breath is not a bare label.
#
# Two rounds of tuning, both measured on the real corpus rather than reasoned about:
#   * `for` and `of` used to count as defining. They do not: "the frozen-window problem
#     for staging" and "...of the ingest path" explain nothing, they are ordinary
#     prepositions. Removing them changed no fire count, so they were buying no precision.
#   * It used to require the definition to start immediately after the head noun, and to
#     be introduced by `which`. That blocked three ordinary ways of doing exactly what
#     Rule 1 asks: an appositive ("the frozen-window fix, the pause while writes are
#     locked"), a `meaning` gloss, and `which` with a word or two in front. All three now
#     count. On the real corpus that trades one catch for another, one in and one out, so
#     the cost is nothing and the gain is that the checker stops blocking compliance.
#     A checker that fires on the correct version of a sentence is worse than one that
#     misses the wrong version.
_SELF_DEFINING = re.compile(
    r"(\s+\S+){0,3}?\s*(,\s*(which|meaning|where|the|a|an)\b|\(|:|\s+about\b)")

# Check 2's premise is that an ARGUMENT got compressed into a label. A reply with no
# argument in it has nothing to compress, and a two-word hyphenated phrase there is an
# ordinary adjective, not a coinage. Measured: every real fire in the corpus sits in a
# reply of 128+ words of prose; the four known false positives
# ("the read-only check", "the single-source rule", "the server-side fix", "the
# row-level security rule") are all replies of about 20 words. 100 leaves margin under
# the observed floor. The cost is stated in KNOWN_MISSES below: a coinage in a short
# reply is not caught.
_MIN_PROSE_WORDS = 100


def _installed_command_names():
    """Hyphenated names already in the user's own workflow are not coinages.

    Derived from the filesystem rather than written out: every skill and command the
    user installed is a name they typed themselves. `pre-commit`, `session-end` and the
    rest come from here, so the set stays right when they add one.
    """
    import os
    names = set()
    for d in ("~/.claude/skills", "~/.claude/commands"):
        try:
            for entry in os.listdir(os.path.expanduser(d)):
                names.add(re.sub(r"\.md$", "", entry).lower())
        except OSError:
            pass
    return names


def closing_questions(prose: str):
    """Every question in the closing region, not just the last one.

    Taking only the last one had a hole the style file itself walked into: Rule 2 tells
    the writer to put unrequested detail behind a one-line offer ("Want the parser
    detail?"). Put that offer after the ask and it becomes the last question, the real
    ask stops being inspected, and this check goes silent on exactly the reply it exists
    for. Scanning all of them costs 2 more fires in 1,977 real turns.
    """
    lines = [l for l in prose.strip().split("\n") if l.strip()]
    if not lines:
        return []
    return [q.strip() for q in re.findall(r"[^.?!\n]*\?", "\n".join(lines[-8:]))]


def find_coined_labels(prose: str):
    """Return [(label, coined_word)] for hyphen-compound labels in the closing ask
    that appear nowhere earlier in the same reply."""
    if len(prose.split()) < _MIN_PROSE_WORDS:
        return []
    questions = closing_questions(prose)
    if not questions:
        return []
    # "Earlier in the reply" means before the FIRST question of the closing region, so a
    # label introduced in one closing question does not excuse itself in the next.
    idx = prose.lower().rfind(questions[0].lower()[:40])
    # `idx >= 0`, not `> 0`: a reply that IS its closing question starts the match at 0,
    # and treating that as "not found" made `before` the whole reply, so the label always
    # counted as seen and the check never fired.
    before = (prose[:idx] if idx >= 0 else prose).lower()
    known = _installed_command_names()
    hits = []
    for q in questions:
        ql = q.lower()
        for m in re.finditer(r"\bthe ((?:[a-z][a-z'-]* ){1,3})" + _HEADS + r"\b", ql):
            if _SELF_DEFINING.match(ql[m.end():]):
                continue
            for w in m.group(1).split():
                if _COMPOUND.match(w) and w not in before and w not in known:
                    hits.append((m.group(0).strip(), w))
                    break
    return hits


# --- the block message -----------------------------------------------------------


def build_reason(dashes, labels) -> str:
    parts = ["Your reply broke the Plain English style. Say it again, corrected. "
             "Do not apologise, do not explain the correction, just give the corrected "
             "reply."]
    if dashes:
        parts.append(
            "\nEM DASHES in your own prose. The rule is zero, no exceptions "
            "(~/.claude/output-styles/plain-english.md). Replace each with a period, "
            "comma, colon, or parentheses, or restructure the sentence:")
        for d in dashes:
            parts.append(f"  ... {d} ...")
    if labels:
        parts.append(
            "\nCOINED LABEL IN YOUR CLOSING QUESTION. You invented a name to compress "
            "an argument, then put it in the one sentence they read for the decision, "
            "where they have the least context to decode it:")
        for label, word in labels:
            parts.append(f'  "{label}"  ({word} appears nowhere else in this reply)')
        parts.append(
            "Rewrite the closing question so it stands alone for someone who read "
            "nothing above it. Say the thing the label stands for, in words. If that "
            "reads clumsy, that is the answer: do not coin the phrase at all.")
    return "\n".join(parts)


def check(message: str):
    prose = prose_only(message)
    return find_em_dashes(prose), find_coined_labels(prose)


# --- self-test -------------------------------------------------------------------

def selftest() -> int:
    """Prove the check FIRES, prove it stays quiet on text the style file accepts, and
    print what it still does not catch.

    Three rules learned the hard way and each enforced below:

    1. A check must be proven to fire, not observed to be silent.
    2. Half of what it looks for sits one clause away from text the style file correctly
       contains, so the quiet half is enforced too.
    3. **Every passage in must_not_fire has to be a reply the style file would actually
       accept.** An earlier draft filed under "correct passages left alone" six replies
       that closed with "Want me to run it on staging first?" and the like, which Rule 3
       forbids outright. A fixture list is a second statement of the rules, and one that
       contradicts them is worse than no fixture at all.
    """
    body = ("The reset path throws away everything git is tracking, which is the point "
            "of it, and it leaves anything git has never recorded exactly where it was. "
            "That asymmetry is fine when you know about it and surprising when you do "
            "not, because the files that survive are the ones nobody has reviewed. I "
            "traced every caller and only one runs against a tree that could hold new "
            "files at all, so the blast radius is one command rather than the whole "
            "script. The safe version refuses to run when it finds anything untracked "
            "and says what it found, which costs one extra call to git status on a path "
            "that already shells out four times. ")

    must_fire = [
        ("em dash in prose",
         "Here is the finding. The fix is small \u2014 one line in the parser.\n"
         "Want me to ship it?"),
        ("a real failure this was written for, at real length",
         "The rule I drafted says a wrong sentence in text only people working in "
         "the repo read can never block a commit. Code comments, plan documents, "
         "memory files. Two rounds of grading on this task caught two real mistakes "
         "of mine, and both of them are exactly that: a wrong sentence in a document "
         "nobody outside the repo will ever open. My analysis file and my proposal "
         "gave different counts for the same fifteen cases, and I claimed the strict "
         "version would not have fixed round nine when it would have. So the rule as "
         "written would have made both rounds of its own grading non-blocking, and "
         "both rounds found something real.\n\n"
         "Do you want me to re-plan 047 around symbol citations, or do you want the "
         "hard version fixed as drafted despite the self-disarming problem?"),
        ("a second real failure, at real length",
         body + "\n\nAnd should I add the untracked-file check before the reset, or "
         "leave it as the documented sharp edge?"),
        ("a coinage the style files do not use as an example",
         "The synthesis step reads the transcript twice and the second pass does not "
         "see what the first one wrote, so a question answered in turn three and "
         "referred back to in turn nine is counted as two separate answers. That "
         "inflates every per-goal number on the report by roughly the rate at which "
         "people refer back, which is not a constant and is higher on longer "
         "interviews. The parser is the thing to change, not the report, because the "
         "report is only reading what the parser handed it.\n\n"
         "Want me to fix that, or start with the double-anchored parse gap?"),
        ("an offer placed after the ask must not hide the ask",
         body + "\n\nShould I ship the frozen-window handoff now? Want the parser "
         "detail?"),
    ]

    # Every one of these is a reply the shipped style file accepts: names defined where
    # they first appear, and a closing question that stands alone for someone who read
    # nothing above it. If you add a fixture here, check it against Rule 1 and Rule 3
    # first. The label cases are deliberately over 100 words, because a shorter fixture
    # is skipped by the prose floor and would prove nothing about the exclusion it names.
    must_not_fire = [
        ("an em dash inside fenced code is not the agent's prose",
         "Here is the line as it stands:\n\n```\nfoo = bar \u2014 baz\n```\n\n"
         "Want me to rewrite the `foo` assignment so `bar` and `baz` are joined with "
         "a comma rather than a dash?"),
        ("an em dash in a quoted block is not the agent's prose",
         "Their own words:\n\n> the fix is small \u2014 one line\n\n"
         "Want me to change the parser's retry limit from three to one now?"),
        ("a verbatim grader relay is skipped on purpose",
         "The grader failed two rubric items.\n\n<details>\nResult: FAIL \u2014 3 of 5\n"
         "</details>\n\nWant me to go back to Plan mode for the two rubric items the "
         "grader failed?"),
        ("a label that defines itself in place",
         body + "\n\nWant me to add the untracked-file check, which looks for files "
         "git has never recorded, before the reset runs?"),
        ("a skill the user installed is a name they already typed",
         body + "\n\nWant me to run the pre-commit check over the staged diff, so "
         "known anti-patterns get caught before the pull request goes up?"),
        ("another one, from the commands directory",
         body + "\n\nWant me to run the session-end step now, so the session notes "
         "get written and the worktree goes away?"),
        ("a plain closing question with no coinage in it",
         body + "\n\nWant me to run the migration, the versioned change to the "
         "database's structure, on staging before production?"),
    ]

    # Fixtures that must fire ONLY because of the installed-name exclusion. Without the
    # proof below, "a skill the user installed" passing proves nothing: it could be
    # because the head noun is missing from _HEADS, or the prose floor caught it, or the
    # regex never matched at all. Naming the reason and testing it is the difference.
    exclusion_proof = [
        ("a skill the user installed is a name they already typed", "pre-commit"),
        ("another one, from the commands directory", "session-end"),
    ]

    # Real violations of the style file that this check does NOT catch. Asserted here so
    # the gap is recorded and stays visible, NOT because the text is acceptable: Rule 1
    # requires a coined name's definition to travel with it every time it is used, and
    # Rule 3 forbids leaning on a term defined further up. The check cannot see either.
    known_misses = [
        ("defined once far above, then used bare in the closing ask",
         "There is a self-disarming problem here: the rule I wrote would have excused "
         "both of my own errors this session.\n\n" + ("Filler. " * 120) +
         "\n\nDo you want the hard version despite the self-disarming problem?"),
        ("a coinage made of ordinary separate words",
         "The synthesis step reads the transcript twice.\n" + ("Filler. " * 120) +
         "\n\nWant me to fix that, or leave the pending question alone?"),
        ("a coined label in a reply too short to have an argument in it",
         "I checked.\n\nWant me to build the tail-archetype guard?"),
    ]

    # Every must_not_fire passage claims to be a reply the style file accepts, so its
    # closing question has to satisfy Rule 3: it must make sense to someone who read
    # nothing above it. Checked mechanically, because a human wrote this list wrong twice
    # running: four bare "it"s in the first draft became "that line", "that one-line
    # change" and "those two items" in the second, and only a grader caught either.
    #
    # This ban is deliberately STRICTER than Rule 3. Rule 3 allows "this worktree" and
    # "the items that failed", where the word is a determiner or a relative pronoun and
    # carries a referent with it. Telling those apart from a bare pointer needs judgment,
    # and a checker that needs judgment is the thing this whole change argues against. On
    # a seven-item list I write myself, banning the words outright costs nothing and is
    # certain. Do not copy this pattern onto real replies: there it would cry wolf.
    _DEICTIC = re.compile(r"\b(it|its|this|that|these|those|them|they|above)\b", re.I)

    fails = []
    for name, msg in must_not_fire:
        q = (closing_questions(prose_only(msg)) or [""])[-1]
        bad = sorted({m.group(0).lower() for m in _DEICTIC.finditer(q)})
        if bad:
            fails.append(f"FIXTURE BREAKS RULE 3: '{name}' closes with "
                         f"{bad} pointing above it, so it is not a passage the style "
                         f"file accepts and must not be listed as one.\n"
                         f"    {q}")
    for name, msg in must_fire:
        d, l = check(msg)
        if not (d or l):
            fails.append(f"MISSED: {name}")
    for name, msg in must_not_fire:
        d, l = check(msg)
        if d or l:
            fails.append(f"FALSE POSITIVE: {name} -> dashes={d} labels={l}")

    # Prove the installed-name exclusion is the reason those two stay quiet.
    fixtures = dict(must_not_fire)
    global _installed_command_names
    real = _installed_command_names
    try:
        _installed_command_names = lambda: set()
        for name, word in exclusion_proof:
            _, l = check(fixtures[name])
            if not any(w == word for _, w in l):
                fails.append(f"NOT ACTUALLY EXCLUDED: '{name}' stays quiet for some "
                             f"reason other than '{word}' being an installed name")
    finally:
        _installed_command_names = real

    # The shipped style files must trip NEITHER check. Both, not just labels: an em dash
    # introduced into the file it governs is exactly the regression worth catching.
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.path.expanduser("~/.claude/output-styles/plain-english.md"),
              os.path.join(here, "..", "output-styles", "plain-english.md")):
        if os.path.exists(p):
            d, l = check(open(p).read())
            if d or l:
                fails.append(f"SHIPPED FILE TRIPS ITS OWN CHECK: {p} -> "
                             f"dashes={d} labels={l}")

    escaped = []
    for name, msg in known_misses:
        d, l = check(msg)
        if d or l:
            escaped.append(name)

    if fails:
        for f in fails:
            print(f)
        print(f"\nSELFTEST FAILED: {len(fails)} problem(s)")
        return 1
    print(f"SELFTEST PASSED: {len(must_fire)} violations caught, "
          f"{len(must_not_fire)} correct passages left alone, "
          f"{len(exclusion_proof)} exclusions proven to be the reason")
    print(f"  known misses still uncaught, as documented: "
          f"{len(known_misses) - len(escaped)} of {len(known_misses)}")
    for name, _ in known_misses:
        print(f"    NOT CAUGHT (by design, a real violation): {name}")
    if escaped:
        print("  now caught, so update the docs and move these into must_fire: "
              + ", ".join(escaped))
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        data = json.loads(raw)
    except Exception:
        return 0
    try:
        if data.get("stop_hook_active"):
            return 0
        msg = data.get("last_assistant_message") or ""
        if not msg.strip():
            return 0
        dashes, labels = check(msg)
        if not (dashes or labels):
            return 0
        sys.stderr.write(build_reason(dashes, labels) + "\n")
        return 2
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
