# sidecar/config/settings.py - Pydantic configuration models
# Implements config validation for POC scope (HTTP only, no K8s, no mTLS)

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from enum import Enum
import yaml


class DiscoveryType(str, Enum):
    """Supported discovery types for POC (no K8s)."""
    STATIC = "static"
    DNS = "dns"


class LoadBalancingType(str, Enum):
    """Supported load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"


class ServerConfig(BaseModel):
    """Server configuration - ports for inbound, outbound, admin.
    All ports are required - user must explicitly set them."""
    inbound_port: int = Field(ge=1, le=65535)
    outbound_port: int = Field(ge=1, le=65535)
    admin_port: int = Field(ge=1, le=65535)

    @field_validator('inbound_port', 'outbound_port', 'admin_port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Ensure ports are in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError('Port must be between 1 and 65535')
        return v


class DiscoveryConfig(BaseModel):
    """Service discovery configuration."""
    type: DiscoveryType = DiscoveryType.STATIC
    refresh_interval: int = Field(default=30, ge=5)

    @field_validator('type')
    @classmethod
    def validate_discovery_type(cls, v: DiscoveryType) -> DiscoveryType:
        """Only allow static and DNS for POC (no K8s)."""
        if v == "kubernetes":
            raise ValueError('Kubernetes discovery not supported in POC')
        return v


class RouteMatch(BaseModel):
    """Route matching criteria."""
    host: Optional[str] = None
    path_prefix: Optional[str] = None
    path_exact: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class RouteConfig(BaseModel):
    """Individual route configuration."""
    name: str
    match: RouteMatch
    cluster: str
    timeout: int = Field(default=30, ge=1)
    weight: int = Field(default=100, ge=0)


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    scope: str = Field(default="client", pattern="^(global|client|route)$")
    limit: int = Field(default=100, ge=1)
    window: int = Field(default=1, ge=1)
    path: Optional[str] = None


class TelemetryConfig(BaseModel):
    """Telemetry configuration (Prometheus only for POC)."""
    enabled: bool = True
    port: int = Field(default=15002, ge=1, le=65535)
    path: str = Field(default="/sidecar/metrics")


class SidecarConfig(BaseModel):
    """Main sidecar configuration."""
    version: str = "1.0"
    server: ServerConfig = Field(default_factory=ServerConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    routes: List[RouteConfig] = Field(default_factory=list)
    rate_limits: List[RateLimitConfig] = Field(default_factory=list)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    logging: Dict[str, Any] = Field(default_factory=lambda: {"level": "info", "format": "json"})

    @model_validator(mode='after')
    def validate_poc_constraints(self) -> 'SidecarConfig':
        """Validate POC scope constraints."""
        # No K8s discovery
        if self.discovery.type == "kubernetes":
            raise ValueError("Kubernetes discovery not supported in POC scope")

        # No TLS/mTLS validation (deferred for POC)
        # No tracing validation (deferred for POC)

        return self

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'SidecarConfig':
        """Load configuration from YAML file."""
        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls.model_validate(config_dict)

    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'SidecarConfig':
        """Load configuration from dictionary."""
        return cls.model_validate(config_dict)

