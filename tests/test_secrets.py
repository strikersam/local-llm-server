"""tests/test_secrets.py — Unit tests for the user-scoped secrets store."""

from __future__ import annotations

import pytest

from secrets_store import (
    SecretScope,
    SecretRecord,
    SecretsStore,
    SecretCreateRequest,
    SecretUpdateRequest,
    _encrypt,
    _decrypt,
)
from rbac import UserRole


# ── Encryption ────────────────────────────────────────────────────────────────

class TestEncryption:

    def test_roundtrip(self):
        plain = "sk-proj-abc123def456"
        assert _decrypt(_encrypt(plain)) == plain

    def test_encrypted_differs_from_plain(self):
        plain = "my-secret-value"
        enc   = _encrypt(plain)
        assert enc != plain
        assert plain not in enc

    def test_different_calls_differ(self):
        # Each call uses a random nonce → different ciphertexts
        plain = "same-secret"
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa
            enc1 = _encrypt(plain)
            enc2 = _encrypt(plain)
            assert enc1 != enc2   # different nonces → different ciphertext
        except ImportError:
            pass  # XOR fallback is deterministic — skip this assertion


# ── SecretRecord ──────────────────────────────────────────────────────────────

class TestSecretRecord:

    def test_set_value_masks_key_hint(self):
        rec = SecretRecord(owner_id="u1", name="My Key", scope=SecretScope.USER)
        rec.set_value("sk-proj-abc123def456xyz")
        assert "****" in rec.key_hint
        assert "abc123def456xyz" not in rec.key_hint

    def test_get_value_decrypts(self):
        rec = SecretRecord(owner_id="u1", name="Test", scope=SecretScope.USER)
        rec.set_value("super-secret-value-123")
        assert rec.get_value() == "super-secret-value-123"

    def test_as_safe_dict_no_value(self):
        rec = SecretRecord(owner_id="u1", name="Test", scope=SecretScope.USER)
        rec.set_value("raw-value-should-not-appear")
        d = rec.as_safe_dict()
        assert "raw-value-should-not-appear" not in str(d)
        assert "_encrypted_value" not in d
        assert "secret_id" in d
        assert "key_hint" in d


# ── Store ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def store():
    return SecretsStore(db=None)


@pytest.mark.asyncio
async def test_create_and_get_metadata(store):
    rec = SecretRecord(owner_id="user1@test.com", name="My Token", scope=SecretScope.USER)
    rec.set_value("ghp_" + "a" * 36)
    await store.create(rec)

    fetched = await store.get_metadata(rec.secret_id, "user1@test.com", UserRole.USER)
    assert fetched is not None
    assert fetched.name == "My Token"


@pytest.mark.asyncio
async def test_owner_isolation(store):
    rec = SecretRecord(owner_id="alice@test.com", name="Alice's key", scope=SecretScope.USER)
    rec.set_value("sk-alice-123")
    await store.create(rec)

    # Bob cannot read Alice's USER-scoped secret
    fetched = await store.get_metadata(rec.secret_id, "bob@test.com", UserRole.USER)
    assert fetched is None


@pytest.mark.asyncio
async def test_admin_can_see_all(store):
    rec = SecretRecord(owner_id="alice@test.com", name="Alice's key", scope=SecretScope.USER)
    rec.set_value("sk-alice-123")
    await store.create(rec)

    # Admin bypasses owner check
    fetched = await store.get_metadata(rec.secret_id, "admin@test.com", UserRole.ADMIN)
    assert fetched is not None


@pytest.mark.asyncio
async def test_get_value_returns_plaintext_for_owner(store):
    rec = SecretRecord(owner_id="u@test.com", name="k", scope=SecretScope.USER)
    rec.set_value("my-plain-secret")
    await store.create(rec)

    val = await store.get_value(rec.secret_id, "u@test.com", UserRole.USER)
    assert val == "my-plain-secret"


@pytest.mark.asyncio
async def test_update_re_encrypts(store):
    rec = SecretRecord(owner_id="u@test.com", name="k", scope=SecretScope.USER)
    rec.set_value("original-value")
    await store.create(rec)

    update = SecretUpdateRequest(value="new-value")
    updated = await store.update(rec.secret_id, update, "u@test.com", UserRole.USER)
    assert updated is not None

    new_val = await store.get_value(rec.secret_id, "u@test.com", UserRole.USER)
    assert new_val == "new-value"


@pytest.mark.asyncio
async def test_delete_own_secret(store):
    rec = SecretRecord(owner_id="u@test.com", name="k", scope=SecretScope.USER)
    rec.set_value("to-delete")
    await store.create(rec)

    ok = await store.delete(rec.secret_id, "u@test.com", UserRole.USER)
    assert ok is True


@pytest.mark.asyncio
async def test_delete_other_user_fails(store):
    rec = SecretRecord(owner_id="alice@test.com", name="k", scope=SecretScope.USER)
    rec.set_value("alice-only")
    await store.create(rec)

    ok = await store.delete(rec.secret_id, "bob@test.com", UserRole.USER)
    assert ok is False


@pytest.mark.asyncio
async def test_workspace_secret_visible_to_power_user(store):
    rec = SecretRecord(owner_id="alice@test.com", name="workspace-key", scope=SecretScope.WORKSPACE)
    rec.set_value("shared-value")
    await store.create(rec)

    # Power user can read workspace secrets
    fetched = await store.get_metadata(rec.secret_id, "bob@test.com", UserRole.POWER_USER)
    assert fetched is not None

    # Standard user cannot read workspace secrets unless they are the owner
    fetched_std = await store.get_metadata(rec.secret_id, "bob@test.com", UserRole.USER)
    assert fetched_std is None  # non-owner USER is denied; workspace is power_user+ only


@pytest.mark.asyncio
async def test_list_for_user_filters_correctly(store):
    own_rec = SecretRecord(owner_id="u@test.com", name="mine", scope=SecretScope.USER)
    own_rec.set_value("my-secret")
    ws_rec  = SecretRecord(owner_id="other@test.com", name="shared", scope=SecretScope.WORKSPACE)
    ws_rec.set_value("workspace-secret")
    for r in [own_rec, ws_rec]:
        await store.create(r)

    records = await store.list_for_user("u@test.com", UserRole.USER)
    ids = [r.secret_id for r in records]
    assert own_rec.secret_id in ids       # own secret visible
    assert ws_rec.secret_id not in ids    # workspace secret NOT visible to non-owner USER
