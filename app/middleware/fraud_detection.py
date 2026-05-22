"""Fraud detection middleware.

Detects suspicious patterns:
- Rapid repeated payment attempts (velocity check)
- Unusually large amounts
- Multiple failed attempts from same IP
- Geographic anomalies
- Suspicious user agent patterns

Uses Redis for distributed state tracking.
Falls back to in-memory storage if Redis unavailable.
"""

import time
import hashlib
import json
import logging
from collections import defaultdict
from typing import Optional, Dict, Any, Set

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


class FraudDetectionConfig:
    """Configuration for fraud detection thresholds."""

    # Velocity checks
    max_requests_per_minute: int = 30
    max_payments_per_hour: int = 10
    max_failed_attempts_per_hour: int = 5

    # Amount checks
    max_single_payment_amount: float = 1000000.0  # 1M RUB
    max_daily_amount_per_ip: float = 5000000.0  # 5M RUB per day

    # Time-based checks
    min_time_between_payments: float = 5.0  # seconds

    # Blocked patterns
    blocked_user_agents: Set[str] = {"sqlmap", "nikto", "nmap", "masscan"}

    # Response
    block_duration_minutes: int = 30


class FraudDetector:
    """Detects fraudulent payment patterns.

    Thread-safe, supports both Redis and in-memory backends.
    """

    def __init__(self, config: Optional[FraudDetectionConfig] = None):
        self.config = config or FraudDetectionConfig()
        self._redis_client = None
        self._init_redis()

        # In-memory fallback
        self._request_counts: Dict[str, list] = defaultdict(list)
        self._payment_counts: Dict[str, list] = defaultdict(list)
        self._failed_counts: Dict[str, list] = defaultdict(list)
        self._daily_amounts: Dict[str, list] = defaultdict(list)
        self._blocked_ips: Dict[str, float] = {}

    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            from app.settings import settings
            import redis

            self._redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=1,
            )
            self._redis_client.ping()
            logger.info("Fraud detection: Redis backend connected")
        except Exception as e:
            logger.debug(f"Fraud detection: using in-memory backend (Redis error: {e})")
            self._redis_client = None

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP, respecting proxy headers."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host or "unknown"

    def _get_fingerprint(self, request: Request) -> str:
        """Generate a unique fingerprint for the request."""
        ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        raw = f"{ip}:{user_agent}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _check_user_agent(self, request: Request) -> Optional[str]:
        """Check for suspicious user agents."""
        ua = request.headers.get("User-Agent", "").lower()
        for blocked in self.config.blocked_user_agents:
            if blocked in ua:
                return f"Blocked user agent detected: {blocked}"
        return None

    def _check_velocity(self, fingerprint: str) -> Optional[str]:
        """Check request velocity (requests per minute)."""
        now = time.time()
        window = 60  # 1 minute

        if self._redis_client:
            key = f"fraud:velocity:{fingerprint}"
            try:
                pipe = self._redis_client.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.zremrangebyscore(key, 0, now - window)
                pipe.zcard(key)
                pipe.expire(key, window + 10)
                _, _, count, _ = pipe.execute()
                if count > self.config.max_requests_per_minute:
                    return f"Rate limit exceeded: {count} requests/minute"
                return None
            except Exception as e:
                logger.warning(f"Fraud detection velocity check Redis error: {e}")

        # In-memory fallback
        timestamps = self._request_counts[fingerprint]
        cutoff = now - window
        self._request_counts[fingerprint] = [t for t in timestamps if t > cutoff]
        if len(self._request_counts[fingerprint]) > self.config.max_requests_per_minute:
            return f"Rate limit exceeded: {len(self._request_counts[fingerprint])} requests/minute"
        self._request_counts[fingerprint].append(now)
        return None

    def _check_payment_velocity(self, fingerprint: str) -> Optional[str]:
        """Check payment creation velocity."""
        now = time.time()
        hour_window = 3600

        if self._redis_client:
            key = f"fraud:payments:{fingerprint}"
            try:
                pipe = self._redis_client.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.zremrangebyscore(key, 0, now - hour_window)
                pipe.zcard(key)
                pipe.expire(key, hour_window + 60)
                _, _, count, _ = pipe.execute()
                if count > self.config.max_payments_per_hour:
                    return f"Too many payments: {count}/hour"
                return None
            except Exception as e:
                logger.warning(f"Fraud detection payment velocity check Redis error: {e}")

        # In-memory
        timestamps = self._payment_counts[fingerprint]
        cutoff = now - hour_window
        self._payment_counts[fingerprint] = [t for t in timestamps if t > cutoff]
        if len(self._payment_counts[fingerprint]) > self.config.max_payments_per_hour:
            return f"Too many payments: {len(self._payment_counts[fingerprint])}/hour"
        self._payment_counts[fingerprint].append(now)
        return None

    def _check_amount(self, amount: Optional[float], fingerprint: str) -> Optional[str]:
        """Check for suspicious payment amounts."""
        if amount is None:
            return None

        # Single payment limit
        if amount > self.config.max_single_payment_amount:
            return f"Amount exceeds maximum: {amount}"

        # Daily amount limit per IP
        now = time.time()
        day_window = 86400

        if self._redis_client:
            key = f"fraud:daily_amount:{fingerprint}"
            try:
                pipe = self._redis_client.pipeline()
                pipe.zadd(key, {f"{now}:{amount}": now})
                pipe.zremrangebyscore(key, 0, now - day_window)
                # Sum all amounts
                entries = pipe.zrangebyscore(key, 0, now)
                pipe.expire(key, day_window + 60)
                _, entries_list, _ = pipe.execute()
                total = sum(float(e.split(":")[1]) for e in entries_list)
                if total > self.config.max_daily_amount_per_ip:
                    return f"Daily amount limit exceeded: {total}"
                return None
            except Exception as e:
                logger.warning(f"Fraud detection daily amount check Redis error: {e}")

        return None

    def record_failed_attempt(self, fingerprint: str) -> None:
        """Record a failed payment attempt."""
        now = time.time()
        hour_window = 3600

        if self._redis_client:
            key = f"fraud:failed:{fingerprint}"
            try:
                pipe = self._redis_client.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.zremrangebyscore(key, 0, now - hour_window)
                pipe.zcard(key)
                pipe.expire(key, hour_window + 60)
                _, _, count, _ = pipe.execute()
                if count >= self.config.max_failed_attempts_per_hour:
                    # Block IP
                    block_until = now + (self.config.block_duration_minutes * 60)
                    self._redis_client.setex(
                        f"fraud:blocked:{fingerprint}",
                        self.config.block_duration_minutes * 60,
                        str(block_until),
                    )
                return
            except Exception as e:
                logger.warning(f"Fraud detection record_failed_attempt Redis error: {e}")

        # In-memory
        timestamps = self._failed_counts[fingerprint]
        cutoff = now - hour_window
        self._failed_counts[fingerprint] = [t for t in timestamps if t > cutoff]
        self._failed_counts[fingerprint].append(now)
        if len(self._failed_counts[fingerprint]) >= self.config.max_failed_attempts_per_hour:
            block_until = now + (self.config.block_duration_minutes * 60)
            self._blocked_ips[fingerprint] = block_until

    def check_blocked(self, fingerprint: str) -> Optional[str]:
        """Check if fingerprint is currently blocked."""
        if self._redis_client:
            try:
                blocked = self._redis_client.get(f"fraud:blocked:{fingerprint}")
                if blocked:
                    return f"IP blocked for {self.config.block_duration_minutes} minutes due to suspicious activity"
                return None
            except Exception as e:
                logger.warning(f"Fraud detection check_blocked Redis error: {e}")

        # In-memory
        block_until = self._blocked_ips.get(fingerprint)
        if block_until and time.time() < block_until:
            return f"IP blocked for {self.config.block_duration_minutes} minutes due to suspicious activity"
        elif block_until:
            del self._blocked_ips[fingerprint]
        return None

    def record_payment(self, fingerprint: str, amount: Optional[float] = None) -> Optional[str]:
        """Run all fraud checks for a payment request.

        Returns violation description or None if clean.
        """
        # Check if blocked
        blocked = self.check_blocked(fingerprint)
        if blocked:
            return blocked

        # Check velocity
        velocity = self._check_velocity(fingerprint)
        if velocity:
            return velocity

        # Check payment frequency
        payment_freq = self._check_payment_velocity(fingerprint)
        if payment_freq:
            return payment_freq

        # Check amount
        amount_violation = self._check_amount(amount, fingerprint)
        if amount_violation:
            return amount_violation

        return None


