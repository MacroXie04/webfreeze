"""HP5 — SSRF guard for the /proxy endpoint.

The proxy fetches arbitrary URLs on behalf of an untrusted page, so it must not
become a relay into the local network or cloud metadata. We block non-http(s)
schemes and any host that resolves to a private / loopback / link-local /
reserved address (incl. 169.254.169.254).

Note: we deliberately do NOT enforce a same-site allowlist — real pages legitimately
load CSS/fonts/images from third-party CDNs, and blocking those would break the
preview and export. Blocking internal address ranges is the actual SSRF defense.

Set WEBFREEZE_ALLOW_PRIVATE=1 to permit private/loopback targets (e.g. to freeze
a localhost dev server).
"""

import ipaddress
import os
import socket
from typing import List

from fastapi import HTTPException

_BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}


def _resolve_ips(host: str, port: int) -> List[str]:
    """Resolve a hostname to all its IPs (separated out so tests can stub it)."""
    return [info[4][0] for info in socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)]


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_proxy_url_allowed(url: str) -> None:
    """Raise HTTPException if `url` is not a safe proxy target."""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Unsupported URL scheme")

    host = parts.hostname
    if not host:
        raise HTTPException(status_code=400, detail="Missing host")
    if host.lower() in _BLOCKED_HOSTNAMES:
        if os.environ.get("WEBFREEZE_ALLOW_PRIVATE") == "1":
            return
        raise HTTPException(status_code=403, detail="Blocked host (SSRF protection)")

    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        ip_obj = ipaddress.ip_address(host)  # host is a literal IP
        ips = [ip_obj]
    except ValueError:
        try:
            ips = [ipaddress.ip_address(a) for a in _resolve_ips(host, port)]
        except socket.gaierror:
            raise HTTPException(status_code=502, detail="DNS resolution failed")

    if os.environ.get("WEBFREEZE_ALLOW_PRIVATE") == "1":
        return
    for ip in ips:
        if _is_blocked_ip(ip):
            raise HTTPException(status_code=403, detail="Blocked address range (SSRF protection)")
