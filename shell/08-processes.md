# Shell 08 — Processes, Subshells and Signals

Every command is a **process**. `( ... )`, `$( ... )` and each pipeline
stage run in a **subshell**: a forked copy that can read your variables but
whose changes die with it. Background jobs and signals follow from there.

## Example

```bash file=example.sh
#!/usr/bin/env bash

# Subshells: a copy of the environment; changes do not come back
x=outer; start=$PWD
( x=inner; cd /tmp; echo "in subshell: x=$x" )
[[ $PWD == "$start" ]] && echo "after: x=$x, same directory"

# ...which is why a piped `while read` loses its counter
n=0
printf 'a\nb\nc\n' | while read -r _; do (( n++ )); done
echo "pipeline loop: n=$n"
n=0
while read -r _; do (( n++ )); done < <(printf 'a\nb\nc\n')
echo "process substitution: n=$n"
shopt -s lastpipe 2>/dev/null     # alternative: run the last stage in this shell

# $$ is this shell's pid, $BASHPID the current (sub)shell's
[[ $$ == "$BASHPID" ]] && echo "top level: same pid"
( [[ $$ != "$BASHPID" ]] && echo "subshell: different pid" )

# Background jobs: & starts, $! is the pid, wait collects the status
sleep 0.2 &
pid=$!
echo "started a background job"
wait "$pid"; echo "job finished with $?"

(exit 3) &
wait $!; echo "job exit code $?"

# Run several at once and collect each result
results=()
for i in 1 2 3; do
  ( sleep 0.$((4 - i)); echo "task $i" ) > "/tmp/byex_task_$i" &
done
wait
cat /tmp/byex_task_{1,2,3}
rm -f /tmp/byex_task_*

# xargs -P runs commands in parallel (-I{} runs one command per item)
printf '%s\n' 1 2 3 4 | xargs -P 4 -I{} sh -c 'echo $(({} * {}))' | sort -n | tr '\n' ' '; echo

# Signals: trap handlers run when the shell receives one
trap 'echo "caught USR1"' USR1
kill -USR1 $$
trap - USR1

# Kill a runaway child; its status is 128 + signal number
sleep 30 &
child=$!
kill "$child"
wait "$child" 2>/dev/null; echo "killed child status: $?"

# timeout is the simplest watchdog (exit 124 = timed out)
timeout 0.2 sleep 5; echo "timeout status: $?"

# exec replaces the shell with another program: nothing after it runs
( exec echo "exec'd"; echo "never" )

# Command lookup: what will actually run?
type -t cd; type -t ls; type -t if
```

```text output
in subshell: x=inner
after: x=outer, same directory
pipeline loop: n=0
process substitution: n=3
top level: same pid
subshell: different pid
started a background job
job finished with 0
job exit code 3
task 1
task 2
task 3
1 4 9 16 
caught USR1
killed child status: 143
timeout status: 124
exec'd
builtin
file
keyword
```

## Details that bite

- `cd` inside `( ... )` or `$( ... )` does not move your shell. That is a
  feature: `( cd dir && make )` is the tidy way to run something "over there".
- A pipeline's stages are subshells. To keep variables from the last stage
  use `< <(cmd)` or `shopt -s lastpipe` (only when job control is off, as in
  scripts).
- `wait` with no arguments returns 0 regardless of what the jobs did. To
  react to failures, `wait` each pid individually and check `$?`.
- Background jobs inherit stdout. If a script is captured with `$(...)`
  and leaves a background job holding that pipe open, the capture hangs
  until the job exits. Redirect (`>/dev/null 2>&1`) or `disown`.
- `kill` sends SIGTERM (15) by default, which the process may handle.
  `kill -9` cannot be caught or cleaned up after: last resort.
- `kill PID` for a pid you recorded long ago can hit an unrelated process
  that reused it. Prefer process groups or `pkill -f` with a precise match.
- `exit` in a trap handler stops the script; otherwise the interrupted
  command resumes.
- Zombies: a finished child stays in the table until its parent `wait`s.

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

# Count the lines of stdin and set the global COUNT (so no $(...) capture).
# The loop must run in the current shell, not a pipeline subshell.
count_lines() {
  COUNT=0  # TODO
}

# Run each command string in "$@" in the background, wait for all, and
# echo how many exited non-zero.
count_failures() {
  echo 0  # TODO
}

# Run "$@" but give up after $1 seconds; echo "timed out" if it did,
# otherwise "finished". (Use timeout; its status is 124 on timeout.)
with_deadline() {
  echo ""  # TODO
}

# In a SUBSHELL, change to directory $1 and echo the basename of $PWD, so
# the caller's directory is untouched.
basename_in() {
  echo ""  # TODO
}

printf 'a\nb\nc\nd\n' > /tmp/ex08_in
count_lines < /tmp/ex08_in; check "count_lines" "$COUNT" "4"
rm -f /tmp/ex08_in
check "failures" "$(count_failures 'true' 'exit 3' 'false' 'sleep 0.1')" "2"
check "deadline fast" "$(with_deadline 2 sleep 0.1)" "finished"
check "deadline slow" "$(with_deadline 0.2 sleep 5)" "timed out"
here=$PWD
check "basename_in" "$(basename_in /tmp)" "tmp"
check "cwd untouched" "$PWD" "$here"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

count_lines() {
  COUNT=0
  local _
  while read -r _; do (( ++COUNT )); done
}

count_failures() {
  local pids=() cmd pid bad=0
  for cmd in "$@"; do
    bash -c "$cmd" &
    pids+=($!)
  done
  for pid in "${pids[@]}"; do
    wait "$pid" || (( ++bad ))
  done
  echo "$bad"
}

with_deadline() {
  local secs=$1
  shift
  if timeout "$secs" "$@"; then echo finished; else
    [[ $? == 124 ]] && echo "timed out" || echo failed
  fi
}

basename_in() {
  ( cd "$1" && basename "$PWD" )
}

printf 'a\nb\nc\nd\n' > /tmp/ex08_in
count_lines < /tmp/ex08_in; check "count_lines" "$COUNT" "4"
rm -f /tmp/ex08_in
check "failures" "$(count_failures 'true' 'exit 3' 'false' 'sleep 0.1')" "2"
check "deadline fast" "$(with_deadline 2 sleep 0.1)" "finished"
check "deadline slow" "$(with_deadline 0.2 sleep 5)" "timed out"
here=$PWD
check "basename_in" "$(basename_in /tmp)" "tmp"
check "cwd untouched" "$PWD" "$here"
exit $failed
```

</details>

Next: [09 — Text tools](09-text-tools.md)
