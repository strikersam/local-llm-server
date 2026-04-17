from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlsplit

_ALLOWED_HTTP_SCHEMES = frozenset({"http", "https"})
_ALLOWED_GIT_SCHEMES = frozenset({"http", "https", "ssh", "git"})

# Cloud instance-metadata endpoints that must never be reachable from user-supplied URLs.
# Accessible even from non-admin contexts if the admin token leaks, so block unconditionally.
_METADATA_IPS = frozenset({
    "169.254.169.254",   # AWS / GCP / Azure IMDS
    "fd00:ec2::254",     # AWS IPv6 IMDS
    "100.100.100.200",   # Alibaba Cloud
})
_METADATA_HOSTS = frozenset({
    "metadata.google.internal",
    "metadata.goog",
})


def _strict_mode() -> bool:
    """When STRICT_OUTBOUND=1, block all private/loopback ranges too.

    Off by default because local-first deployments legitimately point providers at
    localhost (e.g. Ollama at 127.0.0.1:11434).
    """
    return os.environ.get("STRICT_OUTBOUND", "0").strip() in {"1", "true", "yes"}


def _is_metadata_ip(addr: str) -> bool:
    if addr in _METADATA_IPS:
        return True
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return int(ip) == 0xA9FEA9FE


def _is_private_or_loopback(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolved_addresses(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return []
    return [info[4][0] for info in infos]


def validate_outbound_url(raw: str, *, scheme: str = "http") -> str:
    """Validate an outbound URL. Always blocks cloud metadata endpoints.

    If STRICT_OUTBOUND=1, also blocks loopback/private ranges (for hosted deployments).
    """
    if not raw or not isinstance(raw, str):
        raise ValueError("URL is required")
    url = raw.strip()
    parts = urlsplit(url)
    allowed = _ALLOWED_HTTP_SCHEMES if scheme == "http" else _ALLOWED_GIT_SCHEMES
    if parts.scheme.lower() not in allowed:
        raise ValueError(f"URL scheme must be one of {sorted(allowed)}; got {parts.scheme!r}")
    host = (parts.hostname or "").strip().lower()
    if not host:
        raise ValueError("URL host is required")

    if host in _METADATA_HOSTS:
        raise ValueError("Cloud metadata hostnames are not allowed")
    if _is_metadata_ip(host):
        raise ValueError("Cloud metadata IPs are not allowed")

    resolved = _resolved_addresses(host)
    for addr in resolved:
        if _is_metadata_ip(addr):
            raise ValueError("Hostname resolves to a cloud metadata IP")

    if _strict_mode():
        if host in {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}:
            raise ValueError("Loopback hosts are not allowed in strict mode")
        if _is_private_or_loopback(host):
            raise ValueError("Private/loopback IPs are not allowed in strict mode")
        for addr in resolved:
            if _is_private_or_loopback(addr):
                raise ValueError("Hostname resolves to a private/loopback IP in strict mode")

    return url


_GIT_REF_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-"


def validate_git_ref(raw: str) -> str:
    """Validate a git ref/branch string. Prevents flag injection and traversal shapes."""
    ref = (raw or "").strip()
    if not ref:
        raise ValueError("git ref is empty")
    if len(ref) > 200:
        raise ValueError("git ref is too long")
    for ch in ref:
        if ch not in _GIT_REF_CHARS:
            raise ValueError(f"git ref contains invalid character {ch!r}")
    if ref.startswith("-") or ref.startswith(".") or "/." in ref or ".." in ref:
        raise ValueError("git ref has invalid shape")
    return ref
