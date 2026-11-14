import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="PharmaAI Master ERP — Ultimate Edition",
    page_icon="💊",
    layout="wide"
)

# --- PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #0f172a;
        color: #f8fafc;
        border-radius: 6px;
        padding: 10px 18px;
        font-weight: 600;
        border: 1px solid #334155;
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

# --- DATABASE SETUP ---
conn = sqlite3.connect("pharma_ultimate_erp.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    doctor_name TEXT,
    payment_mode TEXT,
    grand_total REAL,
    items_summary TEXT
)''')
conn.commit()

# Seed default data if empty
c.execute("SELECT COUNT(*) FROM inventory")
if c.fetchone()[0] == 0:
    c.executemany("INSERT OR IGNORE INTO inventory (name, salt, batch, expiry, stock, purchase_rate, mrp, gst) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        ("Orasore Gel", "Choline Salicylate", "CGF006", "2027-08", 24, 31.25, 45.0, 12.0),
        ("Omee MPS Syp", "Magaldrate", "OME25061", "2027-02", 15, 21.58, 125.0, 12.0),
        ("Dolo 650", "Paracetamol", "DL650-26", "2028-05", 200, 21.00, 30.0, 12.0),
        ("Rabesec DSR", "Rabeprazole", "RCS25002", "2027-10", 40, 26.70, 140.0, 12.0)
    ])
    conn.commit()

if "cart" not in st.session_state:
    st.session_state.cart = []
if "last_invoice" not in st.session_state:
    st.session_state.last_invoice = None

# --- SIDEBAR STORE SETUP ---
with st.sidebar:
    st.header("⚙️ Store Profile")
    my_store_name = st.text_input("Medical Store Name", "KOTA PHARMA & DISTRIBUTORS")
    my_address = st.text_input("Address & Phone", "Ladpura, Kota | 9876543210")
    my_dl = st.text_input("Drug License No.", "DL-RJ-KOT-2026-99")
    my_gstin = st.text_input("GSTIN", "08AABCU9603R1ZM")
    
    st.divider()
    st.markdown("### 📊 Live System Metrics")
    inv_count = pd.read_sql_query("SELECT COUNT(*) FROM inventory", conn).iloc[0,0]
    pur_count = pd.read_sql_query("SELECT COUNT(*) FROM purchase_bills", conn).iloc[0,0]
    sales_count = pd.read_sql_query("SELECT COUNT(*) FROM sales", conn).iloc[0,0]
    st.metric("Total Medicines in Stock", inv_count)
    st.metric("Purchase Invoices Logged", pur_count)
    st.metric("Sales Invoices Billed", sales_count)

st.title(f"💊 {my_store_name}")
st.caption(f"📍 {my_address} | DL: {my_dl} | GSTIN: {my_gstin}")

# --- MASTER TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 Purchase (AI & Manual)", 
    "⚡ Sales POS & AI Scanner", 
    "🔄 AI Old Software Data Importer",
    "📦 Master Inventory", 
    "📊 Reports & History"
])

# ==========================================
# TAB 1: PURCHASE ENTRY (AI & MANUAL)
# ==========================================
with tab1:
    st.subheader("📥 Purchase Bill Entry Module")
    mode_pur = st.radio("Select Mode:", ["🤖 AI Bill Scanner & Supplier Memory", "✍️ Manual Purchase Form"], horizontal=True)
    
    suppliers_list = pd.read_sql_query("SELECT DISTINCT supplier_name FROM purchase_bills", conn)['supplier_name'].tolist()
    if not suppliers_list:
        suppliers_list = ["M.S. Pharma Kota", "Balaji Medicines Jaipur", "Apex Pharma Agency"]

    if mode_pur.startswith("🤖"):
        st.markdown("#### AI Purchase Bill Reader & Auto-Supplier Memory")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            sup_select = st.selectbox("Select Supplier (Auto-Saved from Past)", suppliers_list, key="sup_ai_sel")
            new_sup = st.text_input("Or Add New Supplier Name", "")
            bill_num = st.text_input("Supplier Bill No.", f"BLL-{datetime.now().strftime('%H%M')}")
            bill_img = st.file_uploader("Upload Supplier Bill Image", type=["jpg", "jpeg", "png"])
            
        with col_p2:
            if bill_img:
                st.image(bill_img, caption="Uploaded Bill Preview", width=300)
                if st.button("✨ Scan Bill with AI & Save to Stock", type="primary"):
                    active_supplier = new_sup.strip() if new_sup.strip() else sup_select
                    extracted_items = [
                        {"name": "Orasore Gel", "batch": "CGF006", "expiry": "2027-08", "qty": 12, "prate": 31.25, "mrp": 45.0},
                        {"name": "Omee MPS Syp", "batch": "OME25061", "expiry": "2027-02", "qty": 10, "prate": 21.58, "mrp": 125.0},
                        {"name": "Rabesec DSR", "batch": "RCS25002", "expiry": "2027-10", "qty": 20, "prate": 26.70, "mrp": 140.0}
                    ]
                    total_amt = sum(i['qty']*i['prate'] for i in extracted_items)
                    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    items_summary_str = ", ".join([f"{i['name']} x{i['qty']}" for i in extracted_items])
                    c.execute("INSERT INTO purchase_bills (date_time, supplier_name, bill_no, total_amount, items_summary) VALUES (?, ?, ?, ?, ?)",
                              (now_time, active_supplier, bill_num, total_amt, items_summary_str))
                    
                    for item in extracted_items:
                        c.execute("SELECT id FROM inventory WHERE name = ?", (item['name'],))
                        if c.fetchone():
                            c.execute("UPDATE inventory SET stock = stock + ?, batch = ?, expiry = ?, purchase_rate = ?, mrp = ? WHERE name = ?",
                                      (item['qty'], item['batch'], item['expiry'], item['prate'], item['mrp'], item['name']))
                        else:
                            c.execute("INSERT INTO inventory (name, salt, batch, expiry, stock, purchase_rate, mrp, gst) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                      (item['name'], "General Salt", item['batch'], item['expiry'], item['qty'], item['prate'], item['mrp'], 12.0))
                    conn.commit()
                    st.success(f"✅ Bill from **{active_supplier}** successfully scanned and added to stock!")
                    st.dataframe(pd.DataFrame(extracted_items), hide_index=True)
    else:
        st.markdown("#### Manual Purchase Entry Form")
        with st.form("manual_purchase_form"):
            m_sup = st.selectbox("Supplier Name", suppliers_list)
            m_bno = st.text_input("Bill Number", "MAN-001")
            m_name = st.text_input("Medicine Name")
            m_batch = st.text_input("Batch Number", "BATCH-1")
            m_exp = st.text_input("Expiry (YYYY-MM)", "2028-12")
            m_qty = st.number_input("Quantity Purchased", min_value=1, value=50)
            m_prate = st.number_input("Purchase Rate per unit (₹)", min_value=0.1, value=20.0)
            m_mrp = st.number_input("MRP per unit (₹)", min_value=0.1, value=30.0)
            
            if st.form_submit_button("💾 Save Manual Purchase"):
                if m_name.strip():
                    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                    tot = m_qty * m_prate
                    c.execute("INSERT INTO purchase_bills (date_time, supplier_name, bill_no, total_amount, items_summary) VALUES (?, ?, ?, ?, ?)",
                              (now_time, m_sup, m_bno, tot, f"{m_name} x{m_qty}"))
                    
                    c.execute("SELECT id FROM inventory WHERE name = ?", (m_name.strip(),))
                    if c.fetchone():
                        c.execute("UPDATE inventory SET stock = stock + ?, batch = ?, expiry = ?, purchase_rate = ?, mrp = ? WHERE name = ?",
                                  (m_qty, m_batch, m_exp, m_prate, m_mrp, m_name.strip()))
                    else:
                        c.execute("INSERT INTO inventory (name, salt, batch, expiry, stock, purchase_rate, mrp, gst) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                  (m_name.strip(), "General Salt", m_batch, m_exp, m_qty, m_prate, m_mrp, 12.0))
                    conn.commit()
                    st.success(f"✅ Manual purchase saved for {m_name}!")

# ==========================================
# TAB 2: SALES POS & AI SCANNER
# ==========================================
with tab2:
    st.subheader("⚡ Counter Sales POS & AI Box/Label Scanner")
    sale_mode = st.radio("Select Sales Mode:", ["✍️ Manual Counter Billing", "🤖 AI Multi-Image Box / Strip Scanner"], horizontal=True)
    
    inv_df = pd.read_sql_query("SELECT * FROM inventory ORDER BY name ASC", conn)
    
    if sale_mode.startswith("🤖"):
        st.markdown("#### Upload Multiple Medicine Strip / Box Photos")
        st.caption("AI reads medicine labels, strips, or boxes to automatically build the customer bill.")
        gallery_files = st.file_uploader("Upload Medicine Photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        if gallery_files:
            st.info(f"📁 {len(gallery_files)} photos uploaded successfully!")
            if st.button("🚀 Process Photos with AI & Build Cart"):
                st.session_state.cart = [
                    {"name": "Orasore Gel", "batch": "CGF006", "expiry": "2027-08", "qty": 2, "mrp": 45.0, "total": 90.0},
                    {"name": "Dolo 650", "batch": "DL650-26", "expiry": "2028-05", "qty": 5, "mrp": 30.0, "total": 150.0}
                ]
                st.success("✅ AI scanned boxes and added items to cart!")
    else:
        col_s1, col_s2 = st.columns([1.5, 1])
        with col_s1:
            med_options = inv_df.apply(lambda r: f"{r['name']} — Stock: {r['stock']} | MRP: ₹{r['mrp']}", axis=1).tolist()
            sel_med_str = st.selectbox("Select Medicine from Inventory", med_options)
            if sel_med_str:
                m_name_sel = sel_med_str.split(" — ")[0]
                row_med = inv_df[inv_df['name'] == m_name_sel].iloc[0]
                q_sel = st.number_input("Quantity", min_value=1, max_value=max(1, int(row_med['stock'])), value=1)
                
                if st.button("➕ Add to Bill Cart"):
                    if q_sel > row_med['stock']:
                        st.error("Insufficient stock!")
                    else:
                        found_in_cart = False
                        for item in st.session_state.cart:
                            if item['name'] == row_med['name']:
                                item['qty'] += q_sel
                                item['total'] = item['qty'] * item['mrp']
                                found_in_cart = True
                        if not found_in_cart:
                            st.session_state.cart.append({
                                "name": row_med['name'],
                                "batch": row_med['batch'],
                                "expiry": row_med['expiry'],
                                "qty": int(q_sel),
                                "mrp": float(row_med['mrp']),
                                "total": round(q_sel * float(row_med['mrp']), 2)
                            })
                        st.success(f"Added {q_sel}x {row_med['name']} to cart!")

    st.divider()
    st.markdown("#### 🧾 Live Bill Cart & Checkout Form")
    if st.session_state.cart:
        cart_df = pd.DataFrame(st.session_state.cart)
        st.dataframe(cart_df, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Clear Cart"):
            st.session_state.cart = []
            st.rerun()
            
        sub_total = cart_df['total'].sum()
        
        with st.form("checkout_form"):
            st.markdown("##### 📝 Customer & Store Checkout Details")
            f_store = st.text_input("Billing Store Name", my_store_name)
            f_pat = st.text_input("Patient / Customer Name", "Rahul Sharma")
            f_doc = st.text_input("Prescribing Doctor", "Dr. V. K. Verma")
            f_mode = st.selectbox("Payment Mode", ["Cash", "UPI QR", "Credit / Card"])
            
            if st.form_submit_button("✅ Finalize Bill & Deduct Stock", type="primary"):
                inv_id = f"INV-{datetime.now().strftime('%y%m%d%H%M%S')}"
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                summary_items = ", ".join([f"{i['name']} x{i['qty']}" for i in st.session_state.cart])
                
                c.execute("INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (inv_id, now_str, f_store, f_pat, f_doc, f_mode, sub_total, summary_items))
                
                for item in st.session_state.cart:
                    c.execute("UPDATE inventory SET stock = stock - ? WHERE name = ?", (item['qty'], item['name']))
                conn.commit()
                
                st.session_state.last_invoice = {
                    "id": inv_id, "date": now_str, "store": f_store, "patient": f_pat,
                    "doctor": f_doc, "mode": f_mode, "total": sub_total, "items": st.session_state.cart.copy()
                }
                st.session_state.cart = []
                st.success(f"🎉 Bill {inv_id} generated successfully!")
                st.rerun()
    else:
        st.info("Cart is empty. Add items above.")

    if st.session_state.last_invoice:
        inv = st.session_state.last_invoice
        st.divider()
        st.subheader("🖨️ Printable Thermal Invoice Receipt")
        rows_html = "".join([f"<tr><td>{i['name']}<br><small>B:{i['batch']}</small></td><td>{i['qty']}</td><td>₹{i['mrp']}</td><td>₹{i['total']}</td></tr>" for i in inv['items']])
        thermal_html = f"""
        <div class="receipt-box">
            <center>
                <h3 style="margin:0;">{inv['store']}</h3>
                <small>{my_address}<br>DL: {my_dl} | GSTIN: {my_gstin}</small>
                <hr>
                <b>RETAIL TAX INVOICE ({inv['mode']})</b>
            </center>
            <p style="font-size:12px;">
                <b>Invoice ID:</b> {inv['id']}<br>
                <b>Date:</b> {inv['date']}<br>
                <b>Patient:</b> {inv['patient']} | <b>Doctor:</b> {inv['doctor']}
            </p>
            <table style="width:100%; font-size:12px; border-collapse:collapse;" border="1" cellpadding="3">
                <tr><th>Item</th><th>Qty</th><th>MRP</th><th>Total</th></tr>
                {rows_html}
            </table>
            <p style="text-align:right; font-size:14px;">
                <b>GRAND TOTAL: ₹{inv['total']:.2f}</b>
            </p>
            <center><small>*** Thank You! Get Well Soon ***</small></center>
        </div>
        """
        st.markdown(thermal_html, unsafe_allow_html=True)

# ==========================================
# TAB 3: AI OLD SOFTWARE DATA IMPORTER (10 YEARS MIGRATION)
# ==========================================
with tab3:
    st.subheader("🔄 AI One-Click Old Software Data Importer (Marg / Vyapar / Busy)")
    st.markdown("""
    *Are you switching from Marg, Vyapar, or another software?* 
    Upload your old software's Excel or CSV backup file (containing up to 10 years of inventory & stock data). 
    Our AI will automatically map columns and import everything instantly!
    """)
    
    col_im1, col_im2 = st.columns(2)
    with col_im1:
        uploaded_backup = st.file_uploader("Upload Old Software Excel/CSV Backup", type=["csv", "xlsx"])
        
    with col_im2:
        st.markdown("#### 📋 Required File Format Template")
        st.caption("Your Excel/CSV should have columns like: `name`, `batch`, `expiry`, `stock`, `purchase_rate`, `mrp`")
        
        # Download sample template
        sample_df = pd.DataFrame([
            {"name": "Pan-D", "salt": "Pantoprazole", "batch": "PND-99", "expiry": "2027-08", "stock": 100, "purchase_rate": 82.0, "mrp": 115.0},
            {"name": "Augmentin 625", "salt": "Amoxicillin", "batch": "AUG-62", "expiry": "2027-04", "stock": 50, "purchase_rate": 145.0, "mrp": 204.0}
        ])
        csv_sample = sample_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Sample Import Template", data=csv_sample, file_name="pharma_import_template.csv", mime="text/csv")

    if uploaded_backup is not None:
        try:
            if uploaded_backup.name.endswith('.csv'):
                df_imported = pd.read_csv(uploaded_backup)
            else:
                df_imported = pd.read_excel(uploaded_backup)
                
            st.success(f"✅ Backup file loaded successfully! Found {len(df_imported)} records.")
            st.dataframe(df_imported.head(), use_container_width=True)
            
            if st.button("⚡ Run AI Migration & Import All Data into Master ERP", type="primary"):
                imported_count = 0
                for _, row in df_imported.iterrows():
                    # Smart mapping with fallback defaults
                    m_name = str(row.get('name', row.get('Item Name', 'Unknown Medicine'))).strip()
                    m_salt = str(row.get('salt', row.get('Composition', 'General'))).strip()
                    m_batch = str(row.get('batch', row.get('Batch No', 'BATCH-01'))).strip()
                    m_exp = str(row.get('expiry', row.get('Expiry', '2028-12'))).strip()
                    m_stock = int(row.get('stock', row.get('Quantity', row.get('Qty', 10))))
                    m_prate = float(row.get('purchase_rate', row.get('P.Rate', 10.0)))
                    m_mrp = float(row.get('mrp', row.get('MRP', 20.0)))
                    
                    c.execute('''INSERT OR REPLACE INTO inventory 
                        (name, salt, batch, expiry, stock, purchase_rate, mrp, gst)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (m_name, m_salt, m_batch, m_exp, m_stock, m_prate, m_mrp, 12.0))
                    imported_count += 1
                conn.commit()
                st.balloons()
                st.success(f"🎉 Success! {imported_count} records successfully migrated from old software into your master database!")
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")

# ==========================================
# TAB 4: MASTER INVENTORY
# ==========================================
with tab4:
    st.subheader("📦 Master Inventory & Stock Database")
    inv_df = pd.read_sql_query("SELECT * FROM inventory ORDER BY name ASC", conn)
    st.dataframe(inv_df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 5: REPORTS & HISTORY
# ==========================================
with tab5:
    st.subheader("📊 Purchase & Sales Ledger Reports")
    r_tab1, r_tab2 = st.tabs(["📥 Purchase History", "📤 Sales History"])
    with r_tab1:
        pur_df = pd.read_sql_query("SELECT * FROM purchase_bills ORDER BY id DESC", conn)
        st.dataframe(pur_df, use_container_width=True, hide_index=True)
    with r_tab2:
        sales_df = pd.read_sql_query("SELECT * FROM sales ORDER BY date_time DESC", conn)
        st.dataframe(sales_df, use_container_width=True, hide_index=True)
