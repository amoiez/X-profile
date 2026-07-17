import pytest

from app.core.errors import AppError, ErrorCode
from app.core.validation import normalize_username


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("@example", "example"),
        ("example", "example"),
        ("  @Example_1  ", "Example_1"),
        ("a", "a"),
        ("A1_bcDEF12345_", "A1_bcDEF12345_"),
    ],
)
def test_normalize_valid(raw, expected):
    assert normalize_username(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "@", "this_name_is_way_too_long", "bad-char", "has space", "emoji😀", "a@b"],
)
def test_normalize_invalid(raw):
    with pytest.raises(AppError) as exc:
        normalize_username(raw)
    assert exc.value.code == ErrorCode.INVALID_USERNAME
