import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="PharmaAI Master ERP — Complete Pharmacy System",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM PROFESSIONAL DARK/ERP STYLING ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        color: #f8fafc;
        border-radius: 6px;
        padding: 10px 18px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }
    .receipt-box {
        background-color: #ffffff;
        color: #000000;
        padding: 20px;
        border-radius: 8px;
        font-family: 'Courier New', Courier, monospace;
        border: 2px dashed #333333;
    }
    </style>
""", unsafe_allow_html=True)

# --- PERSISTENT SQLITE DATABASE SETUP ---
conn = sqlite3.connect("pharma_master_erp.db", check_same_thread=False)
c = conn.cursor()

# Create Tables
c.execute('''CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT,
    name TEXT UNIQUE,
    salt TEXT,
    batch TEXT,
    expiry TEXT,
    stock INTEGER,
    purchase_rate REAL,
    mrp REAL,
    gst REAL
)''')

c.execute('''CREATE TABLE IF NOT EXISTS sales (
    invoice_id TEXT PRIMARY KEY,
    date_time TEXT,
    patient_name TEXT,
    patient_phone TEXT,
    doctor_name TEXT,
    payment_mode TEXT,
    subtotal REAL,
    discount REAL,
    gst_amount REAL,
    grand_total REAL,
    items_summary TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS schedule_h1_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_time TEXT,
    invoice_id TEXT,
    patient_name TEXT,
    patient_phone TEXT,
    doctor_name TEXT,
    medicine_name TEXT,
    qty INTEGER
)''')
conn.commit()

# Seed Initial Real-World Pharmacy Data if Empty
c.execute("SELECT COUNT(*) FROM inventory")
if c.fetchone()[0] == 0:
    initial_meds = [
        ("890101", "Dolo 650", "Paracetamol 650mg", "DL650-26", "2028-05", 200, 21.00, 30.00, 12.0),
        ("890102", "Pan-D", "Pantoprazole + Domperidone", "PND-99", "2027-08", 120, 82.00, 115.00, 12.0),
        ("890103", "Alprazolam 0.5mg", "Alprazolam (Schedule H1)", "ALP-05", "2028-01", 50, 28.00, 45.00, 18.0),
        ("890104", "Augmentin 625", "Amoxicillin + Clavulanic Acid", "AUG-62", "2027-04", 80, 145.00, 204.00, 12.0),
        ("890105", "Orasore Gel", "Choline Salicylate + Lidocaine", "CGF006", "2027-08", 24, 31.25, 45.00, 12.0),
        ("890106", "Omee MPS Syp", "Magaldrate + Simethicone", "OME25061", "2027-02", 15, 21.58, 125.00, 12.0),
        ("890107", "Rabesec DSR", "Rabeprazole + Domperidone", "RCS25002", "2027-10", 40, 26.70, 140.00, 12.0),
        ("890108", "Onditron-MD", "Ondansetron 4mg", "QA25760", "2027-03", 30, 5.25, 25.00, 12.0)
    ]
    c.executemany('''INSERT INTO inventory 
        (barcode, name, salt, batch, expiry, stock, purchase_rate, mrp, gst) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', initial_meds)
    conn.commit()

# --- SESSION STATE ---
if "cart" not in st.session_state:
    st.session_state.cart = []
if "last_receipt" not in st.session_state:
    st.session_state.last_receipt = None

# --- HELPER FUNCTIONS ---
def get_inventory_df():
    return pd.read_sql_query("SELECT * FROM inventory ORDER BY name ASC", conn)

def add_item_to_cart(med_row, qty):
    if qty > med_row['stock']:
        st.error(f"❌ Insufficient stock for {med_row['name']}! Available: {med_row['stock']}")
        return
    # Check if already in cart
    for item in st.session_state.cart:
        if item['name'] == med_row['name']:
            if item['qty'] + qty > med_row['stock']:
                st.error(f"❌ Total quantity exceeds stock ({med_row['stock']})!")
                return
            item['qty'] += qty
            item['total'] = round(item['qty'] * item['mrp'], 2)
            return
    st.session_state.cart.append({
        "barcode": med_row['barcode'],
        "name": med_row['name'],
        "salt": med_row['salt'],
        "batch": med_row['batch'],
        "expiry": med_row['expiry'],
        "qty": int(qty),
        "mrp": float(med_row['mrp']),
        "gst": float(med_row['gst']),
        "total": round(int(qty) * float(med_row['mrp']), 2)
    })

# --- SIDEBAR: STORE SETTINGS & LIVE METRICS ---
with st.sidebar:
    st.header("🏥 Store Profile")
    store_name = st.text_input("Medical Store Name", "KOTA MEDICOS & PHARMA")
    store_address = st.text_input("Address", "Ladpura, Kota, Rajasthan")
    dl_number = st.text_input("Drug License No.", "DL-RJ-KOT-2026-8891")
    gstin = st.text_input("GSTIN", "08AABCU9603R1ZM")
    
    st.divider()
    inv_df = get_inventory_df()
    sales_df_side = pd.read_sql_query("SELECT * FROM sales", conn)
    
    st.metric("Total Medicines", len(inv_df))
    st.metric("Total Stock Value (MRP)", f"₹{(inv_df['stock'] * inv_df['mrp']).sum():,.2f}")
    st.metric("Total Revenue Earned", f"₹{sales_df_side['grand_total'].sum():,.2f}" if not sales_df_side.empty else "₹0.00")

# --- MAIN HEADER ---
st.title(f"💊 {store_name} — Master ERP & AI POS")
st.caption(f"📍 {store_address} | DL: {dl_number} | GSTIN: {gstin}")

# --- TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ Smart POS & Billing",
    "🤖 AI Purchase & Bill Entry",
    "📦 Master Inventory",
    "🚨 Expiry & Schedule H1",
    "📊 GST & Sales Reports"
])

# ==========================================
# TAB 1: SMART POS & BILLING
# ==========================================
with tab1:
    inv_df = get_inventory_df()
    col_left, col_right = st.columns([1.3, 1])

    with col_left:
        st.subheader("1️⃣ AI Quick-Command Billing")
        ai_cmd = st.text_input(
            "Type command (e.g., '2 Dolo 650, 1 Pan-D, 3 Rabesec DSR'):",
            placeholder="2 Dolo 650, 1 Augmentin 625"
        )
        if st.button("⚡ Parse & Add via AI"):
            if ai_cmd.strip():
                parts = [p.strip() for p in ai_cmd.split(",")]
                added_any = False
                for part in parts:
                    match = re.match(r"(\d+)\s+(.+)", part)
                    if match:
                        q = int(match.group(1))
                        med_query = match.group(2).lower()
                        found = inv_df[inv_df['name'].str.lower().str.contains(med_query, regex=False)]
                        if not found.empty:
                            add_item_to_cart(found.iloc[0], q)
                            added_any = True
                        else:
                            st.warning(f"⚠️ Medicine not found: '{match.group(2)}'")
                if added_any:
                    st.success("✅ AI parsed items added to cart!")

        st.divider()
        st.subheader("2️⃣ Barcode / Catalog Search")
        search_mode = st.radio("Search By:", ["Medicine Name / Salt", "Barcode Scan"], horizontal=True)
        
        if search_mode == "Barcode Scan":
            b_code = st.text_input("Scan or Type Barcode (e.g., 890101):")
            if b_code:
                matched_b = inv_df[inv_df['barcode'] == b_code.strip()]
                if not matched_b.empty:
                    med_row = matched_b.iloc[0]
                    st.success(f"Found: **{med_row['name']}** | MRP: ₹{med_row['mrp']} | Stock: {med_row['stock']}")
                    b_qty = st.number_input("Quantity", min_value=1, max_value=max(1, int(med_row['stock'])), value=1, key="b_qty")
                    if st.button("➕ Add Scanned Item"):
                        add_item_to_cart(med_row, b_qty)
                        st.rerun()
                else:
                    st.error("Barcode not found in database.")
        else:
            options = inv_df.apply(lambda r: f"{r['name']} ({r['salt']}) — Stock: {r['stock']} | ₹{r['mrp']}", axis=1).tolist()
            selected_option = st.selectbox("Select Medicine:", options)
            if selected_option:
                med_name = selected_option.split(" (")[0]
                med_row = inv_df[inv_df['name'] == med_name].iloc[0]
                
                c1, c2, c3 = st.columns(3)
                c1.metric("MRP", f"₹{med_row['mrp']}")
                c2.metric("In Stock", f"{med_row['stock']} units")
                c3.metric("Batch / Exp", f"{med_row['batch']} ({med_row['expiry']})")
                
                sel_qty = st.number_input("Enter Quantity", min_value=1, max_value=max(1, int(med_row['stock'])), value=1)
                if st.button("➕ Add to Bill Cart", use_container_width=True):
                    add_item_to_cart(med_row, sel_qty)
                    st.rerun()

    with col_right:
        st.subheader("🧾 Live Customer Cart")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df[["name", "batch", "qty", "mrp", "total"]], hide_index=True, use_container_width=True)
            
            if st.button("🗑️ Clear Cart"):
                st.session_state.cart = []
                st.rerun()

            subtotal = sum(i['total'] for i in st.session_state.cart)
            disc_pct = st.number_input("Discount (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0)
            disc_amt = round(subtotal * (disc_pct / 100), 2)
            taxable = subtotal - disc_amt
            # Inclusive GST calculation
            gst_amt = round(sum((i['total'] * (1 - disc_pct/100)) * (i['gst'] / (100 + i['gst'])) for i in st.session_state.cart), 2)
            grand_total = round(taxable, 2)

            st.markdown(f"**Subtotal:** ₹{subtotal:.2f} | **Discount:** -₹{disc_amt:.2f}")
            st.markdown(f"**Included GST:** ₹{gst_amt:.2f}")
            st.markdown(f"## 💰 Net Payable: ₹{grand_total:.2f}")

            p_name = st.text_input("Patient Name *", "Walk-in Customer")
            p_phone = st.text_input("Patient Mobile (For WhatsApp/H1)", "9876543210")
            d_name = st.text_input("Doctor Name", "Dr. Self / General")
            pay_mode = st.selectbox("Payment Mode", ["Cash", "UPI / QR", "Card", "Credit (Udhaar)"])

            if st.button("✅ Generate Final GST Bill & Deduct Stock", type="primary", use_container_width=True):
                inv_id = f"INV-{datetime.now().strftime('%y%m%d%H%M%S')}"
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                items_str = ", ".join([f"{i['name']} x{i['qty']}" for i in st.session_state.cart])

                # 1. Save Sale
                c.execute('''INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (inv_id, now_str, p_name, p_phone, d_name, pay_mode, subtotal, disc_amt, gst_amt, grand_total, items_str))

                # 2. Deduct Stock & Check Schedule H1
                for item in st.session_state.cart:
                    c.execute("UPDATE inventory SET stock = stock - ? WHERE name = ?", (item['qty'], item['name']))
                    if "schedule h1" in item['salt'].lower() or "alprazolam" in item['name'].lower():
                        c.execute('''INSERT INTO schedule_h1_log 
                            (date_time, invoice_id, patient_name, patient_phone, doctor_name, medicine_name, qty)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (now_str, inv_id, p_name, p_phone, d_name, item['name'], item['qty']))
                conn.commit()

                st.session_state.last_receipt = {
                    "inv_id": inv_id,
                    "date": now_str,
                    "patient": p_name,
                    "phone": p_phone,
                    "doctor": d_name,
                    "pay_mode": pay_mode,
                    "items": st.session_state.cart.copy(),
                    "subtotal": subtotal,
                    "discount": disc_amt,
                    "gst": gst_amt,
                    "total": grand_total
                }
                st.session_state.cart = []
                st.success(f"🎉 Bill {inv_id} Saved Permanently!")
                st.rerun()
        else:
            st.info("Cart is empty. Add medicines from the left panel.")

        # --- PRINTABLE THERMAL RECEIPT PREVIEW ---
        if st.session_state.last_receipt:
            r = st.session_state.last_receipt
            st.divider()
            st.subheader("🖨️ Last Generated Thermal Invoice")
            items_html = "".join([
                f"<tr><td>{i['name']}<br><small>B:{i['batch']} Exp:{i['expiry']}</small></td><td>{i['qty']}</td><td>₹{i['mrp']}</td><td>₹{i['total']}</td></tr>"
                for i in r['items']
            ])
            receipt_html = f"""
            <div class="receipt-box">
                <center>
                    <h3 style="margin:0;">{store_name}</h3>
                    <small>{store_address}<br>DL: {dl_number} | GSTIN: {gstin}</small>
                    <hr>
                    <b>TAX INVOICE ({r['pay_mode']})</b>
                </center>
                <p style="font-size:12px;">
                    <b>Bill No:</b> {r['inv_id']}<br>
                    <b>Date:</b> {r['date']}<br>
                    <b>Patient:</b> {r['patient']} ({r['phone']})<br>
                    <b>Doctor:</b> {r['doctor']}
                </p>
                <table style="width:100%; font-size:12px; border-collapse:collapse;" border="1" cellpadding="4">
                    <tr><th>Item</th><th>Qty</th><th>MRP</th><th>Amt</th></tr>
                    {items_html}
                </table>
                <p style="text-align:right; font-size:13px;">
                    Subtotal: ₹{r['subtotal']:.2f}<br>
                    Discount: -₹{r['discount']:.2f}<br>
                    Incl. GST: ₹{r['gst']:.2f}<br>
                    <b style="font-size:16px;">GRAND TOTAL: ₹{r['total']:.2f}</b>
                </p>
                <center><small>*** Get Well Soon! Computer Generated Invoice ***</small></center>
            </div>
            """
            st.markdown(receipt_html, unsafe_allow_html=True)

# ==========================================
# TAB 2: AI PURCHASE & BILL ENTRY
# ==========================================
with tab2:
    st.subheader("🤖 Supplier Purchase Entry (Photo Upload / Quick Bulk Entry)")
    st.info("Upload a supplier bill image or enter bulk purchase lines to automatically update stock & purchase rates.")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        bill_file = st.file_uploader("Upload Supplier Invoice (JPG/PNG)", type=["jpg", "jpeg", "png"])
        if bill_file:
            st.image(bill_file, caption="Supplier Invoice Preview", use_container_width=True)
            
    with col_u2:
        st.markdown("#### 📝 Quick Bulk Purchase Parser")
        st.caption("Format: `Medicine Name, Batch, Expiry(YYYY-MM), Qty, PurchaseRate, MRP` (One per line)")
        bulk_text = st.text_area(
            "Paste or Type Purchase Items:",
            value="Orasore Gel, CGF006, 2027-08, 12, 31.25, 45.0\nSalvent Ag Syp, SP241602, 2027-05, 10, 30.50, 45.0",
            height=150
        )
        if st.button("🚀 Import Purchase Stock to Database", type="primary"):
            lines = [l.strip() for l in bulk_text.strip().split("\n") if l.strip()]
            count = 0
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    m_name, m_batch, m_exp = parts[0], parts[1], parts[2]
                    m_qty, m_prate, m_mrp = int(parts[3]), float(parts[4]), float(parts[5])
                    
                    c.execute("SELECT id FROM inventory WHERE name = ?", (m_name,))
                    exists = c.fetchone()
                    if exists:
                        c.execute("UPDATE inventory SET stock = stock + ?, batch = ?, expiry = ?, purchase_rate = ?, mrp = ? WHERE name = ?",
                                  (m_qty, m_batch, m_exp, m_prate, m_mrp, m_name))
                    else:
                        b_new = f"890{datetime.now().strftime('%H%M%S')}{count}"
                        c.execute('''INSERT INTO inventory (barcode, name, salt, batch, expiry, stock, purchase_rate, mrp, gst)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                  (b_new, m_name, "Pharma Formulation", m_batch, m_exp, m_qty, m_prate, m_mrp, 12.0))
                    count += 1
            conn.commit()
            st.success(f"✅ Successfully updated/added {count} medicines into Master Database!")

# ==========================================
# TAB 3: MASTER INVENTORY
# ==========================================
with tab3:
    st.subheader("📦 Master Stock & Margin Control")
    inv_df = get_inventory_df()
    inv_df['Margin %'] = round(((inv_df['mrp'] - inv_df['purchase_rate']) / inv_df['mrp']) * 100, 1)
    st.dataframe(inv_df, use_container_width=True, hide_index=True)

    with st.expander("➕ Add / Update Single Medicine"):
        with st.form("single_med_form"):
            f1, f2, f3 = st.columns(3)
            m_bar = f1.text_input("Barcode", f"890{int(datetime.now().timestamp())%10000}")
            m_name = f2.text_input("Medicine Name *")
            m_salt = f3.text_input("Salt / Composition *", "Paracetamol")
            
            f4, f5, f6 = st.columns(3)
            m_batch = f4.text_input("Batch No.", "B-2026")
            m_exp = f5.text_input("Expiry (YYYY-MM)", "2028-06")
            m_qty = f6.number_input("Opening Stock", min_value=1, value=50)
            
            f7, f8, f9 = st.columns(3)
            m_prate = f7.number_input("Purchase Rate (₹)", min_value=0.1, value=20.0)
            m_mrp = f8.number_input("MRP (₹)", min_value=0.1, value=30.0)
            m_gst = f9.selectbox("GST Slab (%)", [0.0, 5.0, 12.0, 18.0], index=2)
            
            if st.form_submit_button("💾 Save Medicine"):
                if m_name.strip():
                    c.execute('''INSERT OR REPLACE INTO inventory 
                        (barcode, name, salt, batch, expiry, stock, purchase_rate, mrp, gst)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (m_bar, m_name.strip(), m_salt, m_batch, m_exp, m_qty, m_prate, m_mrp, m_gst))
                    conn.commit()
                    st.success(f"✅ {m_name} saved to database!")
                    st.rerun()

# ==========================================
# TAB 4: EXPIRY & SCHEDULE H1
# ==========================================
with tab4:
    st.subheader("🚨 Compliance, Low Stock & Expiry Alerts")
    inv_df = get_inventory_df()
    
    c_a, c_b = st.columns(2)
    with c_a:
        st.markdown("#### ⚠️ Low Stock Alert (< 20 Units)")
        low_stock = inv_df[inv_df['stock'] < 20]
        if not low_stock.empty:
            st.dataframe(low_stock[['name', 'batch', 'stock', 'mrp']], hide_index=True, use_container_width=True)
        else:
            st.success("All medicines have sufficient stock!")
            
    with c_b:
        st.markdown("#### 📅 Near Expiry Alert (Before 2027-06)")
        near_exp = inv_df[inv_df['expiry'] <= "2027-06"]
        if not near_exp.empty:
            st.dataframe(near_exp[['name', 'batch', 'expiry', 'stock']], hide_index=True, use_container_width=True)
        else:
            st.success("No near-expiry medicines!")

    st.divider()
    st.markdown("#### 📑 Mandatory Schedule H1 Narcotic / Prescription Register")
    h1_logs = pd.read_sql_query("SELECT * FROM schedule_h1_log ORDER BY id DESC", conn)
    if not h1_logs.empty:
        st.dataframe(h1_logs, hide_index=True, use_container_width=True)
    else:
        st.info("No Schedule H1 drugs sold yet. Whenever Alprazolam or any H1 drug is billed, it automatically logs here.")

# ==========================================
# TAB 5: GST & SALES REPORTS
# ==========================================
with tab5:
    st.subheader("📊 Sales Ledger & GST Filing Export")
    sales_df = pd.read_sql_query("SELECT * FROM sales ORDER BY date_time DESC", conn)
    if not sales_df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Bills Generated", len(sales_df))
        m2.metric("Total Sales Value", f"₹{sales_df['grand_total'].sum():,.2f}")
        m3.metric("Total GST Collected", f"₹{sales_df['gst_amount'].sum():,.2f}")
        
        st.dataframe(sales_df, use_container_width=True, hide_index=True)
        
        csv_data = sales_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Complete GSTR / Sales Report (CSV)",
            data=csv_data,
            file_name=f"Pharma_Sales_GST_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No invoices generated yet.")
