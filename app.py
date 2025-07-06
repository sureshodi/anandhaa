import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os

# Cache and load products from CSV
@st.cache_data
def load_products():
    df = pd.read_csv("stock_tracking.csv")
    # Index by Product Code for quick lookups
    return df.set_index("Product Code").T.to_dict()

# Initialize product dictionary
product_dict = load_products()

st.title("🎆 Anandhaa Crackers Wholesale Billing")

# Initialize session state for entries
if "entries" not in st.session_state:
    st.session_state.entries = []

# Entry form
with st.form("add_form"):
    col1, col2 = st.columns(2)
    code = col1.text_input("Enter Product Code").strip().upper()
    qty = col2.number_input("Enter Quantity", min_value=1, step=1)

    submitted = st.form_submit_button("Add Item")
    if submitted:
        if code not in product_dict:
            st.error(f"❌ Product code '{code}' not found.")
        else:
            prod = product_dict[code]
            st.session_state.entries.append({
                "Product Code": code,
                "Product Name": prod['Product Name'],
                "Per Case": prod['Per Case'],
                "Qty": qty,
                "Rate": prod['Rate'],
                "Amount": prod['Rate'] * qty
            })

# Display bill items
if st.session_state.entries:
    st.subheader("🧾 Bill Items")
    df = pd.DataFrame(st.session_state.entries)
    df.insert(0, "S.No", range(1, len(df) + 1))

    # Display the formatted table
    st.table(df[["S.No", "Product Code", "Product Name", "Per Case", "Qty", "Rate", "Amount"]])

    # Calculate and display total
    total_amt = df["Amount"].sum()
    st.markdown(f"### ✅ Total: ₹{total_amt}")

    # Generate bill files
    if st.button("Generate Bill"):
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_file = f"bill_{timestamp}.txt"
        pdf_file = f"bill_{timestamp}.pdf"

        # Write text bill
        with open(txt_file, "w") as f:
            f.write("Wholesale Crackers Bill\n=======================\n")
            for _, row in df.iterrows():
                f.write(
                    f"{row['S.No']} {row['Product Code']} {row['Product Name']} "
                    f"Per Case: {row['Per Case']} ₹{row['Rate']} x {row['Qty']} = ₹{row['Amount']}\n"
                )
            f.write(f"\nTOTAL: ₹{total_amt}\n")

        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Wholesale Crackers Bill", ln=True, align='C')
        for _, row in df.iterrows():
            line = (
                f"{row['S.No']} {row['Product Code']} {row['Product Name']} "
                f"Per Case: {row['Per Case']} ₹{row['Rate']} x {row['Qty']} = ₹{row['Amount']}"
            )
            pdf.cell(200, 10, txt=line, ln=True)
        pdf.cell(200, 10, txt=f"TOTAL: ₹{total_amt}", ln=True)
        pdf.output(pdf_file)

        # Download buttons
        with open(txt_file, "rb") as tf:
            st.download_button("⬇️ Download Text Bill", tf, txt_file)
        with open(pdf_file, "rb") as pf:
            st.download_button("⬇️ Download PDF Bill", pf, pdf_file)

        # Clear entries after download
        st.session_state.entries = []
else:
    st.info("Add products to begin billing.")