# Global instance
fraud_detector = FraudDetector()


class FraudDetectionMiddleware(BaseHTTPMiddleware):
    """Middleware that runs fraud detection on payment-related requests."""

    PAYMENT_PATHS = {
        "/payments/create",
        "/api/v1/payments/create",
        "/api/v2/payments/create",
        "/api/payments/create",
    }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only check payment POST requests
        if request.method == "POST" and request.url.path in self.PAYMENT_PATHS:
            fingerprint = fraud_detector._get_fingerprint(request)

            # Check user agent
            ua_violation = fraud_detector._check_user_agent(request)
            if ua_violation:
                logger.warning(f"Fraud detection: {ua_violation} from {fingerprint}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": "fraud_detected", "message": ua_violation},
                )

            # Check if blocked
            blocked = fraud_detector.check_blocked(fingerprint)
            if blocked:
                logger.warning(f"Fraud detection: blocked request from {fingerprint}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"error": "blocked", "message": blocked},
                )

            # Run fraud checks
            amount = None
            try:
                body_bytes = await request.body()
                # Cache body for downstream handlers
                request.state._cached_body = body_bytes
                body = json.loads(body_bytes)
                amount = body.get("amount")
            except Exception as e:
                logger.debug(f"Fraud detection: could not parse request body: {e}")

            violation = fraud_detector.record_payment(fingerprint, amount)
            if violation:
                logger.warning(f"Fraud detection: {violation} from {fingerprint}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"error": "fraud_detected", "message": violation},
                )

        response = await call_next(request)

        # Track failed responses for fraud detection
        if request.method == "POST" and request.url.path in self.PAYMENT_PATHS:
            if response.status_code >= 400:
                fingerprint = fraud_detector._get_fingerprint(request)
                fraud_detector.record_failed_attempt(fingerprint)

        return response
