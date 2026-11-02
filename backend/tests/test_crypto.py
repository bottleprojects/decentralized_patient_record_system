import pytest
from backend.app.services.crypto import CryptoService

def test_aes_gcm_encrypt_decrypt_roundtrip():
    cs = CryptoService()
    plaintext = b"Clinical Lead-II ECG telemetry: HR=72 BPM, SpO2=98.5%"
    ciphertext = cs.encrypt(plaintext)

    assert len(ciphertext) > len(plaintext)
    assert ciphertext != plaintext

    decrypted = cs.decrypt(ciphertext)
    assert decrypted == plaintext

def test_aes_gcm_unique_nonces():
    cs = CryptoService()
    plaintext = b"Identical medical observation data"
    c1 = cs.encrypt(plaintext)
    c2 = cs.encrypt(plaintext)

    # 12-byte nonces must differ
    assert c1[:12] != c2[:12]
    # Ciphertext must differ due to random IV
    assert c1 != c2

def test_aes_gcm_tampered_ciphertext_fails():
    cs = CryptoService()
    plaintext = b"Sensitive diagnostic statement"
    ciphertext = bytearray(cs.encrypt(plaintext))

    # Tamper with single byte in ciphertext body
    ciphertext[-1] ^= 0xFF

    with pytest.raises(Exception):
        cs.decrypt(bytes(ciphertext))

def test_aes_gcm_truncated_ciphertext_fails():
    cs = CryptoService()
    with pytest.raises(ValueError, match="Invalid encrypted data format"):
        cs.decrypt(b"too_short")

