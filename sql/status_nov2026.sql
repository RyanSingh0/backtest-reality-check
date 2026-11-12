-- 11 Nov 2026: paper status after publication.
-- Risks paper published 23 Oct 2026 (Risks 14(11), 247); commodities paper submitted and under review at Commodities (MDPI).
UPDATE dim_study SET status = 'Published 23 Oct 2026, vol. 14(11), 247' WHERE short_name = 'DXY';
UPDATE dim_study SET status = 'Under review' WHERE journal LIKE 'Commodities%';
