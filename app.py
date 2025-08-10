import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os
import unicodedata

# --- Shop Header Image ---
HEADER_IMG = "header.png"
if os.path.exists(HEADER_IMG):
    st.image(HEADER_IMG, use_container_width=True)
else:
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

# --------- Unicode helpers for FPDF ---------
def ascii_safe(text: str) -> str:
    """Strip/replace to ASCII for when we don't have a Unicode font."""
    if text is None:
        return ""
    t = unicodedata.normalize("NFKD", str(text))
    t = (
        t.replace("…", "...")
         .replace("−", "-")
         .replace("—", "-")
         .replace("–", "-")
    )
    return t.encode("ascii", "ignore").decode("ascii")

def find_font_paths():
    """Return (regular_path, bold_path) if found, else (None, None)."""
    candidates_regular = [
        "fonts/NotoSansTamil-Regular.ttf",
        "fonts/NotoSans-Regular.ttf",
        "fonts/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    candidates_bold = [
        "fonts/NotoSansTamil-Bold.ttf",
        "fonts/NotoSans-Bold.ttf",
        "fonts/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    reg = next((p for p in candidates_regular if os.path.exists(p)), None)
    bold = next((p for p in candidates_bold if os.path.exists(p)), None)
    return reg, bold

class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unicode_font_loaded = False
        self.bold_supported = False
        self.font_family_name = "Arial"  # fallback core font family

        reg_path, bold_path = find_font_paths()
        if reg_path:
            try:
                self.add_font("Universal", "", reg_path, uni=True)
                self.font_family_name = "Universal"
                self.unicode_font_loaded = True
            except Exception:
                self.unicode_font_loaded = False
                self.font_family_name = "Arial"

        if self.unicode_font_loaded and bold_path:
            try:
                # Add bold face for the same family name
                self.add_font("Universal", "B", bold_path, uni=True)
                self.bold_supported = True
            except Exception:
                self.bold_supported = False

    def set_u_font(self, size: int, bold: bool = False):
        """Set font with optional bold. If bold TTF isn't available, fall back to normal."""
        if self.unicode_font_loaded:
            style = "B" if (bold and self.bold_supported) else ""
            self.set_font(self.font_family_name, style, size)
        else:
            # Core fonts (Arial) support style toggling without extra TTFs
            style = "B" if bold else ""
            self.set_font("Arial", style, size)

    def safe_cell(self, w, h=0, txt="", border=0, ln=0, align="", fill=False, link=""):
        if not self.unicode_font_loaded:
            txt = ascii_safe(txt)
        super().cell(w, h, txt, border, ln, align, fill, link)

    def safe_multi_cell(self, w, h, txt="", border=0, align="J", fill=False):
        if not self.unicode_font_loaded:
            txt = ascii_safe(txt)
        super().multi_cell(w, h, txt, border, align, fill)

# --- Add Order Items Form ---
with st.form("add_form"):
    st.subheader("Add Order Items")

    codes = sorted(product_dict.keys())
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

# --- Display Order Table and Summary ---
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
    st.markdown(f"**Discount:** {discount:.2f}% → Rs. {discount_value:.2f}")
    st.markdown(f"**Package Charges:** {pkg_charges:.2f}% → Rs. {pkg_amount:.2f}")
    st.markdown(f"**Total:** Rs. {total:.2f}")

    # --- Generate Bill TXT & PDF ---
    if st.button("Generate Bill"):
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_file = f"bill_{ts}.txt"
        pdf_file = f"bill_{ts}.pdf"

        # Text bill
        with open(txt_file, "w", encoding="utf-8") as f:
            if os.path.exists(HEADER_IMG):
                f.write(f"[Header Image: {HEADER_IMG}]\n")
            f.write("SALES ORDER\n=======================\n")
            f.write(f"Customer: {customer_name} | {customer_mobile}\n")
            f.write(f"Address: {customer_address}\n\n")
            for _, row in df.iterrows():
                f.write(
                    f"{row['S.No']} {row['Product Code']} {row['Product Name']} "
                    f"Per Case: {row['Per Case']} Rs. {row['Rate']:.2f} x {row['Qty']} = Rs. {row['Amount']:.2f}\n"
                )
            f.write(f"\nSub Total: Rs. {sub_total:.2f}\n")
            f.write(f"Discount: {discount:.2f}%  (-Rs. {discount_value:.2f})\n")
            f.write(f"Package Charges: {pkg_charges:.2f}%  (+Rs. {pkg_amount:.2f})\n")
            f.write(f"Total: Rs. {total:.2f}\n")

        # PDF bill
        pdf = PDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()

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
        pdf.set_u_font(size=14, bold=True)  # will fall back to non-bold if bold TTF not loaded
        pdf.safe_cell(0, 10, "SALES ORDER", ln=True, align='C')
        pdf.ln(3)

        # Customer info
        pdf.set_u_font(size=10, bold=False)
        pdf.safe_cell(0, 6, f"Customer: {customer_name} | {customer_mobile}", ln=True)
        pdf.safe_multi_cell(0, 6, f"Address: {customer_address}")
        pdf.ln(5)

        # Table header
        pdf.set_u_font(size=10, bold=True)
        col_w = [12,30,60,25,15,20,25]
        headers = ["S.No","Code","Name","Per Case","Qty","Rate","Amount"]
        for w, h in zip(col_w, headers):
            pdf.safe_cell(w,7,h,1,0,'C')
        pdf.ln()

        # Table rows
        pdf.set_u_font(size=10, bold=False)
        for _, row in df.iterrows():
            name = str(row['Product Name'])
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

        pdf.output(pdf_file)
        with open(txt_file,'rb') as tf:
            st.download_button("⬇️ Download Text Bill", tf, txt_file)
        with open(pdf_file,'rb') as pf:
            st.download_button("⬇️ Download PDF Bill", pf, pdf_file)

        st.success(f"Invoice generated: {txt_file}, {pdf_file}")
        st.session_state.entries = []
else:
    st.info("Add at least one item to generate a bill.")
