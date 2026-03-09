-- IP Reputation SQL Migration
-- Quick-20: Redis-only mimarisinden SQL+Redis cache mimarisine gecis
-- Kullanim: mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios < 20_ip_reputation_tables.sql

CREATE TABLE IF NOT EXISTS ip_reputation_checks (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    ip_address    VARCHAR(45)  NOT NULL,
    abuse_score   INT          DEFAULT 0,
    total_reports INT          DEFAULT 0,
    country       VARCHAR(100) DEFAULT NULL,
    country_code  VARCHAR(10)  DEFAULT NULL,
    city          VARCHAR(100) DEFAULT NULL,
    isp           VARCHAR(200) DEFAULT NULL,
    org           VARCHAR(200) DEFAULT NULL,
    checked_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_irc_ip         (ip_address),
    INDEX        idx_irc_score      (abuse_score),
    INDEX        idx_irc_checked_at (checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ip_blacklist_entries (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    ip_address       VARCHAR(45) NOT NULL,
    abuse_score      INT         DEFAULT 0,
    country          VARCHAR(10) DEFAULT NULL,
    last_reported_at VARCHAR(50) DEFAULT NULL,
    fetched_at       DATETIME    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_ibe_ip      (ip_address),
    INDEX        idx_ibe_score   (abuse_score),
    INDEX        idx_ibe_fetched (fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
