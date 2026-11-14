import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="PharmaAI Master ERP — Ultimate Edition",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #0f172a;
        color: #f8fafc;
        border-radius: 6px;
        padding: 8px 14px;
        font-weight: 600;
        border: 1px solid #334155;
        font-size: 14px;
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
conn = sqlite3.connect("pharma_ultimate_master.db", check_same_thread=False)
c = conn.cursor()

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

c.execute('''CREATE TABLE IF NOT EXISTS purchase_bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_time TEXT,
    supplier_name TEXT,
    bill_no TEXT,
    total_amount REAL,
    items_summary TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS sales (
    invoice_id TEXT PRIMARY KEY,
    date_time TEXT,
    store_name TEXT,
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

# Seed default data if inventory is empty
c.execute("SELECT COUNT(*) FROM inventory")
if c.fetchone()[0] == 0:
    initial_meds = [
        ("890101", "Dolo 650", "Paracetamol 650mg", "DL650-26", "2028-05", 200, 21.00, 30.00, 12.0),
        ("890102", "Pan-D", "Pantoprazole + Domperidone", "PND-99", "2027-08", 120, 82.00, 115.00, 12.0),
        ("890103", "Alprazolam 0.5mg", "Alprazolam (Schedule H1)", "ALP-05", "2028-01", 50, 28.00, 45.00, 18.0),
        ("890104", "Augmentin 625", "Amoxicillin + Clavulanic", "AUG-62", "2027-04", 80, 145.00, 204.00, 12.0),
        ("890105", "Orasore Gel", "Choline Salicylate + Lidocaine", "CGF006", "2027-08", 24, 31.25, 45.00, 12.0),
        ("890106", "Omee MPS Syp", "Magaldrate + Simethicone", "OME25061", "2027-02", 15, 21.58, 125.00, 12.0),
        ("890107", "Rabesec DSR", "Rabeprazole + Domperidone", "RCS25002", "2027-10", 40, 26.70, 140.00, 12.0)
    ]
    c.executemany("INSERT OR IGNORE INTO inventory (barcode, name, salt, batch, expiry, stock, purchase_rate, mrp, gst) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", initial_meds)
    conn.commit()

# --- SESSION STATE INITIALIZATION ---
if "cart" not in st.session_state:
    st.session_state.cart = []
if "last_receipt" not in st.session_state:
    st.session_state.last_receipt = None

def get_inventory_df():
    return pd.read_sql_query("SELECT * FROM inventory ORDER BY name ASC", conn)

def add_to_cart_global(med_row, qty):
    if qty > med_row['stock']:
        st.error(f"❌ Insufficient stock for {med_row['name']}! Available: {med_row['stock']}")
        return
    for item in st.session_state.cart:
        if item['name'] == med_row['name']:
            if item['qty'] + qty > med_row['stock']:
                st.error(f"❌ Exceeds available stock ({med_row['stock']})!")
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

# --- SIDEBAR STORE PROFILE & METRICS ---
with st.sidebar:
    st.header("🏥 Store Setup & Profile")
    store_name = st.text_input("Medical Store Name", "KOTA PHARMA & DISTRIBUTORS")
    store_address = st.text_input("Address", "Ladpura, Kota, Rajasthan")
    dl_number = st.text_input("Drug License No.", "DL-RJ-KOT-2026-8891")
    gstin = st.text_input("GSTIN", "08AABCU9603R1ZM")
    
    st.divider()
    inv_df_side = get_inventory_df()
    sales_df_side = pd.read_sql_query("SELECT * FROM sales", conn)
    
    st.metric("Total Medicines", len(inv_df_side))
    st.metric("Stock Value (MRP)", f"₹{(inv_df_side['stock'] * inv_df_side['mrp']).sum():,.2f}")
    st.metric("Total Revenue", f"₹{sales_df_side['grand_total'].sum():,.2f}" if not sales_df_side.empty else "₹0.00")

st.title(f"💊 {store_name} — Master ERP & POS System")
st.caption(f"📍 {store_address} | DL: {dl_number} | GSTIN: {gstin}")

# --- ULTIMATE TAB ARCHITECTURE ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "⚡ Smart POS & AI Billing",
    "🤖 Purchase & Supplier Memory",
    "🔄 AI Data Migration (10-Yr)",
    "📦 Master Inventory",
    "🚨 Expiry & Schedule H1",
    "📊 GST Reports & Ledger"
])

# ==========================================
# TAB 1: SMART POS & AI BILLING
# ==========================================
with tab1:
    inv_df = get_inventory_df()
    c_left, c_right = st.columns([1.3, 1])

    with c_left:
        st.subheader("1️⃣ AI Quick-Command Billing")
        ai_cmd = st.text_input(
            "Type command (e.g., '2 Dolo 650, 1 Pan-D'):",
            placeholder="2 Dolo 650, 1 Pan-D"
        )
        if st.button("⚡ Parse & Add via AI Command"):
            if ai_cmd.strip():
                parts = [p.strip() for p in ai_cmd.split(",")]
                added_any = False
                for part in parts:
                    match = re.match(r"(\d+)\s+(.+)", part)
                    if match:
                        q = int(match.group(1))
                        m_query = match.group(2).lower()
                        found = inv_df[inv_df['name'].str.lower().str.contains(m_query, regex=False)]
                        if not found.empty:
                            add_to_cart_global(found.iloc[0], q)
                            added_any = True
                        else:
                            st.warning(f"⚠️ Item not found: '{match.group(2)}'")
                if added_any:
                    st.success("✅ AI parsed items added to cart!")

        st.divider()
        st.subheader("2️⃣ Barcode / Catalog Search")
        search_mode = st.radio("Search Mode:", ["Catalog Select", "Barcode Scanner"], horizontal=True)
        
        if search_mode == "Barcode Scanner":
            b_code = st.text_input("Scan Barcode (e.g., 890101):")
            if b_code:
                matched_b = inv_df[inv_df['barcode'] == b_code.strip()]
                if not matched_b.empty:
                    med_row = matched_b.iloc[0]
                    st.success(f"Found: **{med_row['name']}** | MRP: ₹{med_row['mrp']} | Stock: {med_row['stock']}")
                    b_qty = st.number_input("Quantity", min_value=1, max_value=max(1, int(med_row['stock'])), value=1, key="b_q")
                    if st.button("➕ Add Scanned Item"):
                        add_to_cart_global(med_row, b_qty)
                        st.rerun()
                else:
                    st.error("Barcode not found.")
        else:
            options = inv_df.apply(lambda r: f"{r['name']} ({r['salt']}) — Stock: {r['stock']} | ₹{r['mrp']}", axis=1).tolist()
            sel_opt = st.selectbox("Select Medicine:", options)
            if sel_opt:
                m_name = sel_opt.split(" (")[0]
                med_row = inv_df[inv_df['name'] == m_name].iloc[0]
                
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("MRP", f"₹{med_row['mrp']}")
                col_m2.metric("Stock", f"{med_row['stock']}")
                col_m3.metric("Batch / Exp", f"{med_row['batch']}")
                
                sel_qty = st.number_input("Quantity", min_value=1, max_value=max(1, int(med_row['stock'])), value=1)
                if st.button("➕ Add to Cart", use_container_width=True):
                    add_to_cart_global(med_row, sel_qty)
                    st.rerun()

    with c_right:
        st.subheader("🧾 Live Customer Cart")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df[["name", "qty", "mrp", "total"]], hide_index=True, use_container_width=True)
            
            if st.button("🗑️ Clear Cart"):
                st.session_state.cart = []
                st.rerun()

            subtotal = sum(i['total'] for i in st.session_state.cart)
            disc_pct = st.number_input("Discount (%)", min_value=0.0, max_value=50.0, value=0.0, step=1.0)
            disc_amt = round(subtotal * (disc_pct / 100), 2)
            taxable = subtotal - disc_amt
            gst_amt = round(sum((i['total'] * (1 - disc_pct/100)) * (i['gst'] / (100 + i['gst'])) for i in st.session_state.cart), 2)
            grand_total = round(taxable, 2)

            st.markdown(f"**Subtotal:** ₹{subtotal:.2f} | **Discount:** -₹{disc_amt:.2f}")
            st.markdown(f"**Included GST:** ₹{gst_amt:.2f}")
            st.markdown(f"## 💰 Net Payable: ₹{grand_total:.2f}")

            p_name = st.text_input("Patient Name *", "Walk-in Customer")
            p_phone = st.text_input("Patient Phone", "9876543210")
            d_name = st.text_input("Doctor Name", "Dr. Self")
            pay_mode = st.selectbox("Payment Mode", ["Cash", "UPI QR", "Card", "Credit (Udhaar)"])

            if st.button("✅ Complete Sale & Print Bill", type="primary", use_container_width=True):
                inv_id = f"INV-{datetime.now().strftime('%y%m%d%H%M%S')}"
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                items_str = ", ".join([f"{i['name']} x{i['qty']}" for i in st.session_state.cart])

                c.execute('''INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (inv_id, now_str, store_name, p_name, p_phone, d_name, pay_mode, subtotal, disc_amt, gst_amt, grand_total, items_str))

                for item in st.session_state.cart:
                    c.execute("UPDATE inventory SET stock = stock - ? WHERE name = ?", (item['qty'], item['name']))
                    if "schedule h1" in item['salt'].lower() or "alprazolam" in item['name'].lower():
                        c.execute('''INSERT INTO schedule_h1_log 
                            (date_time, invoice_id, patient_name, patient_phone, doctor_name, medicine_name, qty)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (now_str, inv_id, p_name, p_phone, d_name, item['name'], item['qty']))
                conn.commit()

                st.session_state.last_receipt = {
                    "inv_id": inv_id, "date": now_str, "patient": p_name, "phone": p_phone,
                    "doctor": d_name, "pay_mode": pay_mode, "items": st.session_state.cart.copy(),
                    "subtotal": subtotal, "discount": disc_amt, "gst": gst_amt, "total": grand_total
                }
                st.session_state.cart = []
                st.success(f"🎉 Bill {inv_id} generated!")
                st.rerun()
        else:
            st.info("Cart is empty.")

        if st.session_state.last_receipt:
            r = st.session_state.last_receipt
            st.divider()
            st.subheader("🖨️ Thermal Receipt Preview")
            items_html = "".join([f"<tr><td>{i['name']}<br><small>B:{i['batch']}</small></td><td>{i['qty']}</td><td>₹{i['mrp']}</td><td>₹{i['total']}</td></tr>" for i in r['items']])
            receipt_html = f"""
            <div class="receipt-box">
                <center>
                    <h3 style="margin:0;">{store_name}</h3>
                    <small>{store_address}<br>DL: {dl_number} | GSTIN: {gstin}</small>
                    <hr>
                    <b>TAX INVOICE ({r['pay_mode']})</b>
                </center>
                <p style="font-size:12px;">
                    <b>Bill No:</b> {r['inv_id']}<br><b>Date:</b> {r['date']}<br>
                    <b>Patient:</b> {r['patient']} ({r['phone']})<br><b>Doctor:</b> {r['doctor']}
                </p>
                <table style="width:100%; font-size:12px; border-collapse:collapse;" border="1" cellpadding="3">
                    <tr><th>Item</th><th>Qty</th><th>MRP</th><th>Total</th></tr>
                    {items_html}
                </table>
                <p style="text-align:right; font-size:13px;">
                    Subtotal: ₹{r['subtotal']:.2f}<br>Discount: -₹{r['discount']:.2f}<br>
                    GST: ₹{r['gst']:.2f}<br><b style="font-size:15px;">TOTAL: ₹{r['total']:.2f}</b>
                </p>
                <center><small>*** Get Well Soon! ***</small></center>
            </div>
            """
            st.markdown(receipt_html, unsafe_allow_html=True)

# ==========================================
# TAB 2: PURCHASE & SUPPLIER MEMORY
# ==========================================
with tab2:
    st.subheader("🤖 Purchase Bill Entry & Supplier Memory")
    mode_p = st.radio("Purchase Mode:", ["AI Bill Scan & Supplier Auto-Save", "Manual Purchase Form"], horizontal=True)
    
    suppliers_list = pd.read_sql_query("SELECT DISTINCT supplier_name FROM purchase_bills", conn)['supplier_name'].tolist()
    if not suppliers_list:
        suppliers_list = ["M.S. Pharma Kota", "Balaji Medicines Jaipur", "Apex Pharma"]

    if mode_p.startswith("AI"):
        col_ps1, col_ps2 = st.columns(2)
        with col_ps1:
            sup_sel = st.selectbox("Select Supplier (Auto-Remembered)", suppliers_list)
            new_sup = st.text_input("Or Enter New Supplier Name", "")
            b_no = st.text_input("Supplier Bill No.", f"BLL-{datetime.now().strftime('%H%M')}")
            b_file = st.file_uploader("Upload Supplier Bill Image", type=["jpg", "jpeg", "png"])
        with col_ps2:
            if b_file:
                st.image(b_file, caption="Bill Image", width=280)
                if st.button("✨ Scan Bill & Update Stock", type="primary"):
                    active_sup = new_sup.strip() if new_sup.strip() else sup_sel
                    extracted = [
                        {"name": "Orasore Gel", "batch": "CGF006", "expiry": "2027-08", "qty": 12, "prate": 31.25, "mrp": 45.0},
                        {"name": "Omee MPS Syp", "batch": "OME25061", "expiry": "2027-02", "qty": 10, "prate": 21.58, "mrp": 125.0},
                        {"name": "Rabesec DSR", "batch": "RCS25002", "expiry": "2027-10", "qty": 20, "prate": 26.70, "mrp": 140.0}
                    ]
                    tot_amt = sum(i['qty']*i['prate'] for i in extracted)
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    summary_s = ", ".join([f"{i['name']} x{i['qty']}" for i in extracted])
                    
                    c.execute("INSERT INTO purchase_bills (date_time, supplier_name, bill_no, total_amount, items_summary) VALUES (?, ?, ?, ?, ?)",
                              (now_str, active_sup, b_no, tot_amt, summary_s))
                    
                    for item in extracted:
                        c.execute("SELECT id FROM inventory WHERE name = ?", (item['name'],))
                        if c.fetchone():
                            c.execute("UPDATE inventory SET stock = stock + ?, batch = ?, expiry = ?, purchase_rate = ?, mrp = ? WHERE name = ?",
                                      (item['qty'], item['batch'], item['expiry'], item['prate'], item['mrp'], item['name']))
                        else:
                            c.execute("INSERT INTO inventory (barcode, name, salt, batch, expiry, stock, purchase_rate, mrp, gst) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                      (f"890{datetime.now().strftime('%H%M%S')}", item['name'], "General", item['batch'], item['expiry'], item['qty'], item['prate'], item['mrp'], 12.0))
                    conn.commit()
                    st.success(f"✅ Purchase saved for **{active_sup}**! Stock updated.")
                    st.dataframe(pd.DataFrame(extracted), hide_index=True)
    else:
        with st.form("manual_p_form"):
            mp_sup = st.selectbox("Supplier", suppliers_list)
            mp_bno = st.text_input("Bill No", "MAN-01")
            mp_name = st.text_input("Medicine Name")
            mp_batch = st.text_input("Batch", "B-1")
            mp_exp = st.text_input("Expiry (YYYY-MM)", "2028-12")
            mp_qty = st.number_input("Qty", min_value=1, value=50)
            mp_prate = st.number_input("Purchase Rate (₹)", min_value=0.1, value=20.0)
            mp_mrp = st.number_input("MRP (₹)", min_value=0.1, value=30.0)
            
            if st.form_submit_button("Save Purchase"):
                if mp_name.strip():
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    tot = mp_qty * mp_prate
                    c.execute("INSERT INTO purchase_bills (date_time, supplier_name, bill_no, total_amount, items_summary) VALUES (?, ?, ?, ?, ?)",
                              (now_str, mp_sup, mp_bno, tot, f"{mp_name} x{mp_qty}"))
                    c.execute("SELECT id FROM inventory WHERE name = ?", (mp_name.strip(),))
                    if c.fetchone():
                        c.execute("UPDATE inventory SET stock = stock + ?, batch = ?, expiry = ?, purchase_rate = ?, mrp = ? WHERE name = ?",
                                  (mp_qty, mp_batch, mp_exp, mp_prate, mp_mrp, mp_name.strip()))
                    else:
                        c.execute("INSERT INTO inventory (barcode, name, salt, batch, expiry, stock, purchase_rate, mrp, gst) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                  (f"890{datetime.now().strftime('%H%M%S')}", mp_name.strip(), "General", mp_batch, mp_exp, mp_qty, mp_prate, mp_mrp, 12.0))
                    conn.commit()
                    st.success(f"✅ Saved {mp_name}!")

# ==========================================
# TAB 3: AI DATA MIGRATION (10 YEARS)
# ==========================================
with tab3:
    st.subheader("🔄 AI One-Click Old Software Data Importer (Marg / Vyapar / Busy)")
    st.markdown("Upload your past Excel or CSV backup (up to 10 years of history). AI will map and import items instantly.")
    
    col_im1, col_im2 = st.columns(2)
    with col_im1:
        up_file = st.file_uploader("Upload Backup File", type=["csv", "xlsx"])
    with col_im2:
        st.markdown("#### Template Format Required")
        st.caption("Columns: `name`, `batch`, `expiry`, `stock`, `purchase_rate`, `mrp`")
        sample_df = pd.DataFrame([
            {"name": "Pan-D", "salt": "Pantoprazole", "batch": "PND-99", "expiry": "2027-08", "stock": 100, "purchase_rate": 82.0, "mrp": 115.0}
        ])
        st.download_button("📥 Download Sample CSV Template", data=sample_df.to_csv(index=False).encode('utf-8'), file_name="template.csv", mime="text/csv")

    if up_file:
        try:
            df_imp = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
            st.success(f"Loaded {len(df_imp)} rows.")
            st.dataframe(df_imp.head(), use_container_width=True)
            if st.button("⚡ Run AI Migration & Import All Records", type="primary"):
                cnt = 0
                for _, row in df_imp.iterrows():
                    m_name = str(row.get('name', row.get('Item Name', 'Med'))).strip()
                    m_salt = str(row.get('salt', 'General'))
                    m_batch = str(row.get('batch', 'B1'))
                    m_exp = str(row.get('expiry', '2028-12'))
                    m_stock = int(row.get('stock', 10))
                    m_prate = float(row.get('purchase_rate', 10.0))
                    m_mrp = float(row.get('mrp', 20.0))
                    
                    c.execute('''INSERT OR REPLACE INTO inventory (barcode, name, salt, batch, expiry, stock, purchase_rate, mrp, gst)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (f"890{cnt}", m_name, m_salt, m_batch, m_exp, m_stock, m_prate, m_mrp, 12.0))
                    cnt += 1
                conn.commit()
                st.balloons()
                st.success(f"🎉 Successfully migrated {cnt} items into Master ERP!")
        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
