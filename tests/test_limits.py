from backend.limits import ClientConcurrencyLimiter, SlidingWindowRateLimiter


def test_sliding_window_blocks_and_recovers():
    now = [100.0]
    limiter = SlidingWindowRateLimiter(2, 10, clock=lambda: now[0])

    assert limiter.check("client").allowed
    assert limiter.check("client").allowed

    blocked = limiter.check("client")
    assert blocked.allowed is False
    assert blocked.retry_after == 10

    now[0] = 110.1
    recovered = limiter.check("client")
    assert recovered.allowed is True


def test_rate_limit_keys_are_isolated():
    limiter = SlidingWindowRateLimiter(1, 60, clock=lambda: 100.0)

    assert limiter.check("a").allowed
    assert limiter.check("a").allowed is False
    assert limiter.check("b").allowed


def test_concurrency_limiter_releases_slots():
    limiter = ClientConcurrencyLimiter(1)

    assert limiter.try_acquire("client")
    assert limiter.try_acquire("client") is False
    assert limiter.active_for("client") == 1

    limiter.release("client")
    assert limiter.active_for("client") == 0
    assert limiter.try_acquire("client")
