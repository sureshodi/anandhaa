import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os

# Cache and load products
@st.cache_data
def load_products():
    df = pd.read_csv("stock_tracking.csv")
    return df.set_index("Product Code").T.to_dict()

# Initialize product dictionary
product_dict = load_products()

st.title("🎆 Anandhaa Crackers Wholesale Billing")

# Initialize session state for entries
if "entries" not in st.session_state:
    st.session_state.entries = []

# Input form to add items
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

    # Select and display columns without default index
    display_df = df[["S.No", "Product Code", "Product Name", "Per Case", "Qty", "Rate", "Amount"]]
    st.table(display_df.style.hide_index())

    # Summary calculations
    sub_total = df["Amount"].sum()
    discount = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, step=1.0)
    total = sub_total * (1 - discount / 100)

    st.markdown(f"**Sub Total:** ₹{sub_total}")
    st.markdown(f"**Discount:** {discount}%")
    st.markdown(f"**Total:** ₹{total:.2f}")

    # Generate and download bill files
    if st.button("Generate Bill"):
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_file = f"bill_{ts}.txt"
        pdf_file = f"bill_{ts}.pdf"

        # Write text bill
        with open(txt_file, "w") as f:
            f.write("Wholesale Crackers Bill\n")
            f.write("=======================\n")
            for _, row in df.iterrows():
                f.write(
                    f"{row['S.No']} {row['Product Code']} {row['Product Name']} "
                    f"Per Case: {row['Per Case']} ₹{row['Rate']} x {row['Qty']} = ₹{row['Amount']}\n"
                )
            f.write(f"\nSub Total: ₹{sub_total}\n")
            f.write(f"Discount: {discount}%\n")
            f.write(f"Total: ₹{total:.2f}\n")

        # Create PDF bill
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
        pdf.cell(200, 10, txt=f"Sub Total: ₹{sub_total}", ln=True)
        pdf.cell(200, 10, txt=f"Discount: {discount}%", ln=True)
        pdf.cell(200, 10, txt=f"Total: ₹{total:.2f}", ln=True)
        pdf.output(pdf_file)

        # Download buttons
        with open(txt_file, "rb") as tf:
            st.download_button("⬇️ Download Text Bill", tf, txt_file)
        with open(pdf_file, "rb") as pf:
            st.download_button("⬇️ Download PDF Bill", pf, pdf_file)

        # Clear session entries
        st.session_state.entries = []
else:
    st.info("Add products to begin billing.")