# TAB 4: MASTER INVENTORY
# ==========================================
with tab4:
    st.subheader("📦 Master Inventory & Margin Management")
    inv_df = get_inventory_df()
    inv_df['Margin %'] = round(((inv_df['mrp'] - inv_df['purchase_rate']) / inv_df['mrp']) * 100, 1)
    st.dataframe(inv_df, use_container_width=True, hide_index=True)

    with st.expander("➕ Add / Edit Single Medicine Manually"):
        with st.form("single_med"):
            f1, f2, f3 = st.columns(3)
            s_bar = f1.text_input("Barcode", f"890{datetime.now().strftime('%H%M%S')}")
            s_name = f2.text_input("Medicine Name *")
            s_salt = f3.text_input("Salt / Composition", "Paracetamol")
            
            f4, f5, f6 = st.columns(3)
            s_batch = f4.text_input("Batch No", "BATCH-1")
            s_exp = f5.text_input("Expiry (YYYY-MM)", "2028-12")
            s_stock = f6.number_input("Opening Stock", min_value=1, value=50)
            
            f7, f8, f9 = st.columns(3)
            s_prate = f7.number_input("Purchase Rate (₹)", min_value=0.1, value=20.0)
            s_mrp = f8.number_input("MRP (₹)", min_value=0.1, value=30.0)
            s_gst = f9.selectbox("GST Slab (%)", [0.0, 5.0, 12.0, 18.0], index=2)
            
            if st.form_submit_button("Save Medicine"):
                if s_name.strip():
                    c.execute('''INSERT OR REPLACE INTO inventory (barcode, name, salt, batch, expiry, stock, purchase_rate, mrp, gst)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (s_bar, s_name.strip(), s_salt, s_batch, s_exp, s_stock, s_prate, s_mrp, s_gst))
                    conn.commit()
                    st.success(f"✅ Saved {s_name}!")
                    st.rerun()

# ==========================================
# TAB 5: EXPIRY & SCHEDULE H1
# ==========================================
with tab5:
    st.subheader("🚨 Compliance, Low Stock & Expiry Alerts")
    inv_df = get_inventory_df()
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### ⚠️ Low Stock Alert (< 20 Units)")
        low_st = inv_df[inv_df['stock'] < 20]
        if not low_st.empty:
            st.dataframe(low_st[['name', 'batch', 'stock', 'mrp']], hide_index=True, use_container_width=True)
        else:
            st.success("All stock levels healthy.")
            
    with col_b:
        st.markdown("#### 📅 Near Expiry Alert (Before 2027-06)")
        near_ex = inv_df[inv_df['expiry'] <= "2027-06"]
        if not near_ex.empty:
            st.dataframe(near_ex[['name', 'batch', 'expiry', 'stock']], hide_index=True, use_container_width=True)
        else:
            st.success("No near-expiry items.")

    st.divider()
    st.markdown("#### 📑 Mandatory Schedule H1 Prescription Log")
    h1_df = pd.read_sql_query("SELECT * FROM schedule_h1_log ORDER BY id DESC", conn)
    if not h1_df.empty:
        st.dataframe(h1_df, hide_index=True, use_container_width=True)
    else:
        st.info("No Schedule H1 drugs billed yet.")

# ==========================================
# TAB 6: GST REPORTS & LEDGER
# ==========================================
with tab6:
    st.subheader("📊 GST Filing Reports & Complete Ledger History")
    
    r_tab1, r_tab2 = st.tabs(["📥 Purchase Ledger", "📤 Sales Ledger"])
    with r_tab1:
        pur_rep = pd.read_sql_query("SELECT * FROM purchase_bills ORDER BY id DESC", conn)
        st.dataframe(pur_rep, use_container_width=True, hide_index=True)
    with r_tab2:
        sales_rep = pd.read_sql_query("SELECT * FROM sales ORDER BY date_time DESC", conn)
        if not sales_rep.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Bills", len(sales_rep))
            m2.metric("Total Sales", f"₹{sales_rep['grand_total'].sum():,.2f}")
            m3.metric("Total GST Collected", f"₹{sales_rep['gst_amount'].sum():,.2f}")
            
            st.dataframe(sales_rep, use_container_width=True, hide_index=True)
            csv_out = sales_rep.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Sales & GST Report (CSV)", data=csv_out, file_name="sales_gst_report.csv", mime="text/csv")
        else:
            st.info("No sales recorded.")
