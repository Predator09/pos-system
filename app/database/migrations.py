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
                quantity_in_stock REAL DEFAULT 0,
                minimum_stock_level REAL DEFAULT 10,
                maximum_stock_level REAL DEFAULT 1000,
                cost_price REAL NOT NULL,
                selling_price REAL NOT NULL,
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
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                discount_percentage REAL DEFAULT 0,
                total REAL NOT NULL,
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
                quantity REAL NOT NULL,
                cost_price REAL NOT NULL,
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
