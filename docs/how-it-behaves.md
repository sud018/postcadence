# How PostCadence behaves

Every case, and what actually happens. Written against the code, not from memory.

---

## 1. Two workers, one job

There are two things that can publish a post, and **they do not talk to each other**:

| | This app (`python -m web`) | GitHub Actions |
|---|---|---|
| Runs | while it is open on your PC | on your schedule, PC off |
| Drafts live in | `data/drafts.json` (gitignored) | GitHub **Issues** |
| Reads history from | `data/state.json` on your disk | `data/state.json` **in the repo** |
| Writes history to | your disk | the repo (commits it back) |

They share nothing except what git moves between them. Remember this — most of the
surprises below come from it.

## 2. What "closes" a slot

A slot is one posting time on one day, for example `2026-09-28 09:00`.

A slot is **closed** when the history has an entry for that date and slot with
status `posted` or `skipped`. Once closed, neither worker will touch it again
that day.

| Action | Recorded as | Slot closed? | Topic bookmark |
|---|---|---|---|
| Post succeeds | `posted` | yes | moves on |
| You press Skip | `skipped` | yes | stays |
| Post fails (token, network) | `failed` | **no** | stays |
| You press Discard | nothing | no | stays |
| Draft written | nothing | no | stays |

`failed` deliberately does not close the slot: a failure should be retried, not
swallowed.

## 3. One slot's day

Settings for these examples: one post at **09:00**, mode **preview**,
`preview_minutes` 30, `catch_up_hours` 6.

### The one rule that explains everything

**Nothing happens between runs.** GitHub only wakes up at cron ticks. Writing
the draft, checking how long it has been open, publishing - all of it happens
*during a run*. Between runs the agent does not exist, and no clock is ticking
anywhere that can act on your behalf.

Your 09:00 slot gets four ticks a day. Two are for the slot itself, two are the
winter offsets - which still fire in summer, and give you free extra chances:

```
   08:30      09:00      09:30      10:00      <- GitHub is asked to wake
     |          |          |          |
     v          v          v          v
```

### A. GitHub is on time

```
08:30  run --> no draft yet --> CREATE the draft issue
                                notification reaches your phone
                                this run does nothing else

09:00  run --> draft is 30 min old --> PUBLISH
```

### B. GitHub is an hour late

```
08:30 tick ------ delayed ------> 09:30  CREATE the draft
                                         notification reaches your phone now

09:00 tick ------ delayed ------> 10:00  draft is 30 min old --> PUBLISH
```

The post lands at 10:00 instead of 09:00. Late, but it happens - and you still
got your full 30 minutes to look at it.

### C. You approve

```
09:30  CREATE the draft   -> your phone buzzes
09:38  you comment /approve        <- nothing happens yet
10:00  run --> reads /approve --> PUBLISH
```

**Approving does not publish.** Your comment sits in the issue until the next
run reads it. There is nothing listening in between.

### D. You are busy and never look

```
09:30  CREATE the draft   -> buzz (you are in a meeting)
10:00  run --> 30 min passed, no comment --> your fallback applies
                                             "Publish it anyway" -> PUBLISHES
```

Silence is a decision: whatever `preview_timeout_action` says. Set it to
**skip** on the Schedule page if you would rather silence meant "do not post".

### E. You do not look, and GitHub is very late

```
09:30  CREATE the draft
  ...  no run for hours ...
15:00  run --> 09:00 + 6h catch-up has expired --> gives up
                                                   dashboard: "09:00 did not post"
```

`catch_up_hours` is the hard stop. It is what stops a post going out at 3am.

### Why a run never publishes what it just wrote

A run that opens the issue leaves that slot for the next run. Two reasons:

1. A draft written one second ago is not one you have had a chance to read.
2. GitHub's issue list does not show back an issue that quickly. On
   28 September a single run logged `Draft 18:30: drafted - issue #4` and then,
   0.4 seconds later, `No draft issue was found`.

It costs one tick of delay and removes a whole class of surprise.

### In auto mode

No issue, no review, no waiting. The first run at or after 09:00 writes the post
and publishes it in one go.

## 4. Writing drafts in the app

The Drafts page ignores the clock completely. There is no "too early" or
"too late".

**Write a draft** always asks for **the next unused topic**, and writing does not
move the bookmark. That has one consequence worth internalising:

> Three drafts written before any of them is posted are three *different
> wordings of the same topic*.

That is by design — it is how "Rewrite" works — but it surprises people.

| You press | What happens |
|---|---|
| Write a draft | Model writes the next queued topic. Nothing else changes |
| Save edit | Your words replace the model's. Nothing else changes |
| Rewrite | Same topic, fresh attempt, replaces the text |
| Approve & post now | Publishes **immediately**, closes that slot, moves the bookmark, deletes the draft |
| Skip this slot | Closes the slot, deletes the draft, publishes nothing |
| Discard | Deletes the draft. The slot stays open |

The slot on the draft is the one it was written for (the dropdown, or your first
posting time). "Approve & post now" does not wait for that time — it posts at
once, and then that slot counts as done for the day.

## 5. Your questions, answered exactly

### "I click Write a draft at 08:00, before the preview window"

Nothing stops you. A local draft appears. It has no connection to GitHub's
08:30 issue — two separate drafts of the same topic will exist.

If you then approve yours at 08:05:

- you post immediately, and your **local** state closes the 09:00 slot
- GitHub still has its old copy of `state.json`, which says nothing was posted
- so at 08:30 GitHub writes its draft issue, and at 09:00 it publishes it

**You get two posts.** See §7 — this is the sharpest edge in the app today.

### "I write drafts at 10:00, 10:30 and 11:00"

