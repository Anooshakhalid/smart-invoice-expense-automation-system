import streamlit as st
import time
from report_service import ReportService

st.set_page_config(layout="wide")
st.title("📊 Invoice Real-Time Reporting Dashboard")

service = ReportService()

# Auto refresh every 5 seconds
st_autorefresh = st.empty()
time.sleep(1)

# Load fresh data every run
total_revenue = service.total_revenue()
total_invoices = service.total_invoices()
vendor_data = service.revenue_by_vendor()
category_data = service.revenue_by_category()
year_data = service.invoices_by_year()

# -------------------------
# TOP METRICS
# -------------------------
col1, col2 = st.columns(2)
col1.metric("Total Revenue", f"${total_revenue:,.2f}")
col2.metric("Total Invoices", total_invoices)

# -------------------------
# CATEGORY REPORT
# -------------------------
st.subheader("Revenue by Category")
st.bar_chart(category_data)

# -------------------------
# VENDOR REPORT
# -------------------------
st.subheader("Revenue by Vendor")
st.bar_chart(vendor_data)

# -------------------------
# YEAR REPORT
# -------------------------
st.subheader("Invoices by Year")
st.bar_chart(year_data)

# Refresh every 5 seconds
time.sleep(5)
st.rerun()