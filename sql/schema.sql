CREATE TABLE IF NOT EXISTS Item (
    item_id INTEGER AUTO_INCREMENT NOT NULL,
    name VARCHAR(50) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    PRIMARY KEY (item_id),
    UNIQUE KEY uq_item_name_unit (name, unit)
);

CREATE TABLE IF NOT EXISTS Week (
    week_id INTEGER AUTO_INCREMENT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    week_no INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    PRIMARY KEY (week_id)
);

CREATE TABLE IF NOT EXISTS MarketPrice (
    MP_id INTEGER AUTO_INCREMENT NOT NULL,
    traditional_price INTEGER NOT NULL,
    largemarket_price INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    week_id INTEGER NOT NULL,
    PRIMARY KEY (MP_id),
    UNIQUE KEY uq_marketprice_item_week (item_id, week_id),
    CONSTRAINT fk_marketprice_item FOREIGN KEY (item_id) REFERENCES Item (item_id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT fk_marketprice_week FOREIGN KEY (week_id) REFERENCES Week (week_id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE TABLE IF NOT EXISTS WeeklyPrice (
    price_id INTEGER AUTO_INCREMENT NOT NULL,
    last_price INTEGER NOT NULL,
    current_price INTEGER NOT NULL,
    change_rate DECIMAL(5,2) NOT NULL,
    item_id INTEGER NOT NULL,
    week_id INTEGER NOT NULL,
    PRIMARY KEY (price_id),
    UNIQUE KEY uq_weeklyprice_week_item (week_id, item_id),
    CONSTRAINT fk_weeklyprice_item FOREIGN KEY (item_id) REFERENCES Item (item_id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT fk_weeklyprice_week FOREIGN KEY (week_id) REFERENCES Week (week_id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE TABLE IF NOT EXISTS WeeklyReport (
    report_id INTEGER AUTO_INCREMENT NOT NULL,
    summary TEXT NULL,
    season_food VARCHAR(100) NULL,
    week_id INTEGER NOT NULL,
    issue TEXT NULL,
    PRIMARY KEY (report_id),
    UNIQUE KEY uq_weeklyreport_week (week_id),
    CONSTRAINT fk_weeklyreport_week FOREIGN KEY (week_id) REFERENCES Week (week_id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE TABLE IF NOT EXISTS Category (
    category_code VARCHAR(20) NOT NULL,
    category_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (category_code)
);

CREATE TABLE IF NOT EXISTS Product (
    item_code VARCHAR(20) NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    category_code VARCHAR(20) NOT NULL,
    PRIMARY KEY (item_code),
    CONSTRAINT fk_product_category FOREIGN KEY (category_code) REFERENCES Category (category_code)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE TABLE IF NOT EXISTS ProductVariant (
    variant_id BIGINT AUTO_INCREMENT NOT NULL,
    item_code VARCHAR(20) NOT NULL,
    variety_code VARCHAR(20) NOT NULL,
    variety_name VARCHAR(100) NULL,
    PRIMARY KEY (variant_id),
    UNIQUE KEY uq_productvariant_item_variety (item_code, variety_code),
    CONSTRAINT fk_productvariant_product FOREIGN KEY (item_code) REFERENCES Product (item_code)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE TABLE IF NOT EXISTS Grade (
    grade_code VARCHAR(20) NOT NULL,
    grade_name VARCHAR(50) NOT NULL,
    PRIMARY KEY (grade_code)
);

CREATE TABLE IF NOT EXISTS RecentPriceSnapshot (
    snapshot_id BIGINT AUTO_INCREMENT NOT NULL,
    variant_id BIGINT NOT NULL,
    grade_code VARCHAR(20) NOT NULL,
    examined_date DATE NOT NULL,
    product_cls_code CHAR(2) NOT NULL,
    product_cls_name VARCHAR(20) NOT NULL,
    unit VARCHAR(30) NOT NULL,
    unit_size VARCHAR(30) NOT NULL,
    price INTEGER NOT NULL,
    kg_price INTEGER NULL,
    day_before_price INTEGER NULL,
    day_before_kg_price INTEGER NULL,
    week_before_price INTEGER NULL,
    week_before_kg_price INTEGER NULL,
    month_before_price INTEGER NULL,
    month_before_kg_price INTEGER NULL,
    year_before_price INTEGER NULL,
    year_before_kg_price INTEGER NULL,
    source_name VARCHAR(50) NOT NULL,
    collected_at DATETIME NOT NULL,
    PRIMARY KEY (snapshot_id),
    UNIQUE KEY uq_recentpricesnapshot_identity (
        variant_id, grade_code, examined_date, product_cls_code, unit, unit_size
    ),
    CONSTRAINT fk_recentpricesnapshot_variant FOREIGN KEY (variant_id) REFERENCES ProductVariant (variant_id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION,
    CONSTRAINT fk_recentpricesnapshot_grade FOREIGN KEY (grade_code) REFERENCES Grade (grade_code)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);

CREATE OR REPLACE VIEW KAMISPriceAnalysis AS
SELECT
    s.snapshot_id,
    c.category_code,
    c.category_name,
    p.item_code,
    p.item_name,
    v.variety_code,
    v.variety_name,
    g.grade_code,
    g.grade_name,
    s.examined_date,
    GREATEST(DATEDIFF(CURDATE(), s.examined_date), 0) AS freshness_days,
    CASE
        WHEN s.examined_date >= CURDATE() - INTERVAL 30 DAY THEN 'FRESH'
        WHEN s.examined_date >= CURDATE() - INTERVAL 1 YEAR THEN 'CAUTION'
        ELSE 'STALE'
    END AS freshness_status,
    CASE
        WHEN s.examined_date >= CURDATE() - INTERVAL 30 DAY THEN '최신'
        WHEN s.examined_date >= CURDATE() - INTERVAL 1 YEAR THEN '주의'
        ELSE '오래됨'
    END AS freshness_label,
    CASE WHEN s.examined_date >= CURDATE() - INTERVAL 1 YEAR THEN 1 ELSE 0 END AS is_analysis_ready,
    s.product_cls_code,
    s.product_cls_name,
    s.unit,
    s.unit_size,
    s.price,
    s.kg_price,
    s.day_before_price,
    s.day_before_kg_price,
    s.week_before_price,
    s.week_before_kg_price,
    s.month_before_price,
    s.month_before_kg_price,
    s.year_before_price,
    s.year_before_kg_price,
    s.source_name,
    s.collected_at
FROM RecentPriceSnapshot s
JOIN ProductVariant v ON v.variant_id = s.variant_id
JOIN Product p ON p.item_code = v.item_code
JOIN Category c ON c.category_code = p.category_code
JOIN Grade g ON g.grade_code = s.grade_code;
