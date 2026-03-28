# Brainstorming — Examples

Concrete input→output pairs showing how the brainstorming skill runs in practice.

---

## Example 1: Vague feature idea → Architecture decision

**User prompt:**
> "Хочу добавить систему уведомлений в приложение. Пользователи должны получать уведомления о новых подписчиках, комментариях и лайках."

**Step 1 — Read context:**
Agent checks existing code: no notification-related modules found in `cinemauthor-core-api/`. Clean slate.

**Step 2 — Clarify (one question at a time):**
> "Какой канал доставки важнее на первом этапе: in-app (колокольчик в интерфейсе) или email/push?"

User: "In-app сначала, потом добавим email."

> "Нужна ли агрегация — например 'X лайков' вместо X отдельных уведомлений за один час?"

User: "Да, группировка по событию за 1 час."

**Step 3 — NFR clarified:**
- Assumption: ≤10 000 MAU → no message queue needed yet (synchronous is fine)
- Assumption: no real-time WebSocket requirement — polling every 30s is acceptable
- Marked as assumptions, user confirmed

**Step 4 — Understanding Lock:**
```text
Summary:
- Building: in-app notification system with grouping
- Why: user engagement, reduce notification spam
- For: all registered users
- Constraints: sync delivery acceptable, no real-time WS yet
- Non-goals: email, push, external webhooks
```
User confirmed: "Да, всё верно."

**Step 5 — Options:**
1. ✅ **Recommended: synchronous service call** — `NotificationService.createForEvent()` called directly from existing services (SubscriptionService, CommentService) — simple, no new infra
2. Domain events + async handler — decoupled, but adds complexity; reserve for when a queue is needed
3. Dedicated microservice — overkill for current scale

User chose option 1.

**Step 6 — Design presented:**
- `NotificationService.createForEvent(userId, eventType, payload)` creates a notification record
- Grouping applied at read time: service fetches ungrouped records and aggregates by `(eventType, 1h window)` before returning to the client
- No schema changes required beyond a `notifications` table

User confirmed: "Looks good."

**Step 7 — Decision Log:**
- Decision: synchronous service call pattern, read-time grouping
- Alternatives: domain events, microservice
- Why: scale doesn't justify async complexity; easy to migrate to events later when needed

---

## Example 2: Architecture disagreement → Clarified boundary

**User prompt:**
> "I'm not sure whether to put the grouping logic in the repository or the service."

**Triggering:** Yes — design choice with no confirmed answer.

**Step 1 — Read context:**
The question concerns the notification module from Example 1. Repository exists; grouping is not yet implemented.

**Step 2 — Clarify:** Single question:
> "Does the grouping depend on business rules (e.g. 'group only same-type events within 1 hour') or is it purely a data aggregation query?"

User: "Business rule — same type + 1 hour window."

**Outcome:** Business rule → belongs in the **service layer**. Repository returns raw notification records; service applies grouping. Decision logged, no code written.

---

## Non-trigger: design already confirmed

**User prompt:**
> "Реализуй NotificationService с методом createForEvent() — вызывай его из SubscriptionService."

**Triggering:** No — design is confirmed, user is asking for implementation.

→ Exit brainstorming, hand off to implementation.
