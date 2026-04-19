class DatabaseMigrations:
    def __init__(self, db_connection):
        self.db = db_connection

    def init_database(self):
        """Initialize database with all tables."""
        self.db.connect()

        # Version table
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS db_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Check current version
        result = self.db.fetchone("SELECT MAX(version) FROM db_version")
        current_version = result[0] if result and result[0] is not None else 0

        # Apply pending migrations
        if current_version < 1:
            self._migrate_v1(current_version)
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else 0

        if current_version < 2:
            self._migrate_v2(current_version)
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 3:
            self._migrate_v3()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 4:
            self._migrate_v4()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 5:
            self._migrate_v5()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 6:
            self._migrate_v6()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 7:
            self._migrate_v7()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 8:
            self._migrate_v8()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 9:
            self._migrate_v9()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 10:
            self._migrate_v10()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 11:
            self._migrate_v11()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 12:
            self._migrate_v12()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 13:
            self._migrate_v13()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 14:
            self._migrate_v14()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        if current_version < 15:
            self._migrate_v15()
            result = self.db.fetchone("SELECT MAX(version) FROM db_version")
            current_version = result[0] if result and result[0] is not None else current_version

        self.db.close()

    def _migrate_v1(self, from_version):
        """Initial schema - all tables."""

        # Products table
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                category TEXT,
                description TEXT,
                quantity_in_stock REAL DEFAULT 0 CHECK (quantity_in_stock >= 0),
                minimum_stock_level REAL DEFAULT 10 CHECK (minimum_stock_level >= 0),
                maximum_stock_level REAL DEFAULT 1000 CHECK (maximum_stock_level >= 0),
                cost_price REAL NOT NULL CHECK (cost_price >= 0),
                selling_price REAL NOT NULL CHECK (selling_price >= 0),
                discount_percentage REAL DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Sales table
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE NOT NULL,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subtotal REAL NOT NULL,
                discount_amount REAL DEFAULT 0,
                tax_amount REAL DEFAULT 0,
                total_amount REAL NOT NULL,
                payment_method TEXT,
                customer_name TEXT,
                notes TEXT,
                is_synced BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Sale items table
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL CHECK (quantity > 0),
                unit_price REAL NOT NULL CHECK (unit_price >= 0),
                discount_percentage REAL DEFAULT 0,
                total REAL NOT NULL CHECK (total >= 0),
                FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        )

        # Purchases table
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL CHECK (quantity > 0),
                cost_price REAL NOT NULL CHECK (cost_price >= 0),
                supplier_name TEXT,
                notes TEXT,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        )

        # Sync log table (tracks changes for backup/sync)
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                operation TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced BOOLEAN DEFAULT 0
            )
            """
        )

        # Record migration
        self.db.execute("INSERT INTO db_version (version) VALUES (?)", (1,))

    def _migrate_v2(self, from_version):
        """Users for sign-in."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'staff',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.db.execute(
            "INSERT OR IGNORE INTO db_version (version) VALUES (?)", (2,)
        )

    def _migrate_v3(self):
        """Product expiry and image path for inventory UI."""
        cols = {row[1] for row in self.db.fetchall("PRAGMA table_info(products)")}
        if "expiry_date" not in cols:
            self.db.execute("ALTER TABLE products ADD COLUMN expiry_date TEXT")
        if "image_path" not in cols:
            self.db.execute("ALTER TABLE products ADD COLUMN image_path TEXT")
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (3,))

    def _migrate_v4(self):
        """Parked (held) sales for POS — survives app restart."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS parked_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_ref TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                customer TEXT,
                payment TEXT,
                tender TEXT,
                cart_json TEXT NOT NULL
            )
            """
        )
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (4,))

    def _migrate_v5(self):
        """Goods receipt headers (GRN) + link purchase lines to receipts."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS purchase_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT UNIQUE NOT NULL,
                supplier_name TEXT,
                notes TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cols = {row[1] for row in self.db.fetchall("PRAGMA table_info(purchases)")}
        if "receipt_id" not in cols:
            self.db.execute(
                "ALTER TABLE purchases ADD COLUMN receipt_id INTEGER REFERENCES purchase_receipts(id)"
            )
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (5,))

    def _migrate_v6(self):
        """Supplier contact on goods receipts (GRN)."""
        cols = {row[1] for row in self.db.fetchall("PRAGMA table_info(purchase_receipts)")}
        if "supplier_phone" not in cols:
            self.db.execute("ALTER TABLE purchase_receipts ADD COLUMN supplier_phone TEXT")
        if "supplier_email" not in cols:
            self.db.execute("ALTER TABLE purchase_receipts ADD COLUMN supplier_email TEXT")
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (6,))

    def _migrate_v7(self):
        """Registered suppliers directory (reusable on GRNs)."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT,
                notes TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        rcols = {row[1] for row in self.db.fetchall("PRAGMA table_info(purchase_receipts)")}
        if "supplier_id" not in rcols:
            self.db.execute(
                "ALTER TABLE purchase_receipts ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)"
            )
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (7,))

    def _migrate_v8(self):
        """Separate retail barcode from internal product code (``code`` / PC)."""
        cols = {row[1] for row in self.db.fetchall("PRAGMA table_info(products)")}
        if "barcode" not in cols:
            self.db.execute("ALTER TABLE products ADD COLUMN barcode TEXT")
        self.db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_products_barcode_unique
            ON products(barcode)
            WHERE barcode IS NOT NULL AND TRIM(barcode) != ''
            """
        )
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (8,))

    def _migrate_v9(self):
        """Cashier / staff name on sales for receipts."""
        cols = {row[1] for row in self.db.fetchall("PRAGMA table_info(sales)")}
        if "cashier_name" not in cols:
            self.db.execute("ALTER TABLE sales ADD COLUMN cashier_name TEXT")
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (9,))

    def _migrate_v10(self):
        """Returns / refunds linked to original sales; stock restored; revenue net of refunds."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS sale_returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                credit_memo_number TEXT UNIQUE NOT NULL,
                return_date TIMESTAMP NOT NULL,
                total_refund_amount REAL NOT NULL CHECK (total_refund_amount >= 0),
                payment_method TEXT,
                notes TEXT,
                cashier_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sale_id) REFERENCES sales(id)
            )
            """
        )
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS sale_return_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_return_id INTEGER NOT NULL,
                sale_item_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity_returned REAL NOT NULL CHECK (quantity_returned > 0),
                line_refund_amount REAL NOT NULL CHECK (line_refund_amount >= 0),
                FOREIGN KEY (sale_return_id) REFERENCES sale_returns(id) ON DELETE CASCADE,
                FOREIGN KEY (sale_item_id) REFERENCES sale_items(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_sale_returns_sale_id ON sale_returns(sale_id)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_sale_returns_return_date ON sale_returns(return_date)"
        )
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (10,))

    def _migrate_v11(self):
        """Enforce DB-level business rules with CHECK constraints."""
        self._assert_no_invalid_rows(
            "products",
            "quantity_in_stock < 0 OR minimum_stock_level < 0 OR maximum_stock_level < 0 OR cost_price < 0 OR selling_price < 0",
        )
        self._assert_no_invalid_rows(
            "sale_items",
            "quantity <= 0 OR unit_price < 0 OR total < 0",
        )
        self._assert_no_invalid_rows(
            "purchases",
            "quantity <= 0 OR cost_price < 0",
        )
        self._assert_no_invalid_rows(
            "sale_returns",
            "total_refund_amount < 0",
        )
        self._assert_no_invalid_rows(
            "sale_return_items",
            "quantity_returned <= 0 OR line_refund_amount < 0",
        )

        self.db.execute("PRAGMA foreign_keys = OFF")

        # Rebuild products to add CHECK constraints.
        self.db.execute(
            """
            CREATE TABLE products_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                category TEXT,
                description TEXT,
                quantity_in_stock REAL DEFAULT 0 CHECK (quantity_in_stock >= 0),
                minimum_stock_level REAL DEFAULT 10 CHECK (minimum_stock_level >= 0),
                maximum_stock_level REAL DEFAULT 1000 CHECK (maximum_stock_level >= 0),
                cost_price REAL NOT NULL CHECK (cost_price >= 0),
                selling_price REAL NOT NULL CHECK (selling_price >= 0),
                discount_percentage REAL DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiry_date TEXT,
                image_path TEXT,
                barcode TEXT
            )
            """
        )
        self.db.execute(
            """
            INSERT INTO products_new (
                id, name, code, category, description, quantity_in_stock, minimum_stock_level,
                maximum_stock_level, cost_price, selling_price, discount_percentage, is_active,
                created_at, updated_at, expiry_date, image_path, barcode
            )
            SELECT
                id, name, code, category, description, quantity_in_stock, minimum_stock_level,
                maximum_stock_level, cost_price, selling_price, discount_percentage, is_active,
                created_at, updated_at, expiry_date, image_path, barcode
            FROM products
            """
        )
        self.db.execute("DROP TABLE products")
        self.db.execute("ALTER TABLE products_new RENAME TO products")
        self.db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_products_barcode_unique
            ON products(barcode)
            WHERE barcode IS NOT NULL AND TRIM(barcode) != ''
            """
        )

        # Rebuild sale_items to add CHECK constraints.
        self.db.execute(
            """
            CREATE TABLE sale_items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL CHECK (quantity > 0),
                unit_price REAL NOT NULL CHECK (unit_price >= 0),
                discount_percentage REAL DEFAULT 0,
                total REAL NOT NULL CHECK (total >= 0),
                FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        )
        self.db.execute(
            """
            INSERT INTO sale_items_new (
                id, sale_id, product_id, quantity, unit_price, discount_percentage, total
            )
            SELECT
                id, sale_id, product_id, quantity, unit_price, discount_percentage, total
            FROM sale_items
            """
        )
        self.db.execute("DROP TABLE sale_items")
        self.db.execute("ALTER TABLE sale_items_new RENAME TO sale_items")

        # Rebuild purchases to add CHECK constraints.
        self.db.execute(
            """
            CREATE TABLE purchases_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL CHECK (quantity > 0),
                cost_price REAL NOT NULL CHECK (cost_price >= 0),
                supplier_name TEXT,
                notes TEXT,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                receipt_id INTEGER REFERENCES purchase_receipts(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        )
        self.db.execute(
            """
            INSERT INTO purchases_new (
                id, product_id, quantity, cost_price, supplier_name, notes,
                purchase_date, created_at, receipt_id
            )
            SELECT
                id, product_id, quantity, cost_price, supplier_name, notes,
                purchase_date, created_at, receipt_id
            FROM purchases
            """
        )
        self.db.execute("DROP TABLE purchases")
        self.db.execute("ALTER TABLE purchases_new RENAME TO purchases")

        # Rebuild sale_returns to add CHECK constraints.
        self.db.execute(
            """
            CREATE TABLE sale_returns_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                credit_memo_number TEXT UNIQUE NOT NULL,
                return_date TIMESTAMP NOT NULL,
                total_refund_amount REAL NOT NULL CHECK (total_refund_amount >= 0),
                payment_method TEXT,
                notes TEXT,
                cashier_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sale_id) REFERENCES sales(id)
            )
            """
        )
        self.db.execute(
            """
            INSERT INTO sale_returns_new (
                id, sale_id, credit_memo_number, return_date, total_refund_amount,
                payment_method, notes, cashier_name, created_at
            )
            SELECT
                id, sale_id, credit_memo_number, return_date, total_refund_amount,
                payment_method, notes, cashier_name, created_at
            FROM sale_returns
            """
        )
        self.db.execute("DROP TABLE sale_returns")
        self.db.execute("ALTER TABLE sale_returns_new RENAME TO sale_returns")
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_sale_returns_sale_id ON sale_returns(sale_id)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_sale_returns_return_date ON sale_returns(return_date)"
        )

        # Rebuild sale_return_items to add CHECK constraints.
        self.db.execute(
            """
            CREATE TABLE sale_return_items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_return_id INTEGER NOT NULL,
                sale_item_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity_returned REAL NOT NULL CHECK (quantity_returned > 0),
                line_refund_amount REAL NOT NULL CHECK (line_refund_amount >= 0),
                FOREIGN KEY (sale_return_id) REFERENCES sale_returns(id) ON DELETE CASCADE,
                FOREIGN KEY (sale_item_id) REFERENCES sale_items(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        )
        self.db.execute(
            """
            INSERT INTO sale_return_items_new (
                id, sale_return_id, sale_item_id, product_id, quantity_returned, line_refund_amount
            )
            SELECT
                id, sale_return_id, sale_item_id, product_id, quantity_returned, line_refund_amount
            FROM sale_return_items
            """
        )
        self.db.execute("DROP TABLE sale_return_items")
        self.db.execute("ALTER TABLE sale_return_items_new RENAME TO sale_return_items")

        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (11,))

    def _assert_no_invalid_rows(self, table_name, invalid_where_clause):
        invalid_row = self.db.fetchone(
            f"SELECT id FROM {table_name} WHERE {invalid_where_clause} LIMIT 1"
        )
        if invalid_row:
            raise ValueError(
                f"Cannot apply migration v11: invalid row exists in {table_name} "
                f"(id={invalid_row[0]})."
            )

    def _migrate_v12(self):
        """Store monetary amounts in integer cents to avoid float drift."""
        table_cols = {
            "sales": (
                ("subtotal_cents", "subtotal"),
                ("discount_amount_cents", "discount_amount"),
                ("tax_amount_cents", "tax_amount"),
                ("total_amount_cents", "total_amount"),
            ),
            "sale_items": (
                ("unit_price_cents", "unit_price"),
                ("total_cents", "total"),
            ),
            "sale_returns": (("total_refund_amount_cents", "total_refund_amount"),),
            "sale_return_items": (("line_refund_amount_cents", "line_refund_amount"),),
        }

        for table, mappings in table_cols.items():
            cols = {row[1] for row in self.db.fetchall(f"PRAGMA table_info({table})")}
            for cents_col, legacy_col in mappings:
                if cents_col not in cols:
                    self.db.execute(
                        f"ALTER TABLE {table} ADD COLUMN {cents_col} INTEGER NOT NULL DEFAULT 0"
                    )
                self.db.execute(
                    f"""
                    UPDATE {table}
                    SET {cents_col} = CAST(ROUND(COALESCE({legacy_col}, 0) * 100.0, 0) AS INTEGER)
                    WHERE {cents_col} IS NULL OR {cents_col} = 0
                    """
                )

        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (12,))

    def _migrate_v13(self):
        """Add first-login password rotation flag to users."""
        cols = {row[1] for row in self.db.fetchall("PRAGMA table_info(users)")}
        if "must_change_password" not in cols:
            self.db.execute(
                "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0"
            )
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (13,))

    def _migrate_v14(self):
        """Centralized audit trail table for business and admin events."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                actor_user_id INTEGER,
                details_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events(created_at)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type)"
        )
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (14,))

    def _migrate_v15(self):
        """Indexes for reports date-range filters and sort patterns."""
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_sales_sale_date_id ON sales(sale_date, id)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_sale_returns_return_date_id ON sale_returns(return_date, id)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_purchase_receipts_received_at ON purchase_receipts(received_at)"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_purchase_receipts_created_at ON purchase_receipts(created_at)"
        )
        self.db.execute("INSERT OR IGNORE INTO db_version (version) VALUES (?)", (15,))
