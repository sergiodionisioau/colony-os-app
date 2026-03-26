# COE Kernel - Production Readiness Plan

**Owner:** Agent (Self-Governing)
**Status:** Pre-launch hardening phase
**Goal:** Zero violations, real embeddings, full memory loops

---

## CRITICAL BLOCKERS (Fix First)

### 1. Fix extensions.py Violations
- [ ] Remove 24 instances of W293 (whitespace in blank lines)
- [ ] Fix 2 instances of E722 (bare except)
- [ ] Fix 8 instances of E501 (line too long)

### 2. Replace Mock Embeddings
- [ ] Swap MockEmbedding for OpenAIEmbedding in memory/adapter.py
- [ ] Add fallback to mock if API key not available
- [ ] Test with real embeddings

### 3. PostgreSQL + PGVector Connection
- [ ] Add real database connection (not mock)
- [ ] Test vector search with real embeddings
- [ ] Verify memory persistence

---

## MEMORY LOOP HARDENING

### Current State
- Episodic storage: ✅ Working
- Vector storage: ⚠️ Mock mode
- Retrieval: ⚠️ Mock embeddings
- Learning loop: ⚠️ Not verified end-to-end

### Required Fixes
1. **Real Embeddings** - OpenAI text-embedding-3-small
2. **Connection Pool** - Asyncpg with connection pooling
3. **Retry Logic** - Exponential backoff for DB ops
4. **Metrics** - Track retrieval latency, relevance scores

---

## BASELINE COMPLIANCE

### Must Pass (Zero Tolerance)
- flake8 --max-line-length=120
- pylint --disable=all --enable=E,W
- bandit -r .
- mypy --strict
- black --check

### No Suppression Allowed
- No # noqa comments
- No # pylint: disable
- No .flake8 config exceptions
- No pyproject.toml overrides

---

## LAUNCH CHECKLIST

- [ ] All violations fixed
- [ ] Real embeddings working
- [ ] PostgreSQL connected
- [ ] Memory loop verified end-to-end
- [ ] All tests pass
- [ ] Baseline checks: 0 violations
- [ ] Integration tests: 100% pass
- [ ] Documentation complete

---

## GOVERNANCE RULES

1. Every change runs full baseline
2. No violations committed to main
3. Test before claiming done
4. Document all decisions
5. No BS - verify everything
