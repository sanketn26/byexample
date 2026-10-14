#!/usr/bin/env python3
"""Extract and run the code embedded in the lesson Markdown files.

Fence conventions inside a lesson:

    ```python file=example.py      -> written to <tmp>/example.py
    ```text output                -> expected stdout of example.*
    ```python file=exercise.py    -> starter code; must compile and must FAIL
    ```python file=solution.py    -> reference solution; must exit 0

Usage: verify.py [lang|path.md ...]
"""
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
    "c": (["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined",
           "-g", "-pthread", "-o", "{o}", "{f}", "-lm"], ["{o}"]),
}


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)


def execute(lang, path: Path, tmp: Path):
    build, runner = TOOLS[lang]
    out = tmp / (path.stem + ".bin")
    sub = lambda cmd: [c.format(f=path.name, o=out) for c in cmd]
    if build:
        b = run(sub(build), tmp)
        if b.returncode != 0:
            return None, b
    return run(sub(runner), tmp), None


def verify(md: Path) -> list[str]:
    lang = md.parent.name
    problems = []
    files, expected = {}, None
    for _lang, info, body in FENCE.findall(md.read_text()):
        m = re.search(r"file=(\S+)", info)
        if m:
            files[m.group(1)] = body
        elif "output" in info.split():
            expected = body
    kinds = {name.split(".")[0] for name in files}
    missing = {"example", "exercise", "solution"} - kinds
    if missing:
        return [f"{md.name}: missing code block(s): {', '.join(sorted(missing))}"]
    if expected is None:
        return [f"{md.name}: missing ```text output block"]
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
            res, build_err = execute(lang, tmp / name, tmp)
            kind = name.split(".")[0]
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
            elif kind == "example" and expected is not None:
                if res.stdout.rstrip() != expected.rstrip():
                    problems.append(
                        f"{md.name}: {name} output mismatch\n--- expected\n{expected}\n--- got\n{res.stdout}")
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
