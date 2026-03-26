# sidecar/config/loader.py - Configuration loader
# Loads YAML config with validation for POC scope

import yaml
from pathlib import Path
from typing import Dict, Any, Union
from .settings import SidecarConfig


class ConfigLoader:
    """Loads and validates sidecar configuration."""

    @staticmethod
    def load_from_file(config_path: Union[str, Path]) -> SidecarConfig:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)

        if not isinstance(config_dict, dict):
            raise ValueError("Config must be a YAML object")

        return SidecarConfig.from_dict(config_dict)

    @staticmethod
    def load_from_dict(config_dict: Dict[str, Any]) -> SidecarConfig:
        """Load configuration from dictionary."""
        return SidecarConfig.from_dict(config_dict)

    @staticmethod
    def load_default() -> SidecarConfig:
        """Load default configuration for POC."""
        default_config = {
            "version": "1.0",
            "server": {
                "inbound_port": 15000,
                "outbound_port": 15001,
                "admin_port": 15002
            },
            "discovery": {
                "type": "static",
                "refresh_interval": 30
            },
            "routes": [],
            "rate_limits": [],
            "telemetry": {
                "enabled": True,
                "port": 15002,
                "path": "/sidecar/metrics"
            },
            "logging": {
                "level": "info",
                "format": "json"
            }
        }
        return SidecarConfig.from_dict(default_config)

    @staticmethod
    def validate_config(config: SidecarConfig) -> bool:
        """Validate configuration meets POC requirements."""
        # Check for K8s (not allowed in POC)
        if config.discovery.type == "kubernetes":
            return False

        # Check ports don't conflict
        ports = {
            config.server.inbound_port,
            config.server.outbound_port,
            config.server.admin_port
        }
        if len(ports) != 3:
            return False

        return True

