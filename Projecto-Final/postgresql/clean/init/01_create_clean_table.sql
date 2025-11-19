CREATE TABLE IF NOT EXISTS public.real_estate_clean (
    id              BIGSERIAL PRIMARY KEY,
    batch_id        BIGINT       NOT NULL,
    group_number    INTEGER      NOT NULL,
    day             TEXT         NOT NULL,
    batch_number    INTEGER      NOT NULL,
    brokered_by     BIGINT,
    status          TEXT         NOT NULL,
    price           NUMERIC(12,2) NOT NULL,
    bed             INTEGER      NOT NULL,
    bath            INTEGER      NOT NULL,
    acre_lot        NUMERIC(10,4),
    street          BIGINT,
    city            TEXT,
    state           TEXT,
    zip_code        TEXT,
    house_size      INTEGER,
    prev_sold_date  DATE,
    -- nuevas variables para trainng
    price_per_sqft  NUMERIC(12,4),
    price_per_bed   NUMERIC(12,4),
    price_per_acre  NUMERIC(12,4),
	
    ingestion_ts    TIMESTAMPTZ  NOT NULL,
    processed_ts    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_real_estate_clean_batch
    ON public.real_estate_clean (batch_id);

CREATE INDEX IF NOT EXISTS idx_real_estate_clean_city_state
    ON public.real_estate_clean (city, state);
