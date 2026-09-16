# Working on NarrowAisleBot

APS (Annual Progress Seminar, doubling as the comprehensive exam) is
**23 Sep 2026, 14:30–15:30.** Every session between now and then should
know that date and count backward from it.

This file is read automatically at the start of a session. Its job is to
carry forward the mistakes that have already cost real time, so they don't
get made twice.

---

## The dashboard HTML/JS rule — read this before touching `phone_dashboard.py`

**15 Sep 2026.** A one-character bug (`sensor\'s` instead of `sensor's`,
written inside the Python triple-quoted `DASHBOARD_HTML` string) took the
*entire* phone dashboard offline — no joystick, no map, no WebSocket,
nothing. The server was completely healthy the whole time: `curl` returned
`HTTP 200`, nothing appeared in the service log, `ros2 node list` showed
the node running normally. Every signal available from the Pi side said
"fine." The only thing that showed the real fault was the browser's own
JavaScript console: `Uncaught SyntaxError: unexpected token: identifier`.

**Why it happened.** `DASHBOARD_HTML` is a plain Python string containing
an entire HTML page, JavaScript included. `\'` inside it is valid *Python*
escape syntax — Python's own parser consumes the backslash while compiling
the `.py` file, so the string Python actually produces at import time has
a bare, unescaped apostrophe sitting inside a JS string literal. The
browser's JS parser hits that quote, the string terminates early, and a
syntax error anywhere in a `<script>` block aborts the *entire* block
before a single line of it runs — which is why one apostrophe took down
every feature on the page simultaneously, including code that had nothing
to do with the broken line.

**Why testing missed it.** Every check available at the time — `node
--check` on a regex-extracted script, a Chromium render test — read the
*raw .py file text* (`pathlib.read_text()`, or a plain string search over
the source). That text still has the two-character `\'` sequence intact,
which is valid JS, so those checks passed cleanly. None of them could ever
have caught this, by construction: they were validating a string Python
never actually produces. The gap wasn't a missing test; it was testing the
wrong object.

**The rule, going forward:**

- **`phone_dashboard.py`'s embedded HTML/JS must be verified as Python
  actually evaluates it, not as the file's raw text reads.** Use
  `ast.literal_eval` on the `DASHBOARD_HTML` assignment's AST node (or
  equivalent) to get the true runtime string — never `open(...).read()`
  or a regex over the source file directly for anything that will be
  treated as JavaScript syntax.
- **Run `python3 tools/tests/dashboard_html_syntax.py` before every commit
  that touches `DASHBOARD_HTML`.** It does exactly the above: evaluates
  the real string, extracts the real `<script>` block, runs `node --check`
  against it, and separately flags *any* backslash that survives into the
  served page at all (there should never be one — every apostrophe in JS
  text belongs inside double quotes instead, which sidesteps the whole
  collision rather than trying to escape around it).
- **A green `node --check` on extracted text is not proof the deployed
  page is un-broken.** Say so explicitly if that's the only check that ran.
- **After deploying any dashboard change to the Pi, load the page in a
  real browser and open its console before declaring it done.** `curl`
  returning `200` and `ros2 node list` looking normal both said "fine"
  while the page was completely dead. The browser console was the only
  place the actual fault was visible.

This is a specific instance of a general rule worth stating plainly: when
one language's source is embedded as literal text inside another's, always
test what the *outer* language actually produces, not what the *file*
appears to contain. The two are the same thing far more often than they
matter to check — until the one time they aren't.

---

## Standing operational discipline (carried across all sessions)

- One step at a time, copy-pasteable, wait for the actual pasted output.
  Never assume a step succeeded.
- Verify configuration with `ros2 param get` against the **live node**,
  never by reading a YAML file.
- Hash every transferred or patched file, per file, not per batch, before
  and after.
- Write the prediction down before a test or a drive, not after.
- The operator's own scp workflow: files go Windows PC → `for scp download`
  folder → `scp` to the Pi. The Pi does not need internet for routine work.
  When it genuinely does (an `apt` upgrade, a `git pull`), that's a
  deliberate, temporary switch to `eduroam`, done and then reverted — never
  the new default.
- Short and crisp in chat; full reasoning belongs in the docs under
  `docs/`, not in the conversation.

## Where the current plan lives

`docs/Phase_234_Push.md` is the live execution plan for closing Phases 2
(odometry/state estimation), 3 (perception/mapping, G4) and 4 (autonomous
navigation, G5/G6/G7). Read it before proposing a different plan.
`docs/Session_Handoff_2026-09-14.md` and any later-dated handoff file
record what was actually verified on hardware, session by session — read
the most recent one first.
