-- 都道府県別の消費者物価地域差指数（全国平均＝100）
-- 地方・都市の行は除き、全国と47都道府県に絞る

with stg as (
    select * from {{ ref('stg_regional_price_index') }}
)

select
    year,
    area_code,
    area_name,
    expense_category_code,
    expense_category_name,
    price_index
from stg
where price_index is not null
  and (
      area_code = '00000'
      or (area_code like '%000' and cast(left(area_code, 2) as integer) between 1 and 47)
  )
