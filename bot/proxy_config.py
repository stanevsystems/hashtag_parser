"""Настройка прокси для Telethon (SOCKS5 / MTProto)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("true", "1", "yes", "on")


@dataclass
class ProxySettings:
    enabled: bool
    proxy_type: str | None = None
    host: str | None = None
    port: int = 1080
    secret: str | None = None
    username: str | None = None
    password: str | None = None

    @classmethod
    def from_env(cls) -> ProxySettings:
        enabled = _truthy(os.getenv("USE_PROXY") or os.getenv("use_proxy"))
        proxy_type = (os.getenv("PROXY_TYPE") or os.getenv("proxy_type") or "").strip().lower()
        host = (os.getenv("PROXY_HOST") or os.getenv("proxy_host") or "").strip() or None
        port_raw = os.getenv("PROXY_PORT") or os.getenv("proxy_port") or "1080"
        secret = (os.getenv("PROXY_SECRET") or os.getenv("proxy_secret") or "").strip() or None
        username = (os.getenv("PROXY_USERNAME") or os.getenv("proxy_username") or "").strip() or None
        password = (os.getenv("PROXY_PASSWORD") or os.getenv("proxy_password") or "").strip() or None
        return cls(
            enabled=enabled,
            proxy_type=proxy_type or None,
            host=host,
            port=int(port_raw),
            secret=secret,
            username=username,
            password=password,
        )

    def describe(self) -> str:
        if not self.enabled:
            return "proxy: off (direct)"
        return f"proxy: {self.proxy_type} {self.host}:{self.port}"


def build_telethon_client_options(
    proxy: ProxySettings,
) -> dict[str, Any]:
    """
    Доп. аргументы для TelegramClient(..., **options).
    proxy, connection, таймауты.
    """
    options: dict[str, Any] = {
        "connection_retries": 15,
        "retry_delay": 3,
        "timeout": 40,
    }

    if not proxy.enabled:
        logger.info("Telegram: direct connection (USE_PROXY=false)")
        return options

    if proxy.proxy_type == "mtproto":
        if not proxy.host or not proxy.secret:
            raise ValueError(
                "MTProto proxy: set PROXY_HOST and PROXY_SECRET in .env"
            )
        from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate

        options["proxy"] = (proxy.host, proxy.port, proxy.secret)
        options["connection"] = ConnectionTcpMTProxyRandomizedIntermediate
        logger.info("Telegram: MTProto proxy %s:%s", proxy.host, proxy.port)
        return options

    if proxy.proxy_type in ("socks5", "socks"):
        if not proxy.host:
            raise ValueError("SOCKS5 proxy: set PROXY_HOST in .env (e.g. 127.0.0.1)")
        try:
            import python_socks
        except ImportError as e:
            raise ValueError(
                "SOCKS5 requires python-socks in venv: "
                ".\\venv\\Scripts\\pip.exe install \"python-socks[asyncio]\""
            ) from e

        # Telethon expects addr (not host) — see telethon docs / connection._parse_proxy
        proxy_dict: dict[str, Any] = {
            "proxy_type": "socks5",
            "addr": proxy.host,
            "port": proxy.port,
            "rdns": True,
        }
        if proxy.username:
            proxy_dict["username"] = proxy.username
            proxy_dict["password"] = proxy.password or ""

        options["proxy"] = proxy_dict
        logger.info("Telegram: SOCKS5 %s:%s (python-socks)", proxy.host, proxy.port)
        return options

    raise ValueError(
        f"Unknown PROXY_TYPE={proxy.proxy_type!r}. Use socks5 or mtproto."
    )
