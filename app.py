import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os
import unicodedata
from pathlib import Path

# --- Shop Header Image ---
HEADER_IMG = "header.png"
if os.path.exists(HEADER_IMG):
    st.image(HEADER_IMG, use_container_width=True)
else:
    # Avoid emojis here just to keep everything simple
    st.title("Anandhaa Crackers Wholesale Billing")

# --- Customer Details Inputs ---
st.subheader("Customer Details")
customer_name = st.text_input("Customer Name")
customer_mobile = st.text_input("Customer Mobile")
customer_address = st.text_area("Customer Address")

# --- Load Products CSV ---
@st.cache_data
def load_products():
    # Expected columns: Product Code, Product Name, Per Case, Rate
    df = pd.read_csv("stock_tracking.csv")
    d = {}
    for _, r in df.iterrows():
        code = str(r["Product Code"]).strip().upper()
        d[code] = {
            "Product Code": code,
            "Product Name": str(r.get("Product Name", "")).strip(),
            "Per Case": r.get("Per Case", ""),
            "Rate": float(r.get("Rate", 0)),
        }
    return d

product_dict = load_products()

# --- Initialize order entries ---
if "entries" not in st.session_state:
    st.session_state.entries = []

# -------------------- PDF Unicode helpers --------------------
def find_font_file() -> str | None:
    """
    Try to locate a TTF that supports broad Unicode.
    Add your own font file to ./fonts if needed (e.g., NotoSansTamil-Regular.ttf).
    """
    candidates = [
        # Local project
        "fonts/NotoSansTamil-Regular.ttf",
        "fonts/NotoSans-Regular.ttf",
        "fonts/DejaVuSans.ttf",
        "NotoSansTamil-Regular.ttf",
        "NotoSans-Regular.ttf",
        "DejaVuSans.ttf",
        # System common paths
        "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/NotoSansTamil-Regular.ttf",
        "/usr/local/share/fonts/NotoSans-Regular.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def ascii_safe(text: str) -> str:
    """Strip/replace to ASCII so fpdf 1.x won't crash when no Unicode font is available."""
    if text is None:
        return ""
    # Normalize then encode to ASCII, dropping accents & unsupported chars
    t = unicodedata.normalize("NFKD", str(text))
    t = t.replace("…", "...").replace("−", "-").replace("—", "-").replace("–", "-")
    return t.encode("ascii", "ignore").decode("ascii")

class PDF(FPDF):
    """FPDF with optional Unicode TrueType font if found."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unicode_font_loaded = False
        self.font_name = "Arial"  # default
        font_path = find_font_file()
        if font_path:
            try:
                # Register as 'Universal'
                self.add_font("Universal", "", font_path, uni=True)
                self.font_name = "Universal"
                self.unicode_font_loaded = True
            except Exception:
                # If registration fails, we'll fall back to ASCII-sanitized text
                self.unicode_font_loaded = False

    def safe_cell(self, w, h=0, txt="", border=0, ln=0, align="", fill=False, link=""):
        if not self.unicode_font_loaded:
            txt = ascii_safe(txt)
        super().cell(w, h, txt, border, ln, align, fill, link)

    def safe_multi_cell(self, w, h, txt="", border=0, align="J", fill=False):
        if not self.unicode_font_loaded:
            txt = ascii_safe(txt)
        super().multi_cell(w, h, txt, border, align, fill)

# -------------------- Add Order Items Form --------------------
with st.form("add_form"):
    st.subheader("Add Order Items")

    codes = sorted(product_dict.keys())
    # Searchable label
    labels = [f"{c} — {product_dict[c]['Product Name']} — Rs.{product_dict[c]['Rate']:.2f}" for c in codes]
    label_to_code = {label: code for label, code in zip(labels, codes)}

    col1, col2 = st.columns([2,1])
    chosen_label = col1.selectbox("Product Code", options=labels, index=None, placeholder="Select a product code")
    qty_input = col2.number_input("Quantity", min_value=1, step=1)

    submitted_item = st.form_submit_button("Add Item")
    if submitted_item:
        if not chosen_label:
            st.error("⚠️ Please select a product code.")
        else:
            code_input = label_to_code[chosen_label]
            prod = product_dict[code_input]
            st.session_state.entries.append({
                "Product Code": code_input,
                "Product Name": prod["Product Name"],
                "Per Case": prod["Per Case"],
                "Qty": int(qty_input),
                "Rate": float(prod["Rate"]),
                "Amount": float(prod["Rate"]) * int(qty_input),
            })
            st.success(f"Added {code_input} — {prod['Product Name']} (Qty {qty_input})")

# -------------------- Display Order Table and Summary --------------------
if st.session_state.entries:
    st.subheader("Order Details")
    df = pd.DataFrame(st.session_state.entries)
    df.insert(0, "S.No", range(1, len(df) + 1))
    display_df = df[["S.No","Product Code","Product Name","Per Case","Qty","Rate","Amount"]]
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    # Delete item control (by S.No)
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

    # Totals
    sub_total = float(df["Amount"].sum())

    discount = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, step=1.0)
    discounted_total = sub_total * (1 - discount/100)
    discount_value = sub_total - discounted_total

    pkg_charges = st.number_input("Package Charges (%)", min_value=0.0, max_value=100.0, step=0.5)
    pkg_amount = discounted_total * (pkg_charges/100)

    total = discounted_total + pkg_amount

    st.markdown(f"**Sub Total:** Rs. {sub_total:.2f}")
    st.markdown(f"**Discount:** {discount:.2f}% -> Rs. {discount_value:.2f}")
    st.markdown(f"**Package Charges:** {pkg_charges:.2f}% -> Rs. {pkg_amount:.2f}")
    st.markdown(f"**Total:** Rs. {total:.2f}")

    # -------------------- Generate Bill TXT & PDF --------------------
    if st.button("Generate Bill"):
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_file = f"bill_{ts}.txt"
        pdf_file = f"bill_{ts}.pdf"

        # Text bill (always ASCII-safe; Streamlit can show Unicode, but text file is fine either way)
        def txt_safe(s: str) -> str:
            # For consistent text output, keep ASCII
            return ascii_safe(s)

        with open(txt_file, "w", encoding="utf-8") as f:
            if os.path.exists(HEADER_IMG):
                f.write(f"[Header Image: {HEADER_IMG}]\n")
            f.write("SALES ORDER\n=======================\n")
            f.write(f"Customer: {txt_safe(customer_name)} | {txt_safe(customer_mobile)}\n")
            f.write(f"Address: {txt_safe(customer_address)}\n\n")
            for _, row in df.iterrows():
                f.write(
                    f"{row['S.No']} {txt_safe(row['Product Code'])} {txt_safe(row['Product Name'])} "
                    f"Per Case: {txt_safe(row['Per Case'])} Rs. {row['Rate']:.2f} x {row['Qty']} = Rs. {row['Amount']:.2f}\n"
                )
            f.write(f"\nSub Total: Rs. {sub_total:.2f}\n")
            f.write(f"Discount: {discount:.2f}%  (-Rs. {discount_value:.2f})\n")
            f.write(f"Package Charges: {pkg_charges:.2f}%  (+Rs. {pkg_amount:.2f})\n")
            f.write(f"Total: Rs. {total:.2f}\n")

        # PDF bill with Unicode font if available
        pdf = PDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()

        # Select fonts
        if pdf.unicode_font_loaded:
            pdf.set_font(pdf.font_name, size=10)
            hfont = (pdf.font_name, 14, "B")
            thfont = (pdf.font_name, 10, "B")
            rfont = (pdf.font_name, 10, "")
        else:
            pdf.set_font("Arial", size=10)
            hfont = ("Arial", 14, "B")
            thfont = ("Arial", 10, "B")
            rfont = ("Arial", 10, "")

        # Header image
        if os.path.exists(HEADER_IMG):
            avail_w = pdf.w - 20
            header_h = 40
            y_start = pdf.get_y()
            pdf.image(HEADER_IMG, x=10, y=y_start, w=avail_w, h=header_h)
            pdf.ln(header_h + 5)
        else:
            pdf.ln(15)

        # Title
        pdf.set_font(hfont[0], hfont[2], hfont[1])
        pdf.safe_cell(0, 10, "SALES ORDER", ln=True, align='C')
        pdf.ln(3)

        # Customer info
        pdf.set_font(rfont[0], "", rfont[1])
        pdf.safe_cell(0, 6, f"Customer: {customer_name} | {customer_mobile}", ln=True)
        pdf.safe_multi_cell(0, 6, f"Address: {customer_address}")
        pdf.ln(5)

        # Table header
        pdf.set_font(thfont[0], thfont[2], thfont[1])
        col_w = [12,30,60,25,15,20,25]
        headers = ["S.No","Code","Name","Per Case","Qty","Rate","Amount"]
        for w, h in zip(col_w, headers):
            pdf.safe_cell(w,7,h,1,0,'C')
        pdf.ln()

        # Table rows
        pdf.set_font(rfont[0], "", rfont[1])
        for _, row in df.iterrows():
            name = str(row['Product Name'])
            # avoid Unicode ellipsis
            if len(name) > 28:
                name = name[:27] + "..."
            pdf.safe_cell(col_w[0],6,str(row['S.No']),1)
            pdf.safe_cell(col_w[1],6,str(row['Product Code']),1)
            pdf.safe_cell(col_w[2],6,name,1)
            pdf.safe_cell(col_w[3],6,str(row['Per Case']),1,0,'R')
            pdf.safe_cell(col_w[4],6,str(row['Qty']),1,0,'R')
            pdf.safe_cell(col_w[5],6,f"{row['Rate']:.2f}",1,0,'R')
            pdf.safe_cell(col_w[6],6,f"{row['Amount']:.2f}",1,0,'R')
            pdf.ln()

        # Summary
        pdf.ln(2)
        for w in col_w[:5]: pdf.safe_cell(w,6,'',0)
        pdf.safe_cell(col_w[5],6,"Sub Total",1,0,'R')
        pdf.safe_cell(col_w[6],6,f"Rs. {sub_total:.2f}",1,1,'R')

        for w in col_w[:5]: pdf.safe_cell(w,6,'',0)
        pdf.safe_cell(col_w[5],6,"Discount",1,0,'R')
        pdf.safe_cell(col_w[6],6,f"{discount:.2f}% (-Rs. {discount_value:.2f})",1,1,'R')

        for w in col_w[:5]: pdf.safe_cell(w,6,'',0)
        pdf.safe_cell(col_w[5],6,"Package Charges",1,0,'R')
        pdf.safe_cell(col_w[6],6,f"{pkg_charges:.2f}% (+Rs. {pkg_amount:.2f})",1,1,'R')

        for w in col_w[:5]: pdf.safe_cell(w,6,'',0)
        pdf.safe_cell(col_w[5],6,"Total",1,0,'R')
        pdf.safe_cell(col_w[6],6,f"Rs. {total:.2f}",1,1,'R')

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
