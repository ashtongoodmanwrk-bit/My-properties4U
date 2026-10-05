import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx

BASE = "http://127.0.0.1:8000"


def main():
    email, password, charge_a, charge_b, amount = sys.argv[1:6]
    token = httpx.post(f"{BASE}/auth/login", data={"username": email, "password": password}).json()[
        "access_token"
    ]
    auth = {"Authorization": f"Bearer {token}"}

    def run(charge_id, keys):
        barrier = threading.Barrier(len(keys))

        def pay(key):
            barrier.wait()  # release both requests at the same moment
            r = httpx.post(
                f"{BASE}/payments",
                headers={**auth, "Idempotency-Key": key},
                json={
                    "rent_charge_id": int(charge_id),
                    "amount": amount,
                    "method": "card",
                },
                timeout=30,
            )
            return r.status_code

        with ThreadPoolExecutor(len(keys)) as pool:
            return sorted(pool.map(pay, keys))

    # Test 1: two different payments for the full amount, at once.
    codes = run(charge_a, ["race-diff-key-aaaa", "race-diff-key-bbbb"])
    print("Different keys:", codes, "PASS" if codes == [201, 409] else "FAIL")

    # Test 2: the same payment sent twice at once (a double-click).
    codes = run(charge_b, ["race-same-key-cccc", "race-same-key-cccc"])
    print("Same key:      ", codes, "PASS" if codes == [200, 201] else "FAIL")


main()
