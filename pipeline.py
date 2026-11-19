# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
import json
import os
from urllib.parse import urljoin
import pandas as pd
import requests

BASE_URL = 'https://cvijan.github.io/nss-api/v1/'
RAW_DIR = 'data/raw'
PROCESSED_DIR = 'data/processed'

# COMMAND ----------

# Make sure both data folders exist; exist_ok=True means no error if a folder is already there.

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# COMMAND ----------

# 1. (5 поена) Позив API-ја. Написати функцију get_json(url: str) -> dict која шаље GET захтев.
# Подиже грешку ако статус није успешан и враћа одговор као речник ако јесте.
# get_json(BASE_URL + 'status.json')['service'] враћа 'Northern Star Shop API'
# get_json(BASE_URL + 'orders/page-99.json') подиже requests.HTTPError
import requests

def get_json(url: str) -> dict:
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

print(get_json(BASE_URL + 'status.json')['service'])
# print(get_json(BASE_URL + 'orders/page-99.json'))

# COMMAND ----------

# 2. (10 поена) Странице. Написати функцију fetch_all(first_url: str) -> list која прати
# next линкове и враћа записе са свих страна у једној листи
# Помоћ: next је релативна путања ('page-2.json')
# Пуну адресу добијамо са: urljoin(url, page['next']) (пазите када нема следеће
# стране)
# Input: BASE_URL + 'products/page-1.json' даје 48 производа
# Input: BASE_URL + 'orders/page-1.json' даје 125 поруџбина
from pprint import pprint

def fetch_all(first_url: str) -> list:
    lista = []
    for _ in range(1000):
        page = get_json(first_url)
        lista.extend(page['data'])
        if page.get('next') is None:
            break
        first_url = urljoin(first_url, page['next'])
    return lista
# pprint(fetch_all(BASE_URL + 'products/page-1.json'))
# len(fetch_all(BASE_URL + 'products/page-1.json'))
# pprint(fetch_all(BASE_URL + 'orders/page-1.json'))
len(fetch_all(BASE_URL + 'orders/page-1.json'))

# COMMAND ----------

