import pytest
from app.utils.helpers import generate_hash, parse_json, validate_payment_amount


class TestGenerateHash:
    def test_generate_hash_returns_string(self):
        result = generate_hash("test_data")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_generate_hash_is_consistent(self):
        data = "test_data"
        assert generate_hash(data) == generate_hash(data)

    def test_generate_hash_different_inputs(self):
        assert generate_hash("data1") != generate_hash("data2")


class TestParseJson:
    def test_parse_valid_json(self):
        json_str = '{"key": "value", "number": 42}'
        result = parse_json(json_str)
        assert result == {"key": "value", "number": 42}

    def test_parse_empty_json(self):
        result = parse_json("{}")
        assert result == {}

    def test_parse_invalid_json_raises(self):
        with pytest.raises(ValueError):
            parse_json("invalid json")


class TestValidatePaymentAmount:
    def test_positive_amount(self):
        assert validate_payment_amount(100.0) is True

    def test_zero_amount(self):
        assert validate_payment_amount(0.0) is False

    def test_negative_amount(self):
        assert validate_payment_amount(-50.0) is False

    def test_float_amount(self):
        assert validate_payment_amount(99.99) is True
