import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os
import unicodedata

# -------------------- Constants --------------------
HEADER_IMG = "header.png"   # optional
CSV_FILE   = "stock_tracking.csv"

# -------------------- Header --------------------
if os.path.exists(HEADER_IMG):
    st.image(HEADER_IMG, use_container_width=True)
else:
    st.title("Anandhaa Crackers Wholesale Billing")

# -------------------- Customer Details --------------------
st.subheader("Customer Details")
customer_name = st.text_input("Customer Name")
customer_mobile = st.text_input("Customer Mobile")
customer_address = st.text_area("Customer Address")

# -------------------- Load Products --------------------
@st.cache_data
def load_products():
    # Expected columns: Product Code, Product Name, Per Case, Rate
    df = pd.read_csv(CSV_FILE)
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

# -------------------- Session State --------------------
if "entries" not in st.session_state:
    st.session_state.entries = []

# -------------------- FPDF Unicode Helpers --------------------
def ascii_safe(text: str) -> str:
    """Sanitize text to ASCII for when no Unicode TTF is loaded."""
    if text is None:
        return ""
    t = unicodedata.normalize("NFKD", str(text))
    t = (t.replace("…", "...")
           .replace("−", "-")
           .replace("—", "-")
           .replace("–", "-"))
    return t.encode("ascii", "ignore").decode("ascii")

def find_font_paths():
    """Return (regular_path, bold_path) if found."""
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
    """FPDF wrapper that optionally uses a Unicode TTF (regular + bold)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unicode_font_loaded = False
        self.bold_supported = False
        self.font_family_name = "Arial"  # fallback

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
                self.add_font("Universal", "B", bold_path, uni=True)
                self.bold_supported = True
            except Exception:
                self.bold_supported = False

    def set_u_font(self, size: int, bold: bool = False):
        """Set font with optional bold; safe fallback if bold TTF missing."""
        if self.unicode_font_loaded:
            style = "B" if (bold and self.bold_supported) else ""
            self.set_font(self.font_family_name, style, size)
        else:
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

# -------------------- Add Order Items --------------------
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

# -------------------- Table + Totals --------------------
if st.session_state.entries:
    st.subheader("Order Details")
    df = pd.DataFrame(st.session_state.entries)
    df.insert(0, "S.No", range(1, len(df) + 1))
    display_df = df[["S.No","Product Code","Product Name","Per Case","Qty","Rate","Amount"]]
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    # Delete item
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

    # -------------------- Generate Bill --------------------
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
        pdf.set_u_font(size=14, bold=True)  # real bold if bold TTF found
        pdf.safe_cell(0, 10, "SALES ORDER", ln=True, align='C')
        pdf.ln(3)

        # Customer info
        pdf.set_u_font(size=10, bold=False)
        pdf.safe_cell(0, 6, f"Customer: {customer_name} | {customer_mobile}", ln=True)
        pdf.safe_multi_cell(0, 6, f"Address: {customer_address}")
        pdf.ln(5)

        # Table header
        pdf.set_u_font(size=10, bold=True)
        col_w = [12,30,60,25,15,20,25]  # widths for: S.No Code Name PerCase Qty Rate Amount
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

        # -------- Neat summary box aligned to right margin --------
        line_h = 6
        gap_y = 3           # space above the summary box
        rows_needed = 4     # Sub Total, Discount, Package Charges, Total
        box_w = col_w[5] + col_w[6]

        def ensure_space(rows):
            needed = rows * line_h + gap_y
            if pdf.get_y() + needed > (pdf.h - pdf.b_margin):
                pdf.add_page()

        def summary_row(label: str, value: str):
            x_right = pdf.w - pdf.r_margin
            start_x = x_right - box_w
            pdf.set_xy(start_x, pdf.get_y())
            pdf.safe_cell(col_w[5], line_h, label, 1, 0, 'R')
            pdf.safe_cell(col_w[6], line_h, value, 1, 1, 'R')

        pdf.ln(2)
        ensure_space(rows_needed)
        pdf.ln(gap_y)

        summary_row("Sub Total",       f"Rs. {sub_total:.2f}")
        summary_row("Discount",        f"{discount:.2f}% (−Rs. {discount_value:.2f})")
        summary_row("Package Charges", f"{pkg_charges:.2f}% (+Rs. {pkg_amount:.2f})")
        summary_row("Total",           f"Rs. {total:.2f}")

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