# 3. (5 поена) Чување сирових података. Написати функцију save_raw(records: list, path: str) -> None која листу речника уписује у JSON фајл без икаквих измена.
# Ако нешто пође наопако у чишћењу података, сирови подаци остају сачувани онако какви су стигли.
# os.path.join(RAW_DIR, 'test.json') - Представља путању до новог фајла који желимо да буде направљен
# Input: save_raw([{'id': 1, 'city': 'Niš'}], os.path.join(RAW_DIR,
# 'test.json'))
# Output: Нема повратне информације, али у data/raw/test.json пише: "city":
# "Niš"
# Обрисати све направљене JSON фајлове након пробе! Служили су само за проверу.
def save_raw(records: list, path: str) -> None:
    with open(path, mode="w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

save_raw([{'id': 1, 'city': 'Niš'}], os.path.join(RAW_DIR, 'test.json'))

# COMMAND ----------

# 4. (5 поена) Extract. Написати функцију extract(raw_dir: str) -> tupleprodddd која преузима све
# потребне податке са API-ја (orders и products) и враћа их као два DataFrame-а
# Функцијом из задатка 2 преузети све поруџбине и све производе
# Функцијом из задатка 3 сачувати их као orders.json и products.json у RAW_DIR
# Угњеждена поља распаковати помоћу pd.json_nnormalize(..., sep='_')
# customer_name преименовати у customer
# customer_city преименовати у city
# Input: extract(RAW_DIR)
# Output: Два DataFrame-a (orders_df, products_df):
# Orders shape (125, 8)
# Products shape (48, 4)
# Поред њих, направљена су и два фајла у data/raw
def extract(raw_dir: str) -> tuple:
    orders = fetch_all((BASE_URL + 'orders/page-1.json'))
    products = fetch_all((BASE_URL + 'products/page-1.json'))

    save_raw(orders, os.path.join(RAW_DIR, 'orders.json'))
    save_raw(products, os.path.join(RAW_DIR, 'products.json'))

    orders_df = pd.json_normalize(orders, sep='_')
    products_df = pd.json_normalize(products, sep='_')

    orders_df = orders_df.rename(columns={
        'customer_name': 'customer',
        'customer_city': 'city'
    })

    return orders_df, products_df

# COMMAND ----------

# 5. (10 поена) Clean. Написати функцију clean_orders(df: pd.DataFrame) -> pd.DataFrame
# Колонама order_id, customer, city и payment уклонити почетне и крајње размаке
# order_id претворити у велика слова, customer и city у облик title()
# Где град недостаје, уписати 'Unknown'
# Не мењати оригиналан DataFrame
# Помоћ: df[col].str.strip(), .str.upper(), .str.title(), .fillna(...)
# Input (1 ред): {'order_id': 'NSS-0003', 'customer': 'MILICA PETROVIĆ',
# 'city': ' NIŠ '}
# Output: {'order_id': 'NSS-0003', 'customer': 'Milica Petrović', 'city':
# 'Niš'}
# У сировим подацима град има 30 различитих записа, после чишћења 9 (8 градова +
# 'Unknown')
def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ['order_id', 'customer', 'city', 'payment']:
        df[col] = df[col].str.strip()
    df['order_id'] = df['order_id'].str.upper()
    df['customer'] = df['customer'].str.title()
    df['city'] = df['city'].str.title()
    df['city'] = df['city'].fillna('Unknown')
    
    return df

# COMMAND ----------

# 6. (5 поена) Дупликати. Написати функцију remove_duplicates(df: pd.DataFrame) -> tuple
# Враћа торку (unique, duplicates) (Оба DataFrame)
# Поруџбина са истим order_id се задржава само први пут (све остало иде у
# duplicates)
# Помоћ: df.duplicated(...)
# Тестирањем над очишћеним поруџбинама: 122 јединствене и 3 дупликата
def remove_duplicates(df: pd.DataFrame) -> tuple:
    df = df.copy()
    maska_duplikata = df.duplicated(subset=['order_id'], keep='first')
    unique_df = df[~maska_duplikata].copy()
    duplicates_df = df[maska_duplikata].copy()

    return (unique_df, duplicates_df)

# COMMAND ----------

# 7. (15 поена) Validation. Написати функцију validate_order(row: dict, product_ids: set)
# -> str која враћа 'OK' за исправан ред, у супротном разлог
# Провере радити редом и вратити први пронађени проблем
# order_id не почиње са NSS- -> 'invalid_order'
# quantity недостаје -> 'missing_quantity'
# quantity није цео број већи од нуле -> 'invalid_quantity'
# unit_price није број већи од нуле -> 'invalid_price'
# product_id не постоји међу производима -> 'unknown_product'
# Помоћ:
# pd.to_numeric(value, errors='coerce') претвара '2' у 2, а 'abc' у NaN
# pd.isna(value) препознаје и None и NaN
def validate_order(row: dict, product_ids: set) -> str:
    if not row.get('order_id', '').startswith('NSS'):
        return 'invalid_order'
    
    if row.get('quantity') is None or str(row.get('quantity')).strip() == '':
        return 'missing_quantity'
    
    if not str(row.get('quantity')).isdigit() or int(row.get('quantity')) <= 0:
        return 'invalid_quantity'
    
    if not str(row.get('unit_price')).replace('.', '', 1).isdigit() or float(row.get('unit_price')) <= 0:
        return 'invalid_price'
    if row.get('product_id') not in product_ids:
        return 'unknown_product'
    
    return 'OK'


# COMMAND ----------

# 8. (10 поена) Transformation. Написати функцију transform_orders(orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame која прима исправне редове.
# Типови:
# quantity -> int
# unit_price -> float
# order_date -> датум (pd.to_datetime)
# Нова колона total (quantity * unit_price)
# Из products додати product_name (колона name) и category (merge по product_id)
# Output: Нпр за NSS-0001: quantity 2, unit_price 6090.0, total 12180.0,
# product_name 'NPM Kids Jersey', category 'jerseys'
def transform_orders(orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()

    # 1. Konverzija tipova
    df['quantity'] = df['quantity'].astype(int)
    df['unit_price'] = df['unit_price'].astype(float)
    df['order_date'] = pd.to_datetime(df['order_date'])

    # 2. Nova kolona total
    df['total'] = df['quantity'] * df['unit_price']

    # 3. Spajanje sa products (name -> product_name, category)
    prod = products[['product_id', 'name', 'category']].rename(
        columns={'name': 'product_name'}
    )
    df = df.merge(prod, on='product_id', how='left')

    return df


# COMMAND ----------

# 9. (10 поена) Раздвајање. Написати функцију split_orders(df: pd.DataFrame, products:pd.DataFrame) -> tuple која сирове поруџбине чисти, избацује дупликате, проверава и враћа торку (valid, rejected)
# valid су трансформисани исправни редови
# rejected су очишћени неисправни редови и дупликати, са колоном reason
# (дупликати за разлог треба да имају 'duplicate')
# Output: 107 елемената за валидне и 18 за одбијене
def split_orders(df: pd.DataFrame, products: pd.DataFrame) -> tuple:
    # 1. čišćenje
    df = clean_orders(df)

    # 2. duplikati (raspakuješ torku u dve tabele)
    unique_df, duplicates_df = remove_duplicates(df)

    # 3. validacija red po red
    product_ids = set(products['product_id'])
    reasons = []
    for row in unique_df.to_dict('records'):      # row je dict
        reasons.append(validate_order(row, product_ids))
    unique_df['reason'] = reasons                 # lista razloga, red po red

    # 4. razdvajanje na ispravne i neispravne
    ok = unique_df['reason'] == 'OK'
    valid_raw = unique_df[ok].drop(columns='reason')
    invalid_df = unique_df[~ok]

    # 5. transformacija samo ispravnih
    valid = transform_orders(valid_raw, products)

    # 6. rejected = neispravni + duplikati, svi sa kolonom reason
    duplicates_df = duplicates_df.copy()
    duplicates_df['reason'] = 'duplicate'
    rejected = pd.concat([invalid_df, duplicates_df], ignore_index=True)

    return valid, rejected

# COMMAND ----------

# 10. (10 поена) Агрегација. Написати функцију revenue_by(df: pd.DataFrame, column: str) -> pd.DataFrame која сабира total по вредностима задате колоне и враћа DataFrame са колонама [column, 'revenue'], сортиран од највећег промета.
# Input: valid, 'category'
# Output: jerseys 488290.0, balls 66470.0, caps 59940.0, scarves 38070.0, accessories
# 25130.0
def revenue_by(df: pd.DataFrame, column: str) -> pd.DataFrame:
    return (
        df.groupby(column, as_index=False)['total']
          .sum()
          .rename(columns={'total': 'revenue'})
          .sort_values('revenue', ascending=False)
          .reset_index(drop=True)
    )
df_raw, products = extract(RAW_DIR)
valid, rejected = split_orders(df_raw, products)
revenue_by(valid, 'category')

# COMMAND ----------

# 11. (10 поена) Load. Написати функцију load(valid: pd.DataFrame, rejected: pd.DataFrame, processed_dir: str) -> dict која у processed_dir уписује 4 CSV фајла и враћа број уписаних редова по фајлу.
# clean_orders.csv, rejected_orders.csv, revenue_by_city.csv, revenue_by_category.csv
# load(valid, rejected, PROCESSED_DIR) -> {'clean_orders.csv': 107, 'rejected_orders.csv': 18, 'revenue_by_city.csv': 9, 'revenue_by_category.csv': 5}
def load(valid: pd.DataFrame, rejected: pd.DataFrame, processed_dir: str) -> dict:
    os.makedirs(processed_dir, exist_ok=True)
    files = {
        'clean_orders.csv': valid,
        'rejected_orders.csv': rejected,
        'revenue_by_city.csv': revenue_by(valid, 'city'),
        'revenue_by_category.csv': revenue_by(valid, 'category'),
    }
    result = {}
    for name, frame in files.items():
        frame.to_csv(os.path.join(processed_dir, name), index=False)
        result[name] = len(frame)
    return result
load(valid, rejected, PROCESSED_DIR)

# COMMAND ----------

# 12. (5 поена) Run. Написати функцију run_pipeline(raw_dir: str, processed_dir: str) -> dict која покреће цео pipeline и враћа резиме.
# Резиме уписати и у summary.csv (у processed_dir), са заглављем metric, value
# Input: run_pipeline(RAW_DIR, PROCESSED_DIR)
# Output: {'total_rows': 125, 'duplicates': 3, 'valid_rows': 107, 'rejected_rows': 18, 'total_revenue': 677900.0}
import csv

def run_pipeline(raw_dir: str, processed_dir: str) -> dict:
    os.makedirs(processed_dir, exist_ok=True)
    orders_df, products_df = extract(raw_dir)

    valid_df, rejected_df = split_orders(orders_df, products_df)
    load(valid_df, rejected_df, processed_dir)

    summary = {
        "total_rows": len(orders_df),
        "duplicates": int((rejected_df["reason"] == "duplicate").sum()),
        "valid_rows": len(valid_df),
        "rejected_rows": len(rejected_df),
        "total_revenue": float(valid_df["total"].sum()),
    }

    with open(os.path.join(processed_dir, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for k, v in summary.items():
            writer.writerow([k, v])
    return summary

# COMMAND ----------

result = run_pipeline(RAW_DIR, PROCESSED_DIR)
print(result)