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
