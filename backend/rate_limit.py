import time
from collections import defaultdict

import fastapi


class RateLimiter:
    def __init__(self, window_s: int, max_requests: int):
        self.window_s = window_s
        self.max_requests = max_requests
        self._log: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.time()
        cutoff = now - self.window_s
        self._log[key] = [t for t in self._log[key] if t > cutoff]
        if len(self._log[key]) >= self.max_requests:
            raise fastapi.HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again shortly.",
            )
        self._log[key].append(now)


# Generous for CAPTCHA endpoints (testers will click a lot)
challenge_limiter = RateLimiter(window_s=60, max_requests=30)

# Strict for feedback
feedback_limiter = RateLimiter(window_s=60, max_requests=3)
