"""Tests for configuration schema validation."""

from typing import Dict, Any

import pytest
from core.main import KernelBootstrap
from core.errors import KernelError, ErrorCode


def test_invalid_config_mode_rejected() -> None:
    """Test that an invalid bootstrap mode is rejected by the schema."""
    config: Dict[str, Any] = {"bootstrap": {"mode": "invalid_mode"}}
    with pytest.raises(KernelError) as exc_info:
        KernelBootstrap(config)
    assert exc_info.value.code == ErrorCode.CONFIG_INVALID
    assert "is not one of ['genesis', 'normal']" in exc_info.value.message


def test_missing_required_bootstrap_rejected() -> None:
    """Test that missing the required bootstrap section is rejected."""
    config: Dict[str, Any] = {}
    with pytest.raises(KernelError) as exc_info:
        KernelBootstrap(config)
    assert exc_info.value.code == ErrorCode.CONFIG_INVALID
    assert "'bootstrap' is a required property" in exc_info.value.message


def test_invalid_types_rejected() -> None:
    """Test that invalid types for specific fields are rejected."""
    config: Dict[str, Any] = {
        "bootstrap": {"mode": "normal"},
        "events": {"timeout": "not_an_integer"},
    }
    with pytest.raises(KernelError) as exc_info:
        KernelBootstrap(config)
    assert exc_info.value.code == ErrorCode.CONFIG_INVALID
    assert "is not of type 'integer'" in exc_info.value.message