Assume the 09:00 slot already posted this morning.

- All three are created. All three carry slot `09:00` (the default) and today's date.
- All three are the **same topic** — the one after the morning's — in three wordings.
- Approving one publishes it, closes... a slot that is already closed, which
  changes nothing, and moves the bookmark on.
- Approving a second one **posts again**: a second entry for the same date and
  slot. Nothing stops you. The bookmark does not jump twice — both drafts
  point at the same queue position, so it lands on the same next topic.

So: the app treats "Approve & post now" as *you deciding to post*, and does not
second-guess you. Three approvals means three posts today.

### "I write a draft today and approve it tomorrow"

It publishes against **yesterday's** date and slot, because the draft carries the
date it was written on. Yesterday's slot closes; today's is untouched. A draft
left lying around is worth discarding rather than approving days later.

### "My PC is off all day"

GitHub does everything. You see the result when you next open the app and press
**Pull post history**, or the sync badge tells you `1 new run on GitHub`.

### "I run out of topics"

The queue does not stop. The picker reuses the topic last published in that slot
and marks the pick as a repeat, which tells the writer to take a clearly
different angle. The bookmark does not move, so adding new topics later picks up
exactly where you were.

### "The list is empty"

`TopicError`. In the app, a red message on the Drafts page. On GitHub, the run
fails red. Nothing is recorded either way.

### "My LinkedIn token has expired"

The post attempt records `failed` with the error, and the slot stays open, so the
next run inside the catch-up window tries again. The dashboard shows the failure,
and Settings shows the token as expired.

### "My model API key is missing or out of credit"

The draft is never written, so nothing is recorded at all. Locally you see the
error; on GitHub the run goes red. This is a gap: a failure to *write* leaves no
trace in the history, unlike a failure to *post*.

### "Two posting times a day"

Slots are independent. `09:00` and `17:30` close separately, get their own draft
issues, and each takes the next topic in turn — so two posts a day uses the queue
twice as fast.

### "GitHub ran late"

Anything inside `catch_up_hours` still publishes. Later than that, the slot is
dropped silently — no entry, no warning.

## 6. What each worker records

| Situation | History entry | Where |
|---|---|---|
| Actions published | `posted` + post id | repo, committed automatically |
| Actions skipped (`/cancel`) | `skipped` | repo |
| Actions failed to post | `failed` + error | repo |
| Actions found no draft issue | `failed` + reason | repo |
| Actions too late for catch-up | **nothing** | — |
| You approved in the app | `posted` + post id | your disk only |
| You pressed Skip | `skipped` | your disk only |
| Posting from the app failed | `failed` + error | your disk only |

## 7. Two hazards, and one bug this document was written after

### An evening slot used to vanish at midnight

A slot is a clock time, so "18:30" had to be turned into a date before anything
could act on it - and the code only ever used *today's* date. At 00:08, "18:30"
meant tonight, which is in the future, so a post that was still owed from last
night quietly stopped existing.

That is exactly how 28 September was lost: the draft was written at 23:35, and
every run after midnight said "Nothing due right now". Each slot is now checked
against both today's and yesterday's date, so an evening post survives the
change of day for its full catch-up window.


### Local posts are invisible to GitHub

`data/state.json` flows **down** (GitHub → you) because the workflow owns it. It
never flows **up**. So a post you make in the app is unknown to GitHub, and
GitHub will happily post that slot again.

**Settings → Push post history** fixes this. It merges both histories — GitHub
keeps its scheduled posts, your machine keeps the ones you approved by hand —
and writes the result to both sides. The sync badge counts what is waiting:
`2 changes not on GitHub`.

Entries are matched on date, slot and the moment they were created, so two posts
in the same slot are kept as two, and copying the same entry back and forth
never duplicates it.

### Preview mode used to fail in silence

If the 08:30 run cannot open the draft issue — issues disabled, a permissions
problem, an API error — the 09:00 run has nothing to publish.

Each of those now records a `failed` entry with the reason, and the dashboard
shows **"2026-09-28 09:00 did not post"** with the error underneath. The same
complaint is only recorded once, so four cron ticks do not mean four identical
lines. A failure never closes the slot, so a later run inside the catch-up
window still tries.

What is recorded now:

| Went wrong | Recorded as |
|---|---|
| The model could not write the post | `failed` — "Could not write the post: ..." |
| The draft issue could not be opened | `failed` — "Could not open the draft issue: ..." |
| 09:00 came and no draft issue existed | `failed` — "No draft issue was found..." |
| The post itself was rejected | `failed` — LinkedIn's error |

The one gap left: a slot abandoned because it fell outside `catch_up_hours`
still records nothing.

## 8. Quick reference

| Question | Answer |
|---|---|
| Does writing a draft use up a topic? | No. Only a published post does |
| Does "Approve & post now" in the app wait for the slot? | No. It posts the instant you press it |
| Can I post twice in one slot? | Yes, by approving two drafts. Nothing prevents it |
| Does Discard cost me anything? | No. The topic and the slot stay available |
| Does Skip use up a topic? | No, but it closes the slot for the day |
| What if both my PC and GitHub post? | Two posts. Press **Push post history** after posting here |
| Does `/approve` on a GitHub issue publish straight away? | No. The next run reads it and publishes then |
| Will my 09:00 post go out at 09:00? | Often later. GitHub's scheduler is routinely 1-2 hours late |
| Does a late draft lose my review time? | No. The 30 minutes start when the issue opens |
| How late can a post be? | `catch_up_hours` after the slot; then it is dropped |
| Do my edits in the GitHub issue get published? | Yes, exactly as edited |
