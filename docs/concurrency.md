# Concurrency and payment safety

Rent payments are the one place where a bug costs real trust: a double charge, a lost payment or an overpaid balance. This document explains how the API prevents those problems, and shows the evidence.

> Payments in this project are simulated. The design is the point, not the money.

## The problems

1. **Two different payments race for the same charge.** A tenant (or two browser tabs) submits two payments for the full amount at the same instant. Only one may succeed, or the charge would be paid twice.
2. **The same payment is sent twice.** A double-click, a retry after a network timeout, or a mobile app resending a request. The tenant must be charged once, and the second request must get the original result back.

## The three layers of protection

1. **A row lock on the charge.** Creating a payment starts a transaction and runs `SELECT ... FOR UPDATE` on the rent charge row. A second request for the same charge waits at that line until the first transaction commits, so the two can never read the balance at the same time.
2. **An idempotency key.** Every payment request carries an `Idempotency-Key` header. After taking the lock, the API checks whether that key was already used by this user. The same key with the same payload replays the original payment with `200`. The same key with a different payload returns `422`, because that is a client bug and must not be silently accepted.
3. **A unique constraint as the backstop.** The database enforces uniqueness on `(user_id, idempotency_key)`. If application logic ever had a gap, the database would still reject a duplicate.

Inside the same locked transaction the API then checks the balance (an overpayment returns `422`, an already-paid charge returns `409`), inserts the payment, updates the charge to `partial` or `paid`, and writes the audit log entry. It all commits or none of it does.

## Evidence

`backend/scripts/race_test.py` fires pairs of real HTTP requests at the running API at the same instant, using a barrier so both requests are released together. Output from a run against the local Docker stack:

```
Different keys: [201, 409] PASS
Same key:       [200, 201] PASS
```

- **Different keys, same charge:** one request created the payment (`201`). The other waited for the lock, then found the charge already paid and was rejected (`409`). No double payment.
- **Same key, sent twice at once:** one request created the payment (`201`). The other waited for the lock, found the key already used with an identical payload, and replayed the original result (`200`). No duplicate row.

The automated test suite covers the same behaviour on every CI run: `test_concurrent_full_payments_only_one_succeeds` in `tests/test_payments.py`, plus `test_same_idempotency_key_returns_original_payment`, `test_idempotency_key_reused_for_different_payment_is_rejected` and `test_overpayment_is_rejected`. A similar test, `test_concurrent_assignments_only_one_succeeds` in `tests/test_maintenance.py`, shows that two landlords cannot both assign the same maintenance request.

## Related protections

- **Overlapping leases** are blocked by a PostgreSQL exclusion constraint (`btree_gist` with a date range, applied to active leases per unit). The check happens inside the database, so no application bug or race can create two overlapping active leases. The API turns the violation into a `409`.
- **Background jobs** are idempotent. Marking charges overdue is a single bulk update that is safe to repeat, and reminders use `FOR UPDATE SKIP LOCKED` so two job runs never send the same reminder twice.

## Run it yourself

The script needs a tenant login, two unpaid charges with the same amount, and that amount. Run it against a local, freshly seeded database only, because it really pays the charges:

```powershell
cd backend
python -m scripts.seed --reset
python -m scripts.race_test tenant1@example.com Demo1234! CHARGE_ID_1 CHARGE_ID_2 AMOUNT
```

Find two `pending` charge ids and their amount from `GET /leases/{id}/charges` while logged in as `tenant1`. The script can only run once per seed, because its fixed keys and paid charges make a second run fail.

## Limits

- The lock is per charge, so payments against different charges never block each other.
- The race test covers two concurrent requests. The row lock serialises any number of requests per charge, but only the two-request case is tested here.
