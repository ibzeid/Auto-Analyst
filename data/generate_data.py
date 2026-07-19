import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

STORES = ["Downtown Hub", "Marina Express", "JLT QuickStop", "Palm Satellite", "Deira Depot"]
CATEGORIES = {
    "Dairy": ["Fresh Milk 1L", "Greek Yogurt 500g", "Labneh 400g", "Butter 200g", "Cheddar Cheese 200g"],
    "Beverages": ["Cola 1.5L", "Sparkling Water 1L", "Orange Juice 1L", "Energy Drink 250ml", "Iced Tea 500ml"],
    "Snacks": ["Chips Salted 150g", "Chocolate Bar 100g", "Mixed Nuts 200g", "Granola Bar 50g", "Popcorn 100g"],
    "Household": ["Toilet Paper 4pk", "Paper Towels 2pk", "Dish Soap 500ml", "Laundry Detergent 1L", "Trash Bags 30pk"],
    "Pharmacy": ["Paracetamol 20pk", "Multivitamins 30pk", "Hand Sanitizer 200ml", "Face Masks 50pk", "First Aid Kit"],
}
NUM_DAYS = 180


def generate_data():
    rows = []
    start_date = datetime(2025, 10, 1)

    for store in STORES:
        for category, skus in CATEGORIES.items():
            base_demand = {
                "Dairy": 80, "Beverages": 60, "Snacks": 50,
                "Household": 30, "Pharmacy": 15
            }[category]
            category_volatility = {
                "Dairy": 0.15, "Beverages": 0.20, "Snacks": 0.25,
                "Household": 0.10, "Pharmacy": 0.08
            }[category]
            store_multiplier = {
                "Downtown Hub": 1.4, "Marina Express": 1.2,
                "JLT QuickStop": 1.0, "Palm Satellite": 0.8, "Deira Depot": 1.1
            }[store]

            for sku in skus:
                base = base_demand * store_multiplier * np.random.uniform(0.7, 1.3)

                for day_offset in range(NUM_DAYS):
                    date = start_date + timedelta(days=day_offset)
                    dow = date.weekday()

                    weekend_lift = 1.25 if dow >= 5 else 1.0
                    promo = np.random.rand() < 0.08
                    promo_lift = np.random.uniform(1.3, 1.8) if promo else 1.0
                    weekly_pattern = 1 + 0.1 * np.sin(2 * np.pi * day_offset / 7)
                    trend = 1 + 0.0003 * day_offset
                    noise = np.random.normal(1, category_volatility)

                    demand = base * weekend_lift * promo_lift * weekly_pattern * trend * noise
                    demand = max(0, int(round(demand)))

                    price_base = {
                        "Fresh Milk 1L": 5.0, "Greek Yogurt 500g": 8.0,
                        "Labneh 400g": 7.0, "Butter 200g": 6.0, "Cheddar Cheese 200g": 10.0,
                        "Cola 1.5L": 4.0, "Sparkling Water 1L": 3.0,
                        "Orange Juice 1L": 6.0, "Energy Drink 250ml": 5.0,
                        "Iced Tea 500ml": 4.5,
                        "Chips Salted 150g": 3.5, "Chocolate Bar 100g": 5.0,
                        "Mixed Nuts 200g": 12.0, "Granola Bar 50g": 3.0, "Popcorn 100g": 4.0,
                        "Toilet Paper 4pk": 15.0, "Paper Towels 2pk": 12.0,
                        "Dish Soap 500ml": 8.0, "Laundry Detergent 1L": 18.0,
                        "Trash Bags 30pk": 10.0,
                        "Paracetamol 20pk": 6.0, "Multivitamins 30pk": 35.0,
                        "Hand Sanitizer 200ml": 9.0, "Face Masks 50pk": 12.0,
                        "First Aid Kit": 25.0
                    }
                    unit_cost = price_base.get(sku, 5.0) * 0.55
                    price = price_base.get(sku, 5.0) * (0.8 if promo else 1.0)

                    stockout = np.random.rand() < 0.03

                    rows.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "store": store,
                        "store_id": store[:3].upper(),
                        "category": category,
                        "sku": sku,
                        "units_sold": demand,
                        "price": round(price, 2),
                        "unit_cost": round(unit_cost, 2),
                        "revenue": round(demand * price, 2),
                        "cost": round(demand * unit_cost, 2),
                        "promotion": promo,
                        "stockout": stockout,
                        "day_of_week": dow,
                        "is_weekend": dow >= 5,
                    })

    df_ = pd.DataFrame(rows)
    df_ = df_.sort_values(["store", "sku", "date"]).reset_index(drop=True)
    return df_


if __name__ == "__main__":
    df = generate_data()
    path = "data/sample_grocery_data.csv"
    df.to_csv(path, index=False)
    print(f"Generated {len(df):,} rows → {path}")
    print(f"Stores: {df['store'].nunique()}, SKUs: {df['sku'].nunique()}, Days: {df['date'].nunique()}")
