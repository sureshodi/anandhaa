import streamlit as st
import pandas as pd

# Load CSV files
def load_stock_data(file):
    return pd.read_csv(file)

def load_sales_data(file):
    return pd.read_csv(file)

# Update stock and stock sold columns
def update_stock(stock_df, product_code, quantity):
    stock_df.loc[stock_df['Product Code'] == product_code, 'Stock Sold'] += quantity
    stock_df.loc[stock_df['Product Code'] == product_code, 'Stock Available per pcs'] -= quantity
    return stock_df

# Streamlit app
st.title("Crackers Business Bill Generation and Stock Tracking")

# Upload CSV files
stock_file = st.file_uploader("Upload Stock Tracking CSV", type="csv")
if stock_file is not None:
    stock_df = load_stock_data(stock_file)
    st.write("Stock Tracking Data:")
    st.dataframe(stock_df)

sales_file = st.file_uploader("Upload Sales Data CSV", type="csv")
if sales_file is not None:
    sales_df = load_sales_data(sales_file)
    st.write("Sales Data (Bill Generation):")
    st.dataframe(sales_df)

# Customer Details
customer_name = st.text_input("Enter Customer Name")
customer_mobile = st.text_input("Enter Customer Mobile")

# Product Code
product_code = st.text_input("Enter Product Code (e.g., SP10E)")

if product_code:
    product_data = stock_df[stock_df['Product Code'] == product_code]
    if not product_data.empty:
        product_name = product_data['Product Name'].values[0]
        per_case = product_data['Per Case'].values[0]
        rate_per_pcs = product_data['Rate'].values[0]
        st.write(f"Product: {product_name}")
        st.write(f"Per Case: {per_case}")
        st.write(f"Rate per Piece: ₹{rate_per_pcs}")
    else:
        st.error("Product Code not found")

if product_code and not product_data.empty:
    quantity = st.number_input("Enter Quantity", min_value=1, step=1)
    if quantity:
        amount = rate_per_pcs * quantity
        st.write(f"Amount: ₹{amount}")

if st.button("Generate Bill and Update Stock"):
    if product_code and customer_name and customer_mobile and quantity:
        updated_stock_df = update_stock(stock_df, product_code, quantity)
        st.write("Updated Stock Data:")
        st.dataframe(updated_stock_df)

        # Option to download the updated stock CSV
        csv = updated_stock_df.to_csv(index=False)
        st.download_button(
            label="Download Updated Stock CSV",
            data=csv,
            file_name='updated_stock.csv',
            mime='text/csv'
        )
    else:
        st.error("Please fill in all fields to generate the bill.")
