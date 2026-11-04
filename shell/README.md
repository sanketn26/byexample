# Shell by Example (practice edition)

Bash 4.4+ on Linux (macOS ships bash 3.2: install a newer one with
`brew install bash`). Each lesson is a series of tiny scripts, one concept
each: `bash n01.sh`, then `n02.sh`.
Exercises use a tiny `check` helper and exit non-zero until solved.
Lesson 15 targets POSIX `sh`.

| # | Lesson | You will practise |
|---|--------|-------------------|
| 01 | [Values](01-values.md) | variables, quoting, `$(...)`, `$(( ))`, exit status |
| 02 | [Control flow](02-control-flow.md) | `if`, `[[ ]]`, `(( ))`, `for`, `while read`, `case` |
| 03 | [Functions](03-functions.md) | arguments, `return` vs output, `local`, namerefs |
| 04 | [Arrays and maps](04-arrays.md) | indexed and associative arrays, `mapfile`, `read -a` |
| 05 | [Strings and expansion](05-strings.md) | `${var#%/:-}`, case, `IFS`, `printf %q` |
| 06 | [Redirection and pipes](06-redirection-pipes.md) | fds, `2>&1`, here-docs, `<( )`, `pipefail`, `tee` |
| 07 | [Errors](07-errors.md) | strict mode, `trap`, `die`, retry, input validation |
| 08 | [Processes and signals](08-processes.md) | subshells, `&`, `wait`, `kill`, `timeout`, `xargs -P` |
| 09 | [Text tools](09-text-tools.md) | `grep`, `sed`, `awk`, `sort`, `cut`, `jq` |
| 10 | [Files and find](10-files-find.md) | globs, tests, `find`, `-print0`, atomic writes |
| 11 | [Arguments](11-arguments.md) | `getopts`, long options, usage, exit codes |
| 12 | [**Idiomatic shell**](12-idiomatic-shell.md) | the quoting/safety checklist, `shellcheck` |
| 13 | [Testing](13-testing.md) | assertions, function fakes, `PATH` shims, golden files |
| 14 | [Capstone: logstat](14-capstone-logstat.md) | a real tool from small pipeline stages |
| 15 | [Portable POSIX sh](15-posix-sh.md) | what bash features you lose, and the replacements |
