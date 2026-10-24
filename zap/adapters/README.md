# Adapters: replacing the file reader with live systems

Today every source is read from `work_pack/` by `zap/sources.py::load_pack()` and every tool writes to
`handover/` or `outbox/`. The rest of the system only sees two shapes, so each live integration is one
function that returns or accepts exactly that shape.

Reading side: `Source(id, kind, at, text, meta)`. `id` must be stable and unique, because it keys the
extraction cache and the idempotency of every promise. `at` is an ISO timestamp with offset.

| Source today | Replace with | One function | Notes |
|---|---|---|---|
| `calls/calls.json` | Granola export (meeting notes API or export folder) | `load_calls() -> list[Source]` | id = the meeting id; `text` = title, attendees, notes as exported. |
| `slack/messages.json` | Slack Web API (`conversations.history`) | `load_slack() -> list[Source]` | id = channel + `ts`; `text` carries channel and user. Poll with `oldest`. |
| `linear/issues.json` | Linear GraphQL API | `load_linear() -> list[Source]` | id = `L-<identifier>`; re-read every tick, state is a snapshot. |
| `inbox/emails.json` | IMAP (read) | `load_mail() -> list[Source]` | id = Message-ID hash; keep From, To, Cc, Subject in `text`. |
| `calendar/events.json` | CalDAV / Google Calendar | `load_calendar() -> list[Source]` | Clash detection reads `meta["event"]`. |

Writing side: the tools in `zap/acts.py` already return the path they wrote.

| Tool today | Replace with | One function |
|---|---|---|
| `acts.send()` moves a draft to `outbox/sent/` | SMTP send of the same file | `send(rel, persona, at) -> path` |
| `acts.linear_update()` edits `handover/linear.json` | Linear mutation | `linear_update(issue, **fields) -> list[str]` |
| `acts.slack_post()` appends to `handover/slack.jsonl` | `chat.postMessage` | `slack_post(channel, user, at, text, key) -> bool` |
| `acts.ics()` writes a proposal file | CalDAV `PUT` of the same VEVENT | `ics(...) -> path` |

What must not change when swapping an adapter:
1. Source ids stay stable across restarts (never a counter, never a timestamp of ingestion).
2. The send policy and `verify_text` stay in front of every outbound function; adapters never bypass them.
3. Credentials come from the environment, are never written to `handover/`, and payments stay in test mode.
4. Every adapter call is keyed by the action key `{promise_id}:{type}` so a restart cannot repeat it.
