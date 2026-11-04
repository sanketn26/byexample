#!/usr/bin/env python3
"""Extract and run the code embedded in the lesson Markdown files.

Fence conventions inside a lesson:

    ```python file=n01.py         -> one concept; the next output block is its stdout
    ```text output                -> expected stdout of the nugget just above
    ```python file=example.py     -> older single-program shape; still accepted
    ```python file=exercise.py    -> starter code; must compile and must FAIL
    ```python file=solution.py    -> reference solution; must exit 0

Usage: verify.py [lang|path.md ...]
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^```(\w+)([^\n]*)\n(.*?)^```", re.S | re.M)

# lang -> (build command or None, run command); {f} = file, {o} = binary path
TOOLS = {
    "python": (None, ["python3", "-I", "{f}"]),
    "go": (None, ["go", "run", "{f}"]),
    "rust": (["rustc", "--edition", "2021", "-D", "warnings", "-o", "{o}", "{f}"], ["{o}"]),
    "shell": (None, ["bash", "{f}"]),
    "sql": (None, ["python3", "-I", "{tools}/sqlrun.py", "{f}"]),
    "k8s": (None, ["bash", "{f}"]),
    "helm": (None, ["bash", "{f}"]),
    "aws": (None, ["bash", "{f}"]),
    "c": (["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined",
           "-g", "-pthread", "-o", "{o}", "{f}", "-lm"], ["{o}"]),
}


# track -> file suffix of runnable blocks; other file= blocks are support files
SUFFIX = {"shell": ".sh", "sql": ".sql", "k8s": ".sh", "helm": ".sh", "aws": ".sh"}
SLOW = {"k8s": 600, "helm": 600}  # tracks that talk to a cluster get longer


def run(cmd, cwd, lang=None):
    env = dict(os.environ, BYEXAMPLE_TRACK=lang or "")
    # shell-like tracks document what a terminal shows, so stderr is merged in
    merge = lang in SUFFIX and lang != "sql"
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT if merge else subprocess.PIPE,
                          text=True, timeout=SLOW.get(lang, 120), env=env)


def execute(lang, path: Path, tmp: Path):
    build, runner = TOOLS[lang]
    out = tmp / (path.stem + ".bin")
    sub = lambda cmd: [c.format(f=path.name, o=out, tools=ROOT / "tools") for c in cmd]
    if build:
        b = run(sub(build), tmp, lang)
        if b.returncode != 0:
            return None, b
    return run(sub(runner), tmp, lang), None


# A nugget is one concept: file=n01.py, file=n02.py, ... in reading order.
# file=example.* is the older single-program shape and still verifies.
NUGGET = re.compile(r"^(example|n\d+)$")


def parse_blocks(text: str):
    """Return (files, nugget names in order, expected stdout per nugget, problems)."""
    files, nuggets, expected, problems = {}, [], {}, []
    pending = None
    for _lang, info, body in FENCE.findall(text):
        m = re.search(r"file=(\S+)", info)
        if m:
            name = m.group(1)
            files[name] = body
            if NUGGET.match(name.split(".")[0]):
                if pending:
                    problems.append(f"nugget {pending} has no ```text output block before {name}")
                pending = name
                nuggets.append(name)
        elif "output" in info.split():
            if pending is None:
                problems.append("```text output block does not follow a nugget")
            else:
                expected[pending] = body
                pending = None
    if pending:
        problems.append(f"nugget {pending} has no ```text output block")
    return files, nuggets, expected, problems


def verify(md: Path) -> list[str]:
    lang = md.parent.name
    files, nuggets, expected, problems = parse_blocks(md.read_text())
    kinds = {name.split(".")[0] for name in files}
    if not nuggets:
        problems.append(f"{md.name}: missing a nugget (file=n01.* or file=example.*)")
    if not {"exercise", "solution"} <= kinds:
        missing = {"exercise", "solution"} - kinds
        problems.append(f"{md.name}: missing code block(s): {', '.join(sorted(missing))}")
    if problems:
        return [p if p.startswith(md.name) else f"{md.name}: {p}" for p in problems]
    for text in re.findall(r"\]\(([^)#]+\.md)\)", md.read_text()):
        if not (md.parent / text).exists():
            problems.append(f"{md.name}: broken link to {text}")
    readme = (md.parent / "README.md").read_text()
    if md.name not in readme:
        problems.append(f"{md.name}: not listed in {lang}/README.md")
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for name, body in files.items():
            (tmp / name).write_text(body)
        for name in sorted(files):
            kind = name.split(".")[0]
            if not NUGGET.match(kind) and kind not in ("exercise", "solution"):
                continue  # support file
            if lang in SUFFIX and not name.endswith(SUFFIX[lang]):
                continue
            res, build_err = execute(lang, tmp / name, tmp)
            if kind == "exercise":
                if build_err:
                    problems.append(f"{md.name}: {name} does not compile:\n{build_err.stderr}")
                elif res.returncode == 0:
                    problems.append(f"{md.name}: {name} passes without being solved")
                continue
            if build_err:
                problems.append(f"{md.name}: {name} build failed:\n{build_err.stderr}")
            elif res.returncode != 0:
                problems.append(f"{md.name}: {name} exit {res.returncode}\n{res.stdout}{res.stderr}")
            elif NUGGET.match(kind):
                want = expected.get(name, "")
                if res.stdout.rstrip() != want.rstrip():
                    problems.append(
                        f"{md.name}: {name} output mismatch\n--- expected\n{want}\n--- got\n{res.stdout}")
    return problems


def main():
    args = sys.argv[1:] or list(TOOLS)
    targets = []
    for a in args:
        p = Path(a)
        if a in TOOLS:
            targets += sorted((ROOT / a).glob("[0-9]*.md"))
        else:
            targets.append(p.resolve())
    bad = 0
    for md in targets:
        probs = verify(md)
        print(("FAIL " if probs else "ok   ") + str(md.relative_to(ROOT)))
        for p in probs:
            print("   ", p.replace("\n", "\n    "))
        bad += bool(probs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
