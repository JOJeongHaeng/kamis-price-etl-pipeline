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

CREATE TABLE IF NOT EXISTS DailyPrice (
    daily_price_id BIGINT AUTO_INCREMENT NOT NULL,
    product_no VARCHAR(30) NOT NULL,
    price_date DATE NOT NULL,
    product_cls_code CHAR(2) NOT NULL,
    product_cls_name VARCHAR(20) NOT NULL,
    category_code VARCHAR(20) NULL,
    category_name VARCHAR(50) NULL,
    variety_code VARCHAR(20) NOT NULL,
    variety_name VARCHAR(100) NULL,
    grade_code VARCHAR(20) NOT NULL,
    grade_name VARCHAR(50) NULL,
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
    item_id INTEGER NOT NULL,
    PRIMARY KEY (daily_price_id),
    UNIQUE KEY uq_dailyprice_identity (
        product_no, variety_code, grade_code, price_date,
        product_cls_code, unit, unit_size
    ),
    CONSTRAINT fk_dailyprice_item FOREIGN KEY (item_id) REFERENCES Item (item_id)
        ON DELETE NO ACTION
        ON UPDATE NO ACTION
);
