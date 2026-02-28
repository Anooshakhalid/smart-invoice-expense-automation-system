import json
import os
from collections import defaultdict
from utils import DB_PATH

class ReportService:

    def __init__(self):
        self.db_path = DB_PATH

    def load_data(self):
        if not os.path.exists(self.db_path):
            return []
        with open(self.db_path, "r") as f:
            data = json.load(f)
        return data.get("invoices", [])

    # -------------------------
    # CORE METRICS
    # -------------------------

    def total_revenue(self):
        invoices = self.load_data()
        return sum(inv["total_amount"] for inv in invoices)

    def total_invoices(self):
        return len(self.load_data())

    def revenue_by_vendor(self):
        invoices = self.load_data()
        vendor_totals = defaultdict(float)

        for inv in invoices:
            vendor_totals[inv["vendor"]] += inv["total_amount"]

        return dict(vendor_totals)

    def revenue_by_category(self):
        invoices = self.load_data()
        category_totals = defaultdict(float)

        for inv in invoices:
            for item in inv["items"]:
                category_totals[item["category"]] += item["price"]

        return dict(category_totals)

    # Easy to add new reports later
    def invoices_by_year(self):
        invoices = self.load_data()
        year_count = defaultdict(int)

        for inv in invoices:
            year = inv["date"].split("/")[-1]
            year_count[year] += 1

        return dict(year_count)