-- 小売物価統計調査 - 10大費目別消費者物価地域差指数（全国平均＝100）
-- 統計表ID: 0003441258

with source as (
    select * from {{ source('estat', '0003441258') }}
)

select
    "10大費目_code" as expense_category_code,
    "10大費目" as expense_category_name,
    "地域_code" as area_code,
    "地域" as area_name,
    cast(left("時間軸(年)_code", 4) as integer) as year,
    try_cast(value as double) as price_index
from source
