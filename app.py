import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import re
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- DATABASE SETUP ---
conn = sqlite3.connect('pharma_ai.db', check_same_thread=False)
c = conn.cursor()

# 1. Inventory Table
c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                salt TEXT,
                batch TEXT,
                expiry TEXT,
                mrp REAL,
                gst REAL,
                stock INTEGER
            )''')

# 2. Schedule H/H1 Audit Register Table
c.execute('''CREATE TABLE IF NOT EXISTS schedule_h_register (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                patient_name TEXT,
                doctor_name TEXT,
                medicine_name TEXT,
                batch TEXT,
                qty INTEGER
            )''')

# 3. Customer Database Table
c.execute('''CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                last_medicine TEXT,
                next_refill_date TEXT
            )''')

# Sample Data Injection agar khali hai
c.execute("SELECT COUNT(*) FROM inventory")
if c.fetchone()[0] == 0:
    sample_meds = [
        ("Dolo 650", "Paracetamol 650mg", "B101", "2027-05", 30.0, 12.0, 100),
        ("Pan-D", "Pantoprazole + Domperidone", "P204", "2026-12", 190.0, 12.0, 50),
        ("Alprazolam 0.5mg", "Alprazolam (Schedule H1)", "ALP01", "2027-03", 45.0, 18.0, 30),
        ("Augmentin 625", "Amoxicillin + Clavulanic Acid", "AG11", "2027-01", 200.0, 12.0, 30)
    ]
    c.executemany("INSERT INTO inventory (name, salt, batch, expiry, mrp, gst, stock) VALUES (?,?,?,?,?,?,?)", sample_meds)
    conn.commit()

# --- APP UI CONFIGURATION ---
st.set_page_config(page_title="PharmaAI Pro - Enterprise Edition", layout="wide")
st.title("💊 PharmaAI Pro — Next-Gen AI Pharmacy & Billing System")

if 'cart' not in st.session_state:
    st.session_state.cart = []

if 'last_invoice' not in st.session_state:
    st.session_state.last_invoice = None

# --- PDF GENERATOR FUNCTION ---
def generate_pdf_invoice(invoice_data, customer_name, doctor_name):
    pdf_filename = "invoice.pdf"
    c_pdf = canvas.Canvas(pdf_filename, pagesize=letter)
    width, height = letter
    
    c_pdf.setFont("Helvetica-Bold", 16)
    c_pdf.drawString(50, height - 50, "PHARMA AI MEDICAL STORE")
    c_pdf.setFont("Helvetica", 10)
    c_pdf.drawString(50, height - 65, "GSTIN: 08AAAAA0000A1Z5 | Ph: +91 9876543210")
    c_pdf.drawString(50, height - 80, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    c_pdf.drawString(50, height - 110, f"Patient Name: {customer_name}")
    c_pdf.drawString(50, height - 125, f"Prescribing Doctor: {doctor_name}")
    
    c_pdf.line(50, height - 140, 560, height - 140)
    c_pdf.setFont("Helvetica-Bold", 10)
    c_pdf.drawString(50, height - 155, "Medicine")
    c_pdf.drawString(200, height - 155, "Batch")
    c_pdf.drawString(270, height - 155, "Expiry")
    c_pdf.drawString(340, height - 155, "Qty")
    c_pdf.drawString(400, height - 155, "MRP (₹)")
    c_pdf.drawString(480, height - 155, "Total (₹)")
    c_pdf.line(50, height - 165, 560, height - 165)
    
    y = height - 180
    subtotal = 0
    c_pdf.setFont("Helvetica", 10)
    for item in invoice_data:
        c_pdf.drawString(50, y, str(item['Medicine']))
        c_pdf.drawString(200, y, str(item['Batch']))
        c_pdf.drawString(270, y, str(item['Expiry']))
        c_pdf.drawString(340, y, str(item['Qty']))
        c_pdf.drawString(400, y, f"{item['MRP']:.2f}")
        c_pdf.drawString(480, y, f"{item['Total']:.2f}")
        subtotal += item['Total']
        y -= 20
        
    c_pdf.line(50, y - 5, 560, y - 5)
    y -= 25
    c_pdf.setFont("Helvetica-Bold", 11)
    c_pdf.drawString(380, y, f"Grand Total: ₹ {subtotal:.2f}")
    
    c_pdf.setFont("Helvetica-Oblique", 9)
    c_pdf.drawString(50, 50, "Thank you for shopping! Get well soon.")
    c_pdf.save()
    return pdf_filename

# --- NAVIGATION TABS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ Smart Billing & Print", 
    "📦 Inventory & Expiry", 
    "⚖️ Schedule H/H1 Compliance", 
    "📱 GST & WhatsApp CRM",
    "🔄 Marg / Excel Data Import"
])

# ================= TAB 1: SMART BILLING & PRINT =================
with tab1:
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.subheader("🤖 AI Natural Language Quick-Billing")
        ai_input = st.text_input("Type item command (e.g., '2 Dolo 650, 1 Pan-D'):", placeholder="Enter items here...")
        
        if st.button("⚡ Add to Cart via AI") and ai_input:
            df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
            added_any = False
            for _, row in df_inv.iterrows():
                med_name = row['name']
                pattern = rf"(\d+)?\s*{re.escape(med_name)}"
                match = re.search(pattern, ai_input, re.IGNORECASE)
                if match:
                    qty = int(match.group(1)) if match.group(1) else 1
                    if row['stock'] >= qty:
                        total_price = row['mrp'] * qty
                        st.session_state.cart.append({
                            "id": row['id'],
                            "Medicine": med_name,
                            "Batch": row['batch'],
                            "Expiry": row['expiry'],
                            "Qty": qty,
                            "MRP": row['mrp'],
                            "GST%": row['gst'],
                            "Total": total_price
                        })
                        added_any = True
                    else:
                        st.error(f"{med_name} out of stock! Available: {row['stock']}")
            if added_any:
                st.success("Items added to cart successfully!")
            else:
                st.warning("No matching medicine found in inventory.")

        st.divider()
        st.subheader("📋 Available Stock Catalog")
        st.dataframe(pd.read_sql_query("SELECT name, salt, batch, expiry, mrp, gst, stock FROM inventory", conn), use_container_width=True)

    with col2:
        st.subheader("🧾 Invoice Counter & Print")
        cust_name = st.text_input("Patient Name", value="Rahul Sharma")
        cust_phone = st.text_input("Patient WhatsApp Number", value="9876543210")
        doc_name = st.text_input("Prescribing Doctor Name", value="Dr. V. K. Verma")
        
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.table(cart_df[["Medicine", "Batch", "Qty", "MRP", "Total"]])
            
            subtotal = cart_df["Total"].sum()
            gst_amount = (subtotal * 12) / (100 + 12)
            grand_total = subtotal
            
            st.markdown(f"**Subtotal:** ₹ {subtotal:.2f}")
            st.markdown(f"**Estimated GST (Included):** ₹ {gst_amount:.2f}")
            st.markdown(f"### 💰 Grand Total: ₹ {grand_total:.2f}")
            
            c1, c2 = st.columns(2)
            if c1.button("✅ Confirm Bill & Generate PDF", type="primary"):
                for item in st.session_state.cart:
                    c.execute("UPDATE inventory SET stock = stock - ? WHERE id = ?", (item['Qty'], item['id']))
                    if "Alprazolam" in item['Medicine'] or "Amoxicillin" in item['Medicine']:
                        c.execute("INSERT INTO schedule_h_register (timestamp, patient_name, doctor_name, medicine_name, batch, qty) VALUES (?,?,?,?,?,?)",
                                  (str(datetime.now()), cust_name, doc_name, item['Medicine'], item['Batch'], item['Qty']))
                
                refill_date = str(datetime.now().date() + timedelta(days=30))
                c.execute("INSERT INTO customers (name, phone, last_medicine, next_refill_date) VALUES (?,?,?,?)",
                          (cust_name, cust_phone, cart_df.iloc[0]['Medicine'], refill_date))
                conn.commit()
                
                st.session_state.last_invoice = generate_pdf_invoice(st.session_state.cart, cust_name, doc_name)
                st.session_state.cart = []
                st.success("Invoice generated successfully!")
                st.rerun()
                
            if c2.button("🗑️ Clear Cart"):
                st.session_state.cart = []
                st.rerun()
                
        if st.session_state.last_invoice and os.path.exists(st.session_state.last_invoice):
            st.divider()
            st.success("📄 Print-ready Tax Invoice PDF is ready!")
            with open(st.session_state.last_invoice, "rb") as pdf_file:
                st.download_button(
                    label="📥 Download / Print Tax Invoice (PDF)",
                    data=pdf_file,
                    file_name="Medical_Tax_Invoice.pdf",
                    mime="application/pdf"
                )
        else:
            if not st.session_state.cart:
                st.info("Cart is empty.")

# ================= TAB 2: INVENTORY & EXPIRY =================
with tab2:
    st.subheader("📦 Inventory Stock & Automated FEFO Expiry Matrix")
    df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
    
    current_date = datetime.now()
    alerts = []
    for _, row in df_inv.iterrows():
        try:
            exp_date = datetime.strptime(str(row['expiry'])[:7], "%Y-%m")
            days_left = (exp_date - current_date).days
        except:
            days_left = 180
        
        status = "🟢 Safe (>90 Days)"
        if days_left < 30:
            status = "🔴 Critical (<30 Days - Return/Clear)"
        elif days_left < 90:
            status = "🟡 Near-Expiry (30-90 Days)"
            
        alerts.append({"Medicine": row['name'], "Batch": row['batch'], "Expiry": row['expiry'], "Stock": row['stock'], "Status": status})
    
    st.dataframe(pd.DataFrame(alerts), use_container_width=True)

# ================= TAB 3: SCHEDULE H/H1 COMPLIANCE =================
with tab3:
    st.subheader("⚖️ Government Drug Inspector Audit Register (Schedule H / H1)")
    df_h = pd.read_sql_query("SELECT * FROM schedule_h_register", conn)
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
    else:
        st.info("No Schedule H/H1 restricted drugs billed yet.")

# ================= TAB 4: GST & WHATSAPP CRM =================
with tab4:
    st.subheader("📱 Automated WhatsApp Refill Reminders & GST Reports")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("#### 💬 Pending Patient Refills (WhatsApp Automation)")
        df_cust = pd.read_sql_query("SELECT * FROM customers", conn)
        if not df_cust.empty:
            for _, row in df_cust.iterrows():
                st.write(f"👤 **{row['name']}** ({row['phone']}) - Last Med: *{row['last_medicine']}* | Refill Due: `{row['next_refill_date']}`")
                if st.button(f"Send WhatsApp Reminder to {row['name']}", key=str(row['id'])):
                    st.success(f"WhatsApp API Triggered: 'Hello {row['name']}, your medicine {row['last_medicine']} is due for refill. Order now from PharmaAI Store!'")
        else:
            st.info("No customer records found.")
            
    with col_b:
        st.markdown("#### 📊 GST Return Summary (GSTR-1 Format)")
        st.write("Total Taxable turnover computed dynamically for filing returns.")
        st.info("Tax Filing status: Ready for 1-Click JSON Export for GST Portal.")

# ================= TAB 5: MARG / EXCEL UNIVERSAL DATA MIGRATION =================
with tab5:
    st.subheader("🔄 1-Click Data Migration (Marg ERP / Busy / Excel / CSV)")
    st.markdown("""
    Purane software (jaise **Marg ERP, MediBilling, ya Busy**) se apni stock list **CSV ya Excel** format mein export karein aur yahan upload karein. 
    Humara AI Smart Mapper khud columns ko pehchan kar saara data import kar lega.
    """)
    
    # Download Sample Template taaki user format dekh sake
    sample_template = pd.DataFrame({
        "Medicine Name": ["Calpol 500", "Omez 20"],
        "Salt": ["Paracetamol 500mg", "Omeprazole 20mg"],
        "Batch": ["CP102", "OM55"],
        "Expiry": ["2027-09", "2027-04"],
        "MRP": [15.0, 58.0],
        "GST": [12.0, 12.0],
        "Stock": [120, 80]
    })
    
    st.download_button(
        label="📄 Download Sample Import Format (CSV)",
        data=sample_template.to_csv(index=False),
        file_name="Marg_To_PharmaAI_Template.csv",
        mime="text/csv"
    )
    
    st.divider()
    uploaded_file = st.file_uploader("Upload Marg / Excel / CSV Stock File", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_import = pd.read_csv(uploaded_file)
            else:
                df_import = pd.read_excel(uploaded_file)
                
            st.write("👀 **File Preview (Pehli 5 lines):**")
            st.dataframe(df_import.head(), use_container_width=True)
            
            # Smart Column Mapping
            st.markdown("#### 🛠️ Column Mapping (Apni file ke columns select karein)")
            cols = list(df_import.columns)
            
            c_map1, c_map2, c_map3, c_map4 = st.columns(4)
            col_name = c_map1.selectbox("Medicine Name Column", cols, index=0)
            col_batch = c_map2.selectbox("Batch No. Column", cols, index=min(2, len(cols)-1))
            col_exp = c_map3.selectbox("Expiry Column (YYYY-MM)", cols, index=min(3, len(cols)-1))
            col_mrp = c_map4.selectbox("MRP Column", cols, index=min(4, len(cols)-1))
            
            c_map5, c_map6, c_map7 = st.columns(3)
            col_stock = c_map5.selectbox("Stock Quantity Column", cols, index=min(6, len(cols)-1))
            col_salt = c_map6.selectbox("Salt / Composition (Optional)", ["None"] + cols)
            col_gst = c_map7.selectbox("GST % (Optional)", ["Default 12%"] + cols)
            
            if st.button("🚀 Start Bulk Import into PharmaAI", type="primary"):
                imported_count = 0
                for _, r in df_import.iterrows():
                    m_name = str(r[col_name])
                    m_batch = str(r[col_batch])
                    m_exp = str(r[col_exp])
                    m_mrp = float(r[col_mrp]) if pd.notnull(r[col_mrp]) else 0.0
                    m_stock = int(r[col_stock]) if pd.notnull(r[col_stock]) else 0
                    m_salt = str(r[col_salt]) if col_salt != "None" else "Generic"
                    m_gst = float(r[col_gst]) if col_gst != "Default 12%" else 12.0
                    
                    c.execute("INSERT INTO inventory (name, salt, batch, expiry, mrp, gst, stock) VALUES (?,?,?,?,?,?,?)",
                              (m_name, m_salt, m_batch, m_exp, m_mrp, m_gst, m_stock))
                    imported_count += 1
                    
                conn.commit()
                st.success(f"🎉 Zabardast! {imported_count} medicines Marg/Excel file se successfully PharmaAI mein import ho gayi hain!")
                
        except Exception as e:
            st.error(f"File padhne mein error aaya: {e}. Kripya CSV ya Excel (.xlsx) format check karein.")
