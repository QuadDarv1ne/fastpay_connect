import pytest
from app.utils.ip_validator import is_ip_in_whitelist


class TestIsIpInWhitelist:
    def test_single_ip_match(self):
        whitelist = ["192.168.1.1"]
        assert is_ip_in_whitelist("192.168.1.1", whitelist) is True

    def test_single_ip_no_match(self):
        whitelist = ["192.168.1.1"]
        assert is_ip_in_whitelist("192.168.1.2", whitelist) is False

    def test_cidr_match(self):
        whitelist = ["192.168.1.0/24"]
        assert is_ip_in_whitelist("192.168.1.50", whitelist) is True

    def test_cidr_no_match(self):
        whitelist = ["192.168.1.0/24"]
        assert is_ip_in_whitelist("192.168.2.1", whitelist) is False

    def test_multiple_entries(self):
        whitelist = ["192.168.1.1", "10.0.0.0/8"]
        assert is_ip_in_whitelist("192.168.1.1", whitelist) is True
        assert is_ip_in_whitelist("10.0.0.50", whitelist) is True
        assert is_ip_in_whitelist("172.16.0.1", whitelist) is False

    def test_invalid_ip(self):
        whitelist = ["192.168.1.1"]
        assert is_ip_in_whitelist("invalid_ip", whitelist) is False
