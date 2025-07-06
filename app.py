import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os

# Load products from CSV
def load_products():
    df = pd.read_csv("stock_tracking.csv")
    # index by Product Code for fast lookup
    return df.set_index("Product Code").T.to_dict()

@st.cache_data


product_dict = load_products()

st.title("🎆 Anandhaa Crackers Wholesale Billing")

# Input form state\if "entries" not in st.session_state:
    st.session_state.entries = []

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
            per_case = prod['Per Case']
            rate     = prod['Rate']
            name     = prod['Product Name']
            amount   = rate * qty
            st.session_state.entries.append({
                "code": code,
                "name": name,
                "per_case": per_case,
                "qty": qty,
                "rate": rate,
                "amount": amount
            })

# Show bill items
if st.session_state.entries:
    st.subheader("🧾 Bill Items")
    df = pd.DataFrame(st.session_state.entries)
    # Add S.No column
    df.insert(0, "S.No", range(1, len(df) + 1))
    
    # Rename columns for display
    df = df.rename(columns={
        "code": "Product Code",
        "name": "Product Name",
        "per_case": "Per Case",
        "qty": "Qty",
        "rate": "Rate",
        "amount": "Amount"
    })

    # Display the table with renamed headers
    st.table(df[["S.No", "Product Code", "Product Name", "Per Case", "Qty", "Rate", "Amount"]])

    # Calculate total
    total_amt = df["Amount"].sum()
    st.markdown(f"### ✅ Total: ₹{total_amt}")

    # Generate bill files
    if st.button("Generate Bill"):
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_file = f"bill_{ts}.txt"
        pdf_file = f"bill_{ts}.pdf"

        # Write text bill
        with open(txt_file, "w") as f:
            f.write("==== Wholesale Crackers Bill ====" + "\n")
            for e in st.session_state.entries:
                f.write(f"{e['S.No']} - {e['code']} - {e['name']} - Per Case: {e['per_case']} - ₹{e['rate']} x {e['qty']} = ₹{e['amount']}\n")
            f.write(f"\nTOTAL: ₹{total_amt}\n")

        # Create PDF bill
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Wholesale Crackers Bill", ln=True, align='C')
        for e in st.session_state.entries:
            line = (f"{e['S.No']} - {e['code']} - {e['name']} - Per Case: {e['per_case']} - "
                    f"₹{e['rate']} x {e['qty']} = ₹{e['amount']}")
            pdf.cell(200, 10, txt=line, ln=True)
        pdf.cell(200, 10, txt=f"TOTAL: ₹{total_amt}", ln=True)
        pdf.output(pdf_file)

        # Provide downloads
        with open(txt_file, "rb") as f:
            st.download_button("⬇️ Download Text Bill", f, txt_file)
        with open(pdf_file, "rb") as f:
            st.download_button("⬇️ Download PDF Bill", f, pdf_file)

        # Clear entries after generating
        st.session_state.entries = []
else:
    st.info("Add products to begin billing.")
