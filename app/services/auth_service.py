"""Local user authentication (SQLite)."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import unicodedata

from app.database.connection import db

_ITERATIONS = 200_000


def _normalize_password(password: str | None) -> str:
    if password is None:
        return ""
    p = unicodedata.normalize("NFKC", str(password))
    p = p.replace("\r", "").replace("\n", "")
    return p.strip()


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        _ITERATIONS,
    )
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${dk.hex()}"


def _verify_password(stored: str, password: str) -> bool:
    if not stored or password is None:
        return False
    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iters = int(parts[1])
        salt = bytes.fromhex(parts[2])
        want = parts[3]
    except (ValueError, IndexError):
        return False
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iters,
    )
    # Compare hex case-insensitively (some tools store uppercase; Python .hex() is lower)
    return secrets.compare_digest(dk.hex().lower(), (want or "").strip().lower())


def _pbkdf2_record_looks_valid(stored: str) -> bool:
    parts = (stored or "").strip().split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iters = int(parts[1])
        if iters < 1:
            return False
        salt = parts[2]
        digest = parts[3]
        if len(salt) % 2 != 0 or not all(c in "0123456789abcdefABCDEF" for c in salt):
            return False
        bytes.fromhex(salt)
        if len(digest) != 64 or not all(c in "0123456789abcdefABCDEF" for c in digest):
            return False
    except (ValueError, TypeError):
        return False
    return True


class AuthService:
    def has_any_users(self) -> bool:
        """True if at least one row exists in ``users`` (shop already provisioned)."""
        try:
            row = db.fetchone("SELECT COUNT(*) AS n FROM users")
            return int(row["n"] or 0) > 0 if row else False
        except sqlite3.OperationalError:
            return False

    def ensure_default_users(self) -> None:
        """If the database has no users yet, create the built-in admin (password: admin).

        Skipped once any account exists (e.g. after **Register new shop**).
        """
        try:
            row = db.fetchone("SELECT COUNT(*) AS n FROM users")
            if not row or int(row["n"] or 0) > 0:
                return
        except sqlite3.OperationalError:
            return

        pw = _hash_password("admin")
        try:
            db.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                ("admin", pw, "Administrator", "owner"),
            )
        except sqlite3.IntegrityError:
            pass

    def register_new_shop(
        self,
        *,
        shop_name: str,
        full_name: str,
        username: str,
        password: str,
    ) -> dict:
        """Create the first owner account and shop name. Only when no users exist."""
        if self.has_any_users():
            raise ValueError("This device already has a shop. Sign in with your account.")

        from app.services.shop_settings import ShopSettings

        sn = (shop_name or "").strip()
        if not sn:
            raise ValueError("Shop name is required.")
        name = (full_name or "").strip()
        if not name:
            raise ValueError("Your full name is required.")
        uname = (username or "").strip()
        if not uname:
            raise ValueError("Username is required.")
        if len(uname) > 64:
            raise ValueError("Username is too long.")
        pwd = _normalize_password(password)
        if len(pwd) < 4:
            raise ValueError("Password must be at least 4 characters.")
        h = _hash_password(pwd)
        try:
            db.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, 'owner', 1)
                """,
                (uname, h, name),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Username “{uname}” is already taken.") from None

        ShopSettings().set_shop_name(sn)

        row = db.fetchone(
            """
            SELECT id, username, full_name, role
            FROM users WHERE lower(username) = lower(?)
            """,
            (uname,),
        )
        if not row:
            raise ValueError("Registration failed.")
        return {
            "id": row["id"],
            "username": row["username"],
            "full_name": row["full_name"],
            "role": row["role"],
        }

    def authenticate(self, username: str, password: str) -> dict | None:
        username = (username or "").strip()
        if not username:
            return None
        try:
            row = db.fetchone(
                """
                SELECT id, username, password_hash, full_name, role
                FROM users WHERE lower(username) = lower(?) AND is_active = 1
                """,
                (username,),
            )
        except sqlite3.OperationalError:
            return None

        if not row:
            return None

        stored = row["password_hash"]
        if isinstance(stored, bytes):
            stored = stored.decode("utf-8", errors="replace")
        stored = (stored or "").strip()

        pwd = _normalize_password(password)

        ok = _verify_password(stored, pwd)
        if (
            not ok
            and username.lower() == "admin"
            and pwd == "admin"
            and not _pbkdf2_record_looks_valid(stored)
        ):
            new_h = _hash_password("admin")
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_h, row["id"]),
            )
            ok = _verify_password(new_h, pwd)

        if not ok:
            return None

        return {
            "id": row["id"],
            "username": row["username"],
            "full_name": row["full_name"],
            "role": row["role"],
        }

    @staticmethod
    def is_owner(user: dict | None) -> bool:
        return str((user or {}).get("role") or "").lower() == "owner"

    def _require_owner(self, acting_user: dict | None) -> None:
        if not self.is_owner(acting_user):
            raise ValueError("Only an owner can manage user accounts.")

    def _acting_id(self, acting_user: dict | None) -> int | None:
        uid = (acting_user or {}).get("id")
        return int(uid) if uid is not None else None

    def list_users(self, acting_user: dict | None) -> list[dict]:
        self._require_owner(acting_user)
        rows = db.fetchall(
            """
            SELECT id, username, full_name, role, is_active
            FROM users
            ORDER BY lower(username)
            """
        )
        return [dict(r) for r in rows]

    def get_user(self, acting_user: dict | None, user_id: int) -> dict | None:
        self._require_owner(acting_user)
        row = db.fetchone(
            """
            SELECT id, username, full_name, role, is_active
            FROM users WHERE id = ?
            """,
            (int(user_id),),
        )
        return dict(row) if row else None

    def _active_owner_count(self) -> int:
        row = db.fetchone(
            """
            SELECT COUNT(*) AS n FROM users
            WHERE lower(role) = 'owner' AND is_active = 1
            """
        )
        return int(row["n"] or 0) if row else 0

    def create_user(
        self,
        acting_user: dict | None,
        *,
        username: str,
        password: str,
        full_name: str,
        role: str = "staff",
    ) -> int:
        self._require_owner(acting_user)
        uname = (username or "").strip()
        if not uname:
            raise ValueError("Username is required.")
        if len(uname) > 64:
            raise ValueError("Username is too long.")
        pwd = _normalize_password(password)
        if len(pwd) < 4:
            raise ValueError("Password must be at least 4 characters.")
        name = (full_name or "").strip()
        if not name:
            raise ValueError("Full name is required.")
        r = (role or "staff").strip().lower()
        if r not in ("owner", "staff"):
            raise ValueError("Role must be owner or staff.")
        h = _hash_password(pwd)
        try:
            db.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (uname, h, name, r),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Username “{uname}” is already taken.") from None
        row = db.fetchone(
            "SELECT id FROM users WHERE lower(username) = lower(?)",
            (uname,),
        )
        return int(row["id"]) if row else 0

    def update_user(
        self,
        acting_user: dict | None,
        user_id: int,
        *,
        full_name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        self._require_owner(acting_user)
        uid = int(user_id)
        row = db.fetchone(
            "SELECT id, username, role, is_active FROM users WHERE id = ?",
            (uid,),
        )
        if not row:
            raise ValueError("User not found.")
        actor_id = self._acting_id(acting_user)
        was_owner = str(row["role"] or "").lower() == "owner"
        was_active = bool(row["is_active"])

        new_role = str(row["role"] or "")
        if role is not None:
            new_role = (role or "").strip().lower()
            if new_role not in ("owner", "staff"):
                raise ValueError("Role must be owner or staff.")
        new_active = was_active if is_active is None else bool(is_active)

        if actor_id == uid:
            if is_active is False:
                raise ValueError("You cannot deactivate your own account.")
            if role is not None and new_role == "staff" and was_owner:
                raise ValueError("You cannot remove your own owner role.")

        if was_owner and was_active:
            if not new_active and self._active_owner_count() <= 1:
                raise ValueError("Cannot deactivate the only active owner.")
            if new_role == "staff" and self._active_owner_count() <= 1:
                raise ValueError("Cannot demote the only active owner.")

        if full_name is not None:
            name = (full_name or "").strip()
            if not name:
                raise ValueError("Full name cannot be empty.")
            db.execute("UPDATE users SET full_name = ? WHERE id = ?", (name, uid))

        if role is not None:
            db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, uid))

        if is_active is not None:
            db.execute(
                "UPDATE users SET is_active = ? WHERE id = ?",
                (1 if new_active else 0, uid),
            )

    def set_password(self, acting_user: dict | None, user_id: int, new_password: str) -> None:
        self._require_owner(acting_user)
        uid = int(user_id)
        row = db.fetchone("SELECT id FROM users WHERE id = ?", (uid,))
        if not row:
            raise ValueError("User not found.")
        pwd = _normalize_password(new_password)
        if len(pwd) < 4:
            raise ValueError("Password must be at least 4 characters.")
        h = _hash_password(pwd)
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (h, uid))

    def get_session_user(self, user_id: int) -> dict | None:
        """Return the same user dict shape as ``authenticate`` for an active account, or None."""
        row = db.fetchone(
            """
            SELECT id, username, full_name, role
            FROM users WHERE id = ? AND is_active = 1
            """,
            (int(user_id),),
        )
        if not row:
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "full_name": row["full_name"],
            "role": row["role"],
        }

    def update_own_profile(
        self,
        acting_user: dict | None,
        *,
        full_name: str,
        username: str,
    ) -> dict:
        """Update the signed-in user's display name and login username (any active user)."""
        uid = self._acting_id(acting_user)
        if uid is None:
            raise ValueError("Not signed in.")
        row = db.fetchone(
            "SELECT id, username, full_name, is_active FROM users WHERE id = ?",
            (uid,),
        )
        if not row:
            raise ValueError("User not found.")
        if not int(row["is_active"] or 0):
            raise ValueError("Your account is inactive.")
        name = (full_name or "").strip()
        if not name:
            raise ValueError("Full name is required.")
        uname = (username or "").strip()
        if not uname:
            raise ValueError("Username is required.")
        if len(uname) > 64:
            raise ValueError("Username is too long.")
        clash = db.fetchone(
            "SELECT id FROM users WHERE lower(username) = lower(?) AND id != ?",
            (uname, uid),
        )
        if clash:
            raise ValueError(f"Username “{uname}” is already taken.")
        try:
            db.execute(
                "UPDATE users SET full_name = ?, username = ? WHERE id = ?",
                (name, uname, uid),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Username “{uname}” is already taken.") from None
        snap = self.get_session_user(uid)
        if not snap:
            raise ValueError("Could not reload your profile.")
        return snap

    def change_own_password(
        self,
        acting_user: dict | None,
        current_password: str,
        new_password: str,
    ) -> None:
        """Verify the current password, then set a new one (any active user)."""
        uid = self._acting_id(acting_user)
        if uid is None:
            raise ValueError("Not signed in.")
        row = db.fetchone(
            "SELECT password_hash, is_active FROM users WHERE id = ?",
            (uid,),
        )
        if not row:
            raise ValueError("User not found.")
        if not int(row["is_active"] or 0):
            raise ValueError("Your account is inactive.")
        stored = row["password_hash"]
        if isinstance(stored, bytes):
            stored = stored.decode("utf-8", errors="replace")
        stored = (stored or "").strip()
        cur = _normalize_password(current_password)
        if not _verify_password(stored, cur):
            raise ValueError("Current password is incorrect.")
        pwd = _normalize_password(new_password)
        if len(pwd) < 4:
            raise ValueError("New password must be at least 4 characters.")
        h = _hash_password(pwd)
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (h, uid))
