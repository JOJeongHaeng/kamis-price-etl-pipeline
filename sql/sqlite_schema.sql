CREATE TABLE IF NOT EXISTS Category (
    category_code TEXT PRIMARY KEY,
    category_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Product (
    item_code TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    category_code TEXT NOT NULL REFERENCES Category(category_code)
);

CREATE TABLE IF NOT EXISTS ProductVariant (
    variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_code TEXT NOT NULL REFERENCES Product(item_code),
    variety_code TEXT NOT NULL,
    variety_name TEXT,
    UNIQUE(item_code, variety_code)
);

CREATE TABLE IF NOT EXISTS Grade (
    grade_code TEXT PRIMARY KEY,
    grade_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS RecentPriceSnapshot (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL REFERENCES ProductVariant(variant_id),
    grade_code TEXT NOT NULL REFERENCES Grade(grade_code),
    examined_date DATE NOT NULL,
    product_cls_code TEXT NOT NULL,
    product_cls_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    unit_size TEXT NOT NULL,
    price INTEGER NOT NULL,
    kg_price INTEGER,
    day_before_price INTEGER,
    day_before_kg_price INTEGER,
    week_before_price INTEGER,
    week_before_kg_price INTEGER,
    month_before_price INTEGER,
    month_before_kg_price INTEGER,
    year_before_price INTEGER,
    year_before_kg_price INTEGER,
    source_name TEXT NOT NULL,
    collected_at DATETIME NOT NULL,
    UNIQUE(variant_id, grade_code, examined_date, product_cls_code, unit, unit_size)
);
