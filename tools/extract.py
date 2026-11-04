#!/usr/bin/env python3
"""Extract the runnable files of a lesson so you can practise on them.

    tools/extract.py python/01-values.md            # example + exercise
    tools/extract.py go/04-collections.md --solution
    tools/extract.py c/08-memory.md -o /tmp/work

Files land in <out>/<lang>-<lesson>/ (default out: ./work, git-ignored).
Edit exercise.*, run it, and make every line say PASS.
"""
import argparse
import re
import sys
from pathlib import Path

NUGGET = re.compile(r"^(example|n\d+)$")

FENCE = re.compile(r"^```(\w+)([^\n]*)\n(.*?)^```", re.S | re.M)

RUN = {
    "python": "python3 {f}",
    "go": "go run {f}",
    "rust": "rustc --edition 2021 -o {b} {f} && ./{b}",
    "shell": "bash {f}",
    "sql": "python3 {tools}/sqlrun.py {f}",
    "k8s": "bash {f}",
    "helm": "bash {f}",
    "aws": "bash {f}",
    "c": "gcc -std=c11 -Wall -Wextra -g -pthread -fsanitize=address,undefined -o {b} {f} -lm && ./{b}",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("lesson", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("work"))
    ap.add_argument("--solution", action="store_true", help="also write solution.*")
    args = ap.parse_args()

    md = args.lesson.resolve()
    lang = md.parent.name
    if lang not in RUN:
        sys.exit(f"{md}: expected the file to live in one of: {', '.join(RUN)}")
    dest = args.out / f"{lang}-{md.stem}"
    dest.mkdir(parents=True, exist_ok=True)

    written = []
    for _lang, info, body in FENCE.findall(md.read_text()):
        m = re.search(r"file=(\S+)", info)
        if not m:
            continue
        name = m.group(1)
        if name.startswith("solution") and not args.solution:
            continue
        (dest / name).write_text(body)
        written.append(name)

    print(f"wrote {', '.join(written)} to {dest}/")
    tools = Path(__file__).resolve().parent
    for name in written:
        kind = Path(name).stem
        if NUGGET.match(kind) or kind == "exercise":
            cmd = RUN[lang].format(f=name, b=kind, tools=tools)
            label = "practise" if kind == "exercise" else "run"
            print(f"{label}:  cd {dest} && {cmd}")


if __name__ == "__main__":
    main()
