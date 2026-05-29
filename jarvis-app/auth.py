"""App-level website login. Credentials live in APP_USERS as
"username:bcrypt_hash" pairs (comma-separated). Only hashes are stored;
plaintext passwords are never persisted. Sessions are held in st.session_state."""
import os
import bcrypt
import streamlit as st


def _load_users():
    raw = os.getenv("APP_USERS", "").strip()
    users = {}
    if not raw:
        return users
    for pair in raw.split(","):
        if ":" not in pair:
            continue
        user, _, h = pair.partition(":")
        users[user.strip()] = h.strip().encode()
    return users


def verify(username, password):
    users = _load_users()
    h = users.get(username.strip())
    if not h:
        return False
    try:
        return bcrypt.checkpw(password.encode(), h)
    except ValueError:
        return False


def is_authenticated():
    return st.session_state.get("auth_user") is not None


def login_gate():
    """Renders the login form. Returns True once authenticated."""
    if is_authenticated():
        return True
    st.markdown("## JARVIS · ECM Prospecting Terminal")
    st.caption("Internal broker-dealer tool — authorized users only.")
    if not _load_users():
        st.error("No users configured. Set APP_USERS in .env "
                 "(generate a hash with `python make_hash.py 'password'`).")
        return False
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Authenticate")
    if ok:
        if verify(u, p):
            st.session_state["auth_user"] = u
            st.rerun()
        else:
            st.error("Invalid credentials.")
    return False


def logout_button():
    if st.sidebar.button("Logout"):
        for k in ("auth_user", "capiq_ok", "dc_ok"):
            st.session_state.pop(k, None)
        st.rerun()
