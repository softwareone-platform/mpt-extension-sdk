# Devmock — local schedule harness

[WireMock](https://wiremock.org/) service that stands in for the Marketplace API so
the schedule demo (`mock_app`) can run end-to-end without a real backend, and that
also plays the part of the Extension Framework: it delivers the schedule event and
keeps re-delivering it until the extension acknowledges it.

## Run

```bash
make run-demo
```

This starts the extension in local mode (`mpt-ext run --local`, so no platform
registration) with `MPT_API_BASE_URL` pointing at the devmock (`.env.demo`), plus a
second instance for the claim scenario below and a Jaeger collector for traces (UI on
http://localhost:16686).

## The two lifecycles

A schedule execution has two independent lifecycles, and the harness models them
separately:

- **the event** is the delivery. It is answered with `Defer` while its task is not
  final, so it has to come back; it is acknowledged with `OK` once the task is final.
  Re-delivering is the framework's job, so it is the devmock's job here.
- **the task** is state the SDK reports through the Tasks API (`execute`, `complete`,
  `fail`, `reschedule`). No callback is involved: the SDK calls, the platform records.

## How a flow runs

Postman does not deliver the event. It starts the flow, and the devmock does the rest:

```text
POST {{devmock_url}}/devmock/flows/{use-case}/{task-id}     (once, from Postman)
      → devmock records the flow and delivers the event to the extension
      → SDK reads the task, claims it with execute, submits the handler, answers Defer
      → the non-final task-read stub schedules the next delivery
      → handler finishes; the SDK reports complete or fail
      → next delivery: the task now reads final, so the SDK answers OK
      └── the event is acknowledged and the loop stops
```

The re-delivery hangs off the task read, which is the one call the SDK makes on every
delivery, whatever else that delivery does. So exactly one delivery is scheduled per
delivery, and the loop ends by itself: a task that reads final is answered `OK` from a
branch that carries no webhook, so nothing schedules another one.

The flip side is that reading a non-final task from outside — a `curl`, a dashboard —
also queues one delivery. In a demo nothing else reads these tasks, so that is a
footgun rather than a problem.

## What it stubs

- `POST /devmock/flows/{use-case}/{task-id}` → the entry point above. Records the use
  case and the enqueue time for the task id, then fires the first delivery.
- `POST /public/v1/integration/installations/-/token` → an unsigned demo JWT
  (`extensionId=EXT-1111-1111`) used by the SDK for its outbound API calls. It is
  assembled by the `base64` template helper from readable claims, in
  `__files/mpt/account_token.json.hbs`, so no token literal is committed. The delivery
  webhook builds its `Authorization` header the same way.
- `GET /public/v1/system/tasks/{id}` → the task, in one of two branches: the status the
  SDK last reported, or `rescheduled` while it has reported none. The second branch is
  what schedules the next delivery.
- `POST /public/v1/system/tasks/{id}/execute` → the claim. The first call answers `200`,
  and later calls answer `409` while the claim is held, which is what the platform does.
- `POST /public/v1/system/tasks/{id}/complete` and `/fail` → record the final status, so
  the next delivery ends the event.
- `POST /public/v1/system/tasks/{id}/reschedule` → releases the claim, so the next
  delivery executes the handler again instead of being rejected.
- everything else → `200 {}`, so an unstubbed call never breaks a demo.

## State, and why it is needed

Task state is held by the [WireMock state
extension](https://github.com/wiremock/wiremock-state-extension), pinned in the
`Dockerfile` and loaded from the classpath. It keys state by the task id taken from the
request path, which is what lets one pair of stubs serve every use case, and what lets
a stub branch on whether the SDK has reported an outcome yet.

Clear it between runs. The two are separate stores, so clearing one leaves the other:

```bash
curl -X DELETE http://localhost:8000/__admin/state-extension/contexts   # task state
curl -X POST http://localhost:8000/__admin/reset                        # stubs and journal
```

Neither cancels deliveries already scheduled. Restart the container when a previous run
may still have one in flight:

```bash
docker compose -f compose.yaml -f compose.demo.yaml restart devmock
```

State lives in memory and expires; `compose.demo.yaml` sets
`WIREMOCK_STATE_EXTENSION_CONTEXT_EXPIRATION_SEC` to a day, because the extension's own
default of an hour would drop a settled task's outcome while a demo is still open. A
restart clears it either way.

Starting a flow whose loop is still running is refused with `409`, so a use case cannot
end up with two chains delivering at once. A flow that has settled can be started again.

## The claim on an execution

Run **schedule / start flow timeout** from Postman. The primary instance claims the
task and starts sleeping. Within one minute, run **schedule / deliver timeout to
secondary** from the same collection. It sends the same task to `app-secondary`
(port 8081): its `execute` is answered `409` and the SDK answers `Defer` instead of
running the handler a second time. That is the guarantee that stops two instances, or
two worker processes, from executing one task.

## Timing

Re-delivery waits 30 s, so a flow finishes while you watch it. The timeout fixture
publishes a 120 s processing budget; after the SDK's safety margin, the timeout handler
fails in about one minute. On the platform the SDK answers 300 s for these tasks, since
the watchdog delay is derived from the task's own timing and clamps to its 5-minute
floor; the demo compresses that and changes nothing else about the sequence.

The value is a literal in `mappings/system/get_task_pending.json`. It has to be: WireMock
accepts a template in a webhook's `delay.milliseconds` but never evaluates it, firing
immediately instead, so the delay cannot be driven from the request.

`defer` never settles its task on purpose, so its loop does not end; stop it with
`Ctrl-C` or `make down`.
