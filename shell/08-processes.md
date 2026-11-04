# Shell 08 — Processes, Subshells and Signals

Every command is a process. `( ... )`, `$( ... )`, and each pipeline
stage run in a subshell: a forked copy that can read your variables
but whose changes die with it. Background jobs and signals follow
from there.

## A subshell's changes die with it

`cd` inside `( ... )` or `$( ... )` does not move your shell. That is
how you run something "over there": `( cd dir && make )`.

```bash file=n01.sh
x=outer
start=$PWD
( x=inner; cd /tmp; echo "in subshell: x=$x" )
[[ $PWD == "$start" ]] && echo "after: x=$x, same directory"
```

```text output
in subshell: x=inner
after: x=outer, same directory
```

## A piped loop loses its counter

Every pipeline stage is a subshell. Process substitution,
`< <(cmd)`, runs the producer on the side and the loop in this shell.

```bash file=n02.sh
n=0
printf 'a\nb\nc\n' | while read -r _; do (( n++ )); done
echo "pipeline loop: n=$n"
n=0
while read -r _; do (( n++ )); done < <(printf 'a\nb\nc\n')
echo "process substitution: n=$n"
```

```text output
pipeline loop: n=0
process substitution: n=3
```

## `lastpipe` keeps the last stage here

It works when job control is off, which it is in a script. It does
not help an interactive shell.

```bash file=n03.sh
shopt -s lastpipe
n=0
printf 'a\nb\nc\n' | while read -r _; do (( n++ )); done
echo "lastpipe: n=$n"
```

```text output
lastpipe: n=3
```

## `$$` is the script; `$BASHPID` is this process

A subshell has a new pid. `$$` stays the pid of the shell that read
the script, which is why a trap or a kill aimed at `$$` hits the
parent of the subshell.

```bash file=n04.sh
[[ $$ == "$BASHPID" ]] && echo "top level: same pid"
( [[ $$ != "$BASHPID" ]] && echo "subshell: different pid" )
```

```text output
top level: same pid
subshell: different pid
```

## `&` starts a job; `wait` collects its status

`$!` is the pid of the job you just started. `wait` on that pid
returns the job's status. A finished child stays in the process
table until the parent waits. That leftover is a zombie.

```bash file=n05.sh
sleep 0.2 &
pid=$!
echo "started a background job"
wait "$pid"
echo "job finished with $?"
(exit 3) &
wait $!
echo "job exit code $?"
```

```text output
started a background job
job finished with 0
job exit code 3
```

## `wait` with no pid returns 0

It does not mean the jobs succeeded. Wait on each pid and check `$?`
when a failure should change what you do next.

```bash file=n06.sh
(exit 3) &
(exit 4) &
wait
echo "wait all: $?"
```

```text output
wait all: 0
```

## Background jobs run at the same time

They inherit stdout. If a script is captured with `$(...)` and a
background job still holds that pipe, the capture hangs until the
job exits. Redirect (`>/dev/null 2>&1`) or `disown`.

```bash file=n07.sh
tmp=$(mktemp -d)
for i in 1 2 3; do
  ( sleep "0.$((4 - i))"; echo "task $i" ) > "$tmp/task_$i" &
done
wait
cat "$tmp/task_1" "$tmp/task_2" "$tmp/task_3"
rm -rf "$tmp"
```

```text output
task 1
task 2
task 3
```

## `xargs -P` runs one command per item

`-I{}` substitutes the item. The processes overlap. Sort the output
if you need a stable order.

```bash file=n08.sh
printf '%s\n' 1 2 3 4 | xargs -P 4 -I{} sh -c 'echo $(({} * {}))' | sort -n | tr '\n' ' '
echo
```

```text output
1 4 9 16 
```

## `trap` runs when the signal arrives

Without `exit` in the handler, the interrupted command resumes.
`kill` sends SIGTERM (15) by default, and the process may catch it.
`kill -9` cannot be caught or cleaned up after. It is the last
resort. A pid saved long ago may belong to someone else now. Prefer
a process group, or `pkill -f` with a precise match.

```bash file=n09.sh
trap 'echo "caught USR1"' USR1
kill -USR1 $$
trap - USR1
echo "resumed"
```

```text output
caught USR1
resumed
```

## `exit` in the handler stops the script

The command that was interrupted does not resume, and the script's
status is the status you passed to `exit`.

```bash file=n10.sh
bash -c 'trap "echo stop; exit 3" USR1; kill -USR1 $$; echo resumed'
echo "handler exit: $?"
```

```text output
stop
handler exit: 3
```

## A killed child reports 128 plus the signal

SIGTERM is 15, so `wait` returns 143. Redirect `wait`'s stderr if you
do not want the shell's "terminated" note.

```bash file=n11.sh
sleep 30 &
child=$!
kill "$child"
wait "$child" 2>/dev/null
echo "killed child status: $?"
```

```text output
killed child status: 143
```

## `timeout` exits 124 when the clock wins

It is the small watchdog. The command's own failure is some other
status. 124 means "we gave up".

```bash file=n12.sh
timeout 0.2 sleep 5
echo "timeout status: $?"
```

```text output
timeout status: 124
```

## `exec` replaces this shell

Nothing after `exec` in that process runs. Wrap it in a subshell when
you still want the script to continue.

```bash file=n13.sh
( exec echo "exec'd"; echo "never" )
```

```text output
exec'd
```

## `type -t` says what a name will run

A function, a builtin, a keyword, and a file on `PATH` are four
different things. The first match wins.

```bash file=n14.sh
type -t cd
type -t ls
type -t if
```

```text output
builtin
file
keyword
```

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
