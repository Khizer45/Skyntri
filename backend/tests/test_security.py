from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hash_and_verify():
    password = "TestPassword123!"

    hashed_password = hash_password(password)

    # Password should be hashed, not stored as plain text
    assert hashed_password != password

    # Correct password should verify successfully
    assert verify_password(password, hashed_password) is True

    # Wrong password should fail verification
    assert verify_password("WrongPassword123!", hashed_password) is False


def test_jwt_create_and_decode():
    user_id = "test-user-123"

    token = create_access_token(
        subject=user_id,
        expires_minutes=10,
    )

    assert token is not None
    assert isinstance(token, str)

    decoded_subject = decode_access_token(token)

    assert decoded_subject == user_id


def test_expired_jwt():
    user_id = "test-user-123"

    # Negative expiry makes the token immediately expired
    token = create_access_token(
        subject=user_id,
        expires_minutes=-1,
    )

    decoded_subject = decode_access_token(token)

    assert decoded_subject is None