"""Thin adapter over Streamlit's built-in OpenID Connect login (``st.login`` / ``st.user``).

Keeping every call to ``st.login`` here means the rest of the app (and the tests) never
touch Streamlit's auth internals directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import streamlit as st


@dataclass(frozen=True)
class AuthUser:
    email: str          # lower-cased, verified by the identity provider
    name: str           # display name suggested by the provider
    verified: bool = True


def is_configured() -> bool:
    """True when an ``[auth]`` section with a client id exists in ``.streamlit/secrets.toml``."""
    if os.environ.get("TYPEMASTER_AUTH", "").lower() in {"off", "0", "false", "local"}:
        return False
    try:
        section = st.secrets.get("auth")
        if not section:
            return False
        if section.get("client_id"):
            return True
        return any(hasattr(v, "get") and v.get("client_id") for v in section.values())  # [auth.google] style
    except Exception:  # no secrets file at all
        return False


def current_user() -> Optional[AuthUser]:
    """The signed-in user, or ``None`` when nobody is logged in."""
    user = st.user
    if not getattr(user, "is_logged_in", False):
        return None
    email = str(user.get("email") or "").strip().lower()
    if not email:
        return None
    name = str(user.get("name") or email.split("@")[0]).strip()
    return AuthUser(email=email, name=name, verified=bool(user.get("email_verified", True)))


def login() -> None:
    st.login()


def logout() -> None:
    st.logout()
