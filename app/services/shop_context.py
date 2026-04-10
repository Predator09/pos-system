"""Per-shop data directories under ``data/shops/<id>/`` — multiple shops on one machine."""

from __future__ import annotations

import json
import re
from collections import Counter
import shutil
from pathlib import Path

from app.runtime_paths import get_data_dir

_DATA_ROOT = get_data_dir()
SHOPS_ROOT = _DATA_ROOT / "shops"
LAST_SHOP_FILE = _DATA_ROOT / "last_shop.json"
DEFAULT_SHOP_ID = "main"
LEGACY_DB = _DATA_ROOT / "pos_system.db"

_current_shop_id: str = DEFAULT_SHOP_ID


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return s[:48] or "shop"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def ensure_legacy_migrated() -> None:
    """Move old flat ``data/`` layout into ``data/shops/main/`` once."""
    SHOPS_ROOT.mkdir(parents=True, exist_ok=True)
    main_root = SHOPS_ROOT / DEFAULT_SHOP_ID
    main_db = main_root / "pos_system.db"
    if LEGACY_DB.is_file() and not main_db.is_file():
        main_root.mkdir(parents=True, exist_ok=True)
        shutil.move(str(LEGACY_DB), str(main_db))
        legacy_settings = _DATA_ROOT / "shop_settings.json"
        if legacy_settings.is_file():
            shutil.move(str(legacy_settings), str(main_root / "shop_settings.json"))
        for folder in ("shop", "product_images", "receipts", "backups"):
            p = _DATA_ROOT / folder
            dest = main_root / folder
            if p.is_dir() and not dest.exists():
                try:
                    shutil.move(str(p), str(dest))
                except OSError:
                    pass


def ensure_shop_tree(shop_id: str) -> Path:
    """Create shop folder and standard subfolders (no DB file)."""
    root = SHOPS_ROOT / shop_id
    root.mkdir(parents=True, exist_ok=True)
    for sub in ("shop", "product_images", "receipts", "backups"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def shop_combo_entries(shops: list[dict]) -> tuple[list[str], list[str]]:
    """Return ``(labels, ids)`` for UI pickers; disambiguate duplicate display names."""
    names = [((s.get("name") or s["id"]) or "").strip() or s["id"] for s in shops]
    c = Counter(names)
    labels: list[str] = []
    ids: list[str] = []
    for s, base in zip(shops, names):
        lab = base
        if c[base] > 1:
            lab = f"{base} ({s['id']})"
        labels.append(lab)
        ids.append(s["id"])
    return labels, ids


def list_shops() -> list[dict]:
    """Shops that have (or can have) a database under ``data/shops/<id>/``."""
    ensure_legacy_migrated()
    SHOPS_ROOT.mkdir(parents=True, exist_ok=True)
    out: list[dict] = []
    if not any(SHOPS_ROOT.iterdir()):
        ensure_shop_tree(DEFAULT_SHOP_ID)
    for d in sorted(SHOPS_ROOT.iterdir(), key=lambda p: p.name.lower()):
        if not d.is_dir():
            continue
        sid = d.name
        dbf = d / "pos_system.db"
        name = _read_json(d / "shop_settings.json").get("shop_name")
        if isinstance(name, str) and name.strip():
            label = name.strip()
        else:
            label = sid.replace("-", " ").title() if sid != DEFAULT_SHOP_ID else "Main shop"
        out.append({"id": sid, "name": label, "has_database": dbf.is_file()})
    if not out:
        ensure_shop_tree(DEFAULT_SHOP_ID)
        out.append({"id": DEFAULT_SHOP_ID, "name": "Main shop", "has_database": False})
    return out


def get_current_shop_id() -> str:
    return _current_shop_id


def set_current_shop_id(shop_id: str) -> None:
    global _current_shop_id
    _current_shop_id = (shop_id or DEFAULT_SHOP_ID).strip() or DEFAULT_SHOP_ID


def load_last_shop_id() -> str:
    data = _read_json(LAST_SHOP_FILE)
    raw = (data.get("shop_id") or DEFAULT_SHOP_ID).strip()
    return raw or DEFAULT_SHOP_ID


def save_last_shop_id(shop_id: str) -> None:
    LAST_SHOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_SHOP_FILE.write_text(
        json.dumps({"shop_id": shop_id}, indent=2),
        encoding="utf-8",
    )


def apply_stored_shop() -> None:
    """Set current shop from ``last_shop.json`` if that shop exists."""
    ensure_legacy_migrated()
    want = load_last_shop_id()
    for s in list_shops():
        if s["id"] == want:
            set_current_shop_id(want)
            return
    set_current_shop_id(DEFAULT_SHOP_ID)
    save_last_shop_id(DEFAULT_SHOP_ID)


def shop_root() -> Path:
    return SHOPS_ROOT / get_current_shop_id()


def database_path() -> Path:
    return shop_root() / "pos_system.db"


def receipts_dir() -> Path:
    p = shop_root() / "receipts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def backups_dir() -> Path:
    p = shop_root() / "backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def product_images_dir() -> Path:
    p = shop_root() / "product_images"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logo_dir() -> Path:
    p = shop_root() / "shop"
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_new_shop(display_name: str) -> str:
    """Create a new shop folder and return its id. Does not open the database."""
    ensure_legacy_migrated()
    base = slugify(display_name)
    shop_id = base
    n = 2
    while (SHOPS_ROOT / shop_id).exists():
        shop_id = f"{base}-{n}"
        n += 1
    ensure_shop_tree(shop_id)
    data = {"shop_name": (display_name or "").strip()[:120] or shop_id}
    (SHOPS_ROOT / shop_id / "shop_settings.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )
    return shop_id


def open_shop_database(db, shop_id: str) -> None:
    """Switch SQLite to this shop, run migrations, and connect."""
    from app.database.migrations import DatabaseMigrations

    set_current_shop_id(shop_id)
    save_last_shop_id(shop_id)
    db.reconfigure(str(database_path()))
    DatabaseMigrations(db).init_database()
    db.connect()


def delete_shop(shop_id: str, db) -> str:
    """Permanently remove a shop directory (database, images, backups, receipts).

    Requires at least two shops. If ``shop_id`` is the active shop, closes the DB,
    switches to another shop, reconnects, then removes the old folder.

    Returns the active shop id after the operation.
    """
    ensure_legacy_migrated()
    shops = [s["id"] for s in list_shops()]
    if shop_id not in shops:
        raise ValueError("That shop does not exist.")
    if len(shops) < 2:
        raise ValueError("You cannot delete the only shop.")

    root = SHOPS_ROOT / shop_id
    if shop_id == get_current_shop_id():
        alt = next(sid for sid in shops if sid != shop_id)
        db.close()
        open_shop_database(db, alt)

    if root.is_dir():
        shutil.rmtree(root)

    return get_current_shop_id()
