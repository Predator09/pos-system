#!/usr/bin/env python3
"""
Seed ~300 demo mini-market products (and a few suppliers) into the active shop DB.

Codes use prefix MMD- (Mini Market Demo). Safe to re-run: skips if 300+ MMD- rows exist,
unless --force (removes demo products and related sale/purchase lines first).

Run from the pos-system folder:
    python seed_mini_market_demo.py
    python seed_mini_market_demo.py --shop main --force
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.database.connection as connmod
from app.database.migrations import DatabaseMigrations
from app.services.product_service import ProductService
from app.services.shop_context import (
    apply_stored_shop,
    database_path,
    ensure_legacy_migrated,
    save_last_shop_id,
)

CODE_PREFIX = "MMD-"
TARGET_COUNT = 300
DEMO_SUPPLIERS = [
    ("Wholesale Gambia Ltd", "+220 700 0001", "orders@example.com"),
    ("Banjul Beverage Co.", "+220 700 0002", None),
    ("Coastal Dry Goods", "+220 700 0003", "sales@example.com"),
    ("FreshLink Distributors", None, None),
    ("Atlantic Imports", "+220 700 0005", "info@example.com"),
]


def _catalog_pools() -> dict[str, list[str]]:
    """Category -> product name stems (combined with optional brand suffix for variety)."""
    return {
        "Beverages": [
            "Still water 500ml",
            "Still water 1.5L",
            "Sparkling water 750ml",
            "Cola 350ml",
            "Cola 1L",
            "Orange soda 350ml",
            "Grape soda 350ml",
            "Lemon-lime soda 500ml",
            "Ginger beer 330ml",
            "Tonic water 1L",
            "Club soda 500ml",
            "Iced tea lemon 500ml",
            "Iced tea peach 500ml",
            "Energy drink 250ml",
            "Sports drink citrus 500ml",
            "Mango juice 1L",
            "Guava juice 1L",
            "Pineapple juice 1L",
            "Apple juice 1L",
            "Tomato juice 1L",
            "Long-life milk 1L",
            "Chocolate milk 250ml",
            "Drinking yogurt strawberry",
            "Drinking yogurt vanilla",
            "Instant coffee 200g",
            "Black tea 25 bags",
            "Green tea 25 bags",
            "Cocoa powder 400g",
            "Bottled coffee latte 240ml",
        ],
        "Snacks & candy": [
            "Salted crisps 150g",
            "BBQ crisps 150g",
            "Cheese puffs 120g",
            "Plantain chips 100g",
            "Roasted peanuts 200g",
            "Mixed nuts 150g",
            "Chocolate bar 45g",
            "Wafer sticks hazelnut",
            "Chewy candy mix 200g",
            "Mint drops 80g",
            "Bubble gum 5-pack",
            "Cookies butter 300g",
            "Digestive biscuits 400g",
            "Cream crackers 250g",
            "Granola bar honey",
            "Energy bar peanut",
            "Rice cakes lightly salted",
            "Popcorn butter 100g",
            "Dried mango 100g",
            "Trail mix 200g",
        ],
        "Dairy & chilled": [
            "Fresh milk 1L",
            "Low-fat milk 1L",
            "Yogurt plain 500g",
            "Yogurt strawberry 4-pack",
            "Butter 250g",
            "Margarine 500g",
            "Cheddar slices 200g",
            "Cream cheese 150g",
            "Eggs tray 30",
            "Eggs half-dozen",
            "Cottage cheese 250g",
            "Sour cream 200ml",
        ],
        "Bakery": [
            "White sliced bread 700g",
            "Brown bread 700g",
            "Baguette",
            "Croissant 4-pack",
            "Plain buns 6-pack",
            "Sweet rolls coconut",
            "Tea cakes 6-pack",
            "Doughnuts 4-pack",
        ],
        "Grocery staples": [
            "Rice parboiled 5kg",
            "Rice jasmine 2kg",
            "Spaghetti 500g",
            "Macaroni 500g",
            "Tomato paste 400g",
            "Cooking oil 1L",
            "Cooking oil 3L",
            "Palm oil 500ml",
            "Sugar 2kg",
            "Salt iodized 1kg",
            "Black pepper 100g",
            "Curry powder 200g",
            "Stock cubes 10-pack",
            "Baking powder 100g",
            "Flour all-purpose 2kg",
            "Lentils red 1kg",
            "Beans black 1kg",
            "Chickpeas dried 500g",
            "Oats quick 500g",
            "Cornflakes 500g",
            "Jam strawberry 450g",
            "Peanut butter 400g",
            "Honey squeeze 350g",
            "Vinegar 500ml",
            "Soy sauce 150ml",
            "Hot sauce 200ml",
        ],
        "Frozen": [
            "Mixed vegetables 1kg",
            "Green peas 400g",
            "Fish fingers 300g",
            "Chicken nuggets 400g",
            "Ice cream vanilla 1L",
            "Ice cream chocolate 500ml",
            "Frozen pizza cheese",
            "Frozen chapati 5-pack",
        ],
        "Household": [
            "Dish liquid 750ml",
            "Laundry powder 2kg",
            "Laundry liquid 1L",
            "Bleach 1L",
            "Floor cleaner 1L",
            "Glass cleaner 500ml",
            "Sponges 3-pack",
            "Trash bags medium 20",
            "Aluminum foil 10m",
            "Cling film 30m",
            "Paper towels 2-roll",
            "Toilet paper 9-roll",
            "Tissues box",
            "Air freshener spray",
            "Insect spray 400ml",
            "Matches 10-box",
            "Candles 4-pack",
            "Storage bags zip 20",
        ],
        "Personal care": [
            "Bar soap 4-pack",
            "Body wash 500ml",
            "Shampoo 400ml",
            "Conditioner 400ml",
            "Toothpaste 100ml",
            "Toothbrush soft",
            "Deodorant roll-on",
            "Face cream 50ml",
            "Hand sanitizer 200ml",
            "Baby wipes 72-count",
            "Razor disposable 5-pack",
            "Shaving foam 200ml",
        ],
        "Baby & kids": [
            "Baby formula stage 1 400g",
            "Baby cereal rice 200g",
            "Diapers size 3 24-pack",
            "Diapers size 4 22-pack",
            "Baby lotion 200ml",
            "Baby shampoo 200ml",
            "Kids fruit pouch 4-pack",
        ],
        "Pet": [
            "Dry dog food 2kg",
            "Dry cat food 1.5kg",
            "Dog treats 200g",
            "Cat treats 100g",
        ],
    }


def _pick_demo_products(rng: random.Random, n: int) -> list[tuple[str, str]]:
    pools = _catalog_pools()
    brands = ("Kuni", "Coastal", "Tropic", "River", "Baobab", "Sunrise", "Island", "Family")
    flat: list[tuple[str, str]] = []
    for cat, names in pools.items():
        for stem in names:
            flat.append((cat, stem))
    rng.shuffle(flat)
    out: list[tuple[str, str]] = []
    seen_names: set[str] = set()
    i = 0
    while len(out) < n and i < len(flat) * 3:
        cat, stem = flat[i % len(flat)]
        i += 1
        name = f"{rng.choice(brands)} {stem}"
        if name in seen_names:
            name = f"{name} ({len(out) + 1})"
        seen_names.add(name)
        out.append((cat, name))
    # If pool too small (shouldn't happen), pad with numbered generics
    g = 0
    while len(out) < n:
        g += 1
        out.append(("Grocery staples", f"Demo grocery item {g}"))
    return out[:n]


def _remove_demo_products(db) -> None:
    rows = db.fetchall(
        f"SELECT id FROM products WHERE code LIKE '{CODE_PREFIX}%'",
    )
    ids = [int(r[0]) for r in rows]
    if not ids:
        return
    ph = ",".join("?" * len(ids))
    db.execute(f"DELETE FROM sale_items WHERE product_id IN ({ph})", tuple(ids))
    try:
        db.execute(f"DELETE FROM purchases WHERE product_id IN ({ph})", tuple(ids))
    except Exception:
        pass
    db.execute(f"DELETE FROM products WHERE id IN ({ph})", tuple(ids))


def _count_demo(db) -> int:
    row = db.fetchone(f"SELECT COUNT(*) AS n FROM products WHERE code LIKE '{CODE_PREFIX}%'")
    return int(row[0] or 0) if row else 0


def _seed_suppliers(db) -> int:
    n = 0
    for name, phone, email in DEMO_SUPPLIERS:
        row = db.fetchone("SELECT 1 FROM suppliers WHERE name = ?", (name,))
        if row:
            continue
        db.execute(
            """
            INSERT INTO suppliers (name, phone, email, is_active)
            VALUES (?, ?, ?, 1)
            """,
            (name, phone, email),
        )
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed 300 mini-market demo products (MMD- SKUs).")
    ap.add_argument("--shop", help="Shop id (writes last_shop.json before opening DB)")
    ap.add_argument(
        "--force",
        action="store_true",
        help=f"Remove existing {CODE_PREFIX}* products (and their sale/purchase lines) then re-seed",
    )
    args = ap.parse_args()

    ensure_legacy_migrated()
    if args.shop:
        save_last_shop_id(args.shop.strip())
    apply_stored_shop()

    # Keep the same ``db`` singleton so ProductService (and other modules) stay in sync.
    connmod.db.close()
    connmod.db.reconfigure(str(database_path()))
    connmod.db.connect()
    DatabaseMigrations(connmod.db).init_database()
    connmod.db.connect()

    db = connmod.db
    path = database_path()
    print(f"Database: {path.resolve()}")

    existing = _count_demo(db)
    if existing >= TARGET_COUNT and not args.force:
        print(f"Already have {existing} demo products ({CODE_PREFIX}*). Use --force to replace.")
        return 0

    if args.force:
        print(f"Removing {existing} existing demo products...")
        _remove_demo_products(db)

    rng = random.Random(42)
    pairs = _pick_demo_products(rng, TARGET_COUNT)
    svc = ProductService()
    created = 0
    for idx, (category, name) in enumerate(pairs, start=1):
        code = f"{CODE_PREFIX}{idx:05d}"
        sell = round(rng.uniform(12.0, 480.0), 2)
        margin = rng.uniform(0.55, 0.82)
        cost = round(sell * margin, 2)
        stock = round(rng.uniform(0.0, 140.0), 1)
        min_lvl = max(5.0, round(rng.uniform(6.0, 24.0), 0))
        exp_roll = rng.random()
        expiry = None
        if exp_roll < 0.08:
            expiry = "2024-06-01"
        elif exp_roll < 0.35:
            d = date.today() + timedelta(days=rng.randint(14, 400))
            expiry = d.isoformat()

        svc.create_product(
            name=name,
            code=code,
            cost_price=cost,
            selling_price=sell,
            category=category,
            description="Demo mini-market catalog item (seed script).",
            quantity_in_stock=stock,
            minimum_stock_level=min_lvl,
            is_active=True,
            expiry_date=expiry,
        )
        created += 1
        if created % 50 == 0:
            print(f"  ... {created} products")

    sup_n = _seed_suppliers(db)
    print(f"Done. Created {created} products ({CODE_PREFIX}00001 - {CODE_PREFIX}{created:05d}).")
    print(f"New suppliers added: {sup_n}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
