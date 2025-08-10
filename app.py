import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os
from typing import Optional

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
    # Expected columns:
    # Product Code, Product Name, Per Case, Rate, [optional: Image or Image Path]
    df = pd.read_csv("stock_tracking.csv")
    # Normalize possible image column names
    img_col = None
    for c in df.columns:
        if c.strip().lower() in {"image", "image path", "image_path", "img"}:
            img_col = c
            break
    if img_col is None:
        df["__image__"] = ""
        img_col = "__image__"
    # Build dict keyed by Product Code
    d = {}
    for _, r in df.iterrows():
        code = str(r["Product Code"]).strip().upper()
        d[code] = {
            "Product Code": code,
            "Product Name": str(r.get("Product Name", "")).strip(),
            "Per Case": r.get("Per Case", ""),
            "Rate": float(r.get("Rate", 0)),
            "Image": str(r.get(img_col, "")).strip()
        }
    return d

product_dict = load_products()

def find_image_for_code(code: str) -> Optional[str]:
    """Return a local image path if available for the product code."""
    if not code:
        return None
    info = product_dict.get(code)
    if info:
        # If CSV carries an image path and it exists
        csv_path = info.get("Image")
        if csv_path and os.path.exists(csv_path):
            return csv_path
    # Fallback: look into ./product_images/<CODE>.<ext>
    folder = "product_images"
    exts = ("png", "jpg", "jpeg", "webp")
    for ext in exts:
        cand = os.path.join(folder, f"{code}.{ext}")
        if os.path.exists(cand):
            return cand
    return None

# --- Initialize order entries ---
if "entries" not in st.session_state:
    st.session_state.entries = []

# --- Add Order Items Form ---
with st.form("add_form"):
    st.subheader("Add Order Items")

    # Dropdown for codes (searchable)
    codes = sorted(product_dict.keys())
    # Show richer label: CODE — Name — Rate
    display_labels = [
        f"{c} — {product_dict[c]['Product Name']} — Rs.{product_dict[c]['Rate']:.2f}"
        for c in codes
    ]
    # Keep a stable index map
    label_to_code = {label: code for label, code in zip(display_labels, codes)}

    col1, col2 = st.columns([2,1])
    chosen_label = col1.selectbox("Product Code", options=display_labels, index=None, placeholder="Select a product code")
    qty_input = col2.number_input("Quantity", min_value=1, step=1)

    # Preview image for the selected code
    if chosen_label:
        code_selected = label_to_code[chosen_label]
        img_path = find_image_for_code(code_selected)
        if img_path:
            st.caption(f"Sample image for {code_selected}")
            st.image(img_path, width=240)
        else:
            st.info("No sample image found for this code. (Add an 'Image' column in CSV or place a file in product_images/ as CODE.png/jpg)")

    submitted_item = st.form_submit_button("Add Item")
    if submitted_item:
        if not chosen_label:
            st.error("⚠️ Please select a product code.")
        else:
            code_input = label_to_code[chosen_label]
            prod = product_dict.get(code_input)
            if not prod:
                st.error(f"⚠️ Unknown product code: {code_input}")
            else:
                st.session_state.entries.append({
                    "Product Code": code_input,
                    "Product Name": prod["Product Name"],
                    "Per Case": prod["Per Case"],
                    "Qty": int(qty_input),
                    "Rate": float(prod["Rate"]),
                    "Amount": float(prod["Rate"]) * int(qty_input)
                })
                st.success(f"Added {code_input} — {prod['Product Name']} (Qty {qty_input})")

# --- Display Order Table and Summary ---
if st.session_state.entries:
    st.subheader("Order Details")
    df = pd.DataFrame(st.session_state.entries)
    df.insert(0, "S.No", range(1, len(df) + 1))
    display_df = df[["S.No","Product Code","Product Name","Per Case","Qty","Rate","Amount"]]
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    # --- Delete item control (by S.No)
    del_col1, del_col2 = st.columns([2,1])
    if len(display_df) > 0:
        s_no_to_delete = del_col1.selectbox(
            "Remove an item (S.No)",
            options=display_df["S.No"].tolist(),
            index=None,
            placeholder="Select S.No to delete"
        )
        if del_col2.button("Delete item", use_container_width=True, type="primary", disabled=(s_no_to_delete is None)):
            idx = int(s_no_to_delete) - 1
            if 0 <= idx < len(st.session_state.entries):
                removed = st.session_state.entries.pop(idx)
                st.success(f"Removed {removed['Product Code']} — {removed['Product Name']}")
                st.rerun()

    # Calculate totals
    sub_total = float(df["Amount"].sum())
    discount = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, step=1.0)
    total = sub_total * (1 - discount/100)
    st.markdown(f"**Sub Total:** Rs. {sub_total:.2f}")
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
            f.write(f"\nSub Total: Rs. {sub_total:.2f}\n")
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
        for w, h in zip(col_w, headers):
            pdf.cell(w,7,h,1,0,'C')
        pdf.ln()

        # Table rows
        pdf.set_font("Arial",size=10)
        for _, row in df.iterrows():
            pdf.cell(col_w[0],6,str(row['S.No']),1)
            pdf.cell(col_w[1],6,row['Product Code'],1)
            # Truncate long names for PDF cell
            name = row['Product Name']
            if len(name) > 28:
                name = name[:27] + "…"
            pdf.cell(col_w[2],6,name,1)
            pdf.cell(col_w[3],6,str(row['Per Case']),1,0,'R')
            pdf.cell(col_w[4],6,str(row['Qty']),1,0,'R')
            pdf.cell(col_w[5],6,f"{row['Rate']:.2f}",1,0,'R')
            pdf.cell(col_w[6],6,f"{row['Amount']:.2f}",1,0,'R')
            pdf.ln()

        # Summary under Rate column
        pdf.ln(2)
        for w in col_w[:5]: pdf.cell(w,6,'',0)
        pdf.cell(col_w[5],6,"Sub Total",1,0,'R')
        pdf.cell(col_w[6],6,f"Rs. {sub_total:.2f}",1,1,'R')

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
