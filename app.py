import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os

# --- Shop Header Image ---
HEADER_IMG = "header.png"
if os.path.exists(HEADER_IMG):
    st.image(HEADER_IMG, use_container_width=True)
else:
    st.title("🎆 Anandhaa Crackers Wholesale Billing 🎆")

# --- Customer Details Inputs ---
st.subheader("Customer Details")
customer_name = st.text_input("Customer Name")
customer_mobile = st.text_input("Customer Mobile")
customer_address = st.text_area("Customer Address")

# --- Load Products CSV ---
@st.cache_data
def load_products():
    df = pd.read_csv("stock_tracking.csv")
    return df.set_index("Product Code").T.to_dict()
product_dict = load_products()

# --- Initialize order entries ---
if "entries" not in st.session_state:
    st.session_state.entries = []

# --- Add Order Items Form ---
with st.form("add_form"):
    st.subheader("Add Order Items")
    col1, col2 = st.columns(2)
    code_input = col1.text_input("Product Code").strip().upper()
    qty_input = col2.number_input("Quantity", min_value=1, step=1)
    submitted_item = st.form_submit_button("Add Item")
    if submitted_item:
        if code_input not in product_dict:
            st.error(f"⚠️ Unknown product code: {code_input}")
        else:
            prod = product_dict[code_input]
            st.session_state.entries.append({
                "Product Code": code_input,
                "Product Name": prod["Product Name"],
                "Per Case": prod["Per Case"],
                "Qty": qty_input,
                "Rate": prod["Rate"],
                "Amount": prod["Rate"] * qty_input
            })

# --- Display Order Table and Summary ---
if st.session_state.entries:
    st.subheader("Order Details")
    df = pd.DataFrame(st.session_state.entries)
    df.insert(0, "S.No", range(1, len(df) + 1))
    display_df = df[["S.No","Product Code","Product Name","Per Case","Qty","Rate","Amount"]]
    st.dataframe(display_df, hide_index=True)

    # Calculate totals
    sub_total = df["Amount"].sum()
    discount = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, step=1.0)
    total = sub_total * (1 - discount/100)
    st.markdown(f"**Sub Total:** Rs. {sub_total}")
    st.markdown(f"**Discount:** {discount}%")
    st.markdown(f"**Total:** Rs. {total:.2f}")

    # --- Generate Bill TXT & PDF ---
    if st.button("Generate Bill"):
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_file = f"bill_{ts}.txt"
        pdf_file = f"bill_{ts}.pdf"

        # Write text bill
        with open(txt_file, "w", encoding="utf-8") as f:
            if os.path.exists(HEADER_IMG):
                f.write(f"[Header Image: {HEADER_IMG}]\n")
            f.write("SALES ORDER\n=======================\n")
            f.write(f"Customer: {customer_name} | {customer_mobile}\n")
            f.write(f"Address: {customer_address}\n\n")
            for _, row in df.iterrows():
                f.write(
                    f"{row['S.No']} {row['Product Code']} {row['Product Name']} "
                    f"Per Case: {row['Per Case']} Rs. {row['Rate']} x {row['Qty']} = Rs. {row['Amount']}\n"
                )
            f.write(f"\nSub Total: Rs. {sub_total}\n")
            f.write(f"Discount: {discount}%\n")
            f.write(f"Total: Rs. {total:.2f}\n")

        # Create PDF bill
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()

        # Header image placement
        if os.path.exists(HEADER_IMG):
            avail_w = pdf.w - 20
            header_h = 40
            y_start = pdf.get_y()
            pdf.image(HEADER_IMG, x=10, y=y_start, w=avail_w, h=header_h)
            pdf.ln(header_h + 5)
        else:
            pdf.ln(15)

        # Title below header
        pdf.set_font("Arial","B",14)
        pdf.cell(0,10,"SALES ORDER", ln=True, align='C')
        pdf.ln(3)

        # Customer info below title
        pdf.set_font("Arial",size=10)
        pdf.cell(0,6,f"Customer: {customer_name} | {customer_mobile}", ln=True)
        pdf.multi_cell(0,6, f"Address: {customer_address}")
        pdf.ln(5)

        # Table header
        pdf.set_font("Arial","B",10)
        col_w = [12,30,60,25,15,20,25]
        headers = ["S.No","Code","Name","Per Case","Qty","Rate","Amount"]
        for w, h in zip(col_w, headers): pdf.cell(w,7,h,1,0,'C')
        pdf.ln()

        # Table rows
        pdf.set_font("Arial",size=10)
        for _, row in df.iterrows():
            pdf.cell(col_w[0],6,str(row['S.No']),1)
            pdf.cell(col_w[1],6,row['Product Code'],1)
            pdf.cell(col_w[2],6,row['Product Name'],1)
            pdf.cell(col_w[3],6,str(row['Per Case']),1,0,'R')
            pdf.cell(col_w[4],6,str(row['Qty']),1,0,'R')
            pdf.cell(col_w[5],6,str(row['Rate']),1,0,'R')
            pdf.cell(col_w[6],6,str(row['Amount']),1,0,'R')
            pdf.ln()

        # Summary under Rate column
        pdf.ln(2)
        for w in col_w[:5]: pdf.cell(w,6,'',0)
        pdf.cell(col_w[5],6,"Sub Total",1,0,'R')
        pdf.cell(col_w[6],6,f"Rs. {sub_total}",1,1,'R')

        for w in col_w[:5]: pdf.cell(w,6,'',0)
        pdf.cell(col_w[5],6,"Discount",1,0,'R')
        pdf.cell(col_w[6],6,f"{discount}%",1,1,'R')

        for w in col_w[:5]: pdf.cell(w,6,'',0)
        pdf.cell(col_w[5],6,"Total",1,0,'R')
        pdf.cell(col_w[6],6,f"Rs. {total:.2f}",1,1,'R')

        # Output files
        pdf.output(pdf_file)
        with open(txt_file,'rb') as tf:
            st.download_button("⬇️ Download Text Bill", tf, txt_file)
        with open(pdf_file,'rb') as pf:
            st.download_button("⬇️ Download PDF Bill", pf, pdf_file)

        st.success(f"Invoice generated: {txt_file}, {pdf_file}")
        st.session_state.entries = []
else:
    st.info("Add at least one item to generate a bill.")
