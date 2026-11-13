import streamlit as st
import pandas as pd
from datetime import datetime

# Page Configuration
st.set_page_config(
    page_title="PharmaAI Pro - Advanced Pharmacy System",
    page_icon="💊",
    layout="wide",
)

# Custom CSS for Professional ERP Look
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1f2937; color: white; border-radius: 5px; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #3b82f6 !important; color: white !important; }
    </style>
""",
    unsafe_allow_html=True,
)

# Initialize Session State for Permanent-like Session Memory & Cart
if "inventory" not in st.session_state:
    st.session_state.inventory = pd.DataFrame([
        {
            "id": 1,
            "name": "Dolo 650",
            "salt": "Paracetamol 650mg",
            "batch": "DL650-24",
            "expiry": "2027-08",
            "stock": 150,
            "mrp": 30.0,
            "gst": 12,
        },
        {
            "id": 2,
            "name": "Pan-D",
            "salt": "Pantoprazole + Domperidone",
            "batch": "PND-99",
            "expiry": "2026-12",
            "stock": 80,
            "mrp": 115.0,
            "gst": 12,
        },
        {
            "id": 3,
            "name": "Alprazolam 0.5mg",
            "salt": "Alprazolam (Schedule H1)",
            "batch": "ALP-05",
            "expiry": "2028-01",
            "stock": 40,
            "mrp": 45.0,
            "gst": 18,
        },
        {
            "id": 4,
            "name": "Augmentin 625",
            "salt": "Amoxicillin + Clavulanic Acid",
            "batch": "AUG-62",
            "expiry": "2026-06",
            "stock": 60,
            "mrp": 204.0,
            "gst": 12,
        },
    ])

if "cart" not in st.session_state:
    st.session_state.cart = []

if "sales_history" not in st.session_state:
    st.session_state.sales_history = []

# App Header
st.title("💊 PharmaAI Pro — Enterprise Pharmacy & ERP System")
st.markdown(
    "*Professional grade inventory management, smart AI billing, schedule H1"
    " tracking, and tax invoicing.*"
)

# Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "⚡ Smart Billing & POS",
    "📦 Inventory & Stock",
    "🚨 Expiry & Schedule H1",
    "📊 Reports & GST",
])

# ----------------- TAB 1: SMART BILLING & POS -----------------
with tab1:
  st.subheader("🛒 Point of Sale (POS) & Invoice Counter")

  col1, col2 = st.columns([2, 1])

  with col1:
    search_query = st.selectbox(
        "Search or Select Medicine from Catalog",
        st.session_state.inventory["name"].tolist(),
    )
    selected_med = st.session_state.inventory[
        st.session_state.inventory["name"] == search_query
    ].iloc[0]

    st.info(
        f"**Available Stock:** {selected_med['stock']} units | **MRP:**"
        f" ₹{selected_med['mrp']} | **Batch:** {selected_med['batch']}"
    )

    qty = st.number_input("Quantity", min_value=1, max_value=int(selected_med['stock']), value=1)
    
    if st.button("➕ Add to Cart"):
      item_total = qty * selected_med["mrp"]
      st.session_state.cart.append({
          "name": selected_med["name"],
          "batch": selected_med["batch"],
          "qty": qty,
          "price": selected_med["mrp"],
          "total": item_total,
          "gst": selected_med["gst"],
      })
      st.success(f"Added {qty}x {selected_med['name']} to cart!")

  with col2:
    st.markdown("### 🧾 Current Cart Summary")
    if len(st.session_state.cart) > 0:
      cart_df = pd.DataFrame(st.session_state.cart)
      st.dataframe(cart_df[["name", "qty", "total"]], hide_index=True)

      subtotal = cart_df["total"].sum()
      discount = st.number_input("Discount (%)", 0.0, 50.0, 0.0)
      final_amount = subtotal - (subtotal * discount / 100)

      st.markdown(f"### **Grand Total: ₹{final_amount:.2f}**")

      patient_name = st.text_input("Patient Name", "Rahul Sharma")
      doctor_name = st.text_input("Prescribing Doctor", "Dr. V. K. Verma")

      if st.button("🖨️ Generate Invoice & Complete Sale"):
        invoice_data = {
            "invoice_id": f"INV-{int(datetime.now().timestamp())}",
            "patient": patient_name,
            "doctor": doctor_name,
            "total": final_amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "items": st.session_state.cart.copy(),
        }
        st.session_state.sales_history.append(invoice_data)

        # Deduct Stock
        for item in st.session_state.cart:
          st.session_state.inventory.loc[
              st.session_state.inventory["name"] == item["name"], "stock"
          ] -= item["qty"]

        st.success(
            f"✅ Invoice Generated Successfully! ID:"
            f" {invoice_data['invoice_id']}"
        )
        st.session_state.cart = []  # Clear cart
    else:
      st.warning("Cart is empty.")

# ----------------- TAB 2: INVENTORY & STOCK -----------------
with tab2:
  st.subheader("📦 Live Inventory Database & Stock Management")
  st.dataframe(st.session_state.inventory, use_container_width=True)

  with st.expander("➕ Add New Medicine to Stock"):
    with st.form("add_stock_form"):
      new_name = st.text_input("Medicine Name")
      new_salt = st.text_input("Salt / Composition")
      new_batch = st.text_input("Batch Number")
      new_expiry = st.text_input("Expiry Date (YYYY-MM)", "2027-12")
      new_stock = st.number_input("Stock Quantity", min_value=1, value=100)
      new_mrp = st.number_input("MRP (₹)", min_value=1.0, value=50.0)
      new_gst = st.selectbox("GST %", [0, 5, 12, 18], index=2)

      submitted = st.form_submit_button("Save to Inventory")
      if submitted:
        new_row = {
            "id": len(st.session_state.inventory) + 1,
            "name": new_name,
            "salt": new_salt,
            "batch": new_batch,
            "expiry": new_expiry,
            "stock": new_stock,
            "mrp": new_mrp,
            "gst": new_gst,
        }
        st.session_state.inventory = pd.concat(
            [st.session_state.inventory, pd.DataFrame([new_row])],
            ignore_index=True,
        )
        st.success(f"Medicine {new_name} added successfully!")

# ----------------- TAB 3: EXPIRY & SCHEDULE H1 -----------------
with tab3:
  st.subheader("🚨 Expiry Risk & Schedule H1 Compliance Tracker")

  col1, col2 = st.columns(2)
  with col1:
    st.markdown("#### ⚠️ Near Expiry / Expired Stock Alert")
    # Simple check for demo
    expired_items = st.session_state.inventory[
        st.session_state.inventory["expiry"] <= "2026-11"
    ]
    if not expired_items.empty:
      st.error(
          "Following items require immediate return/disposal due to expiry date"
          " proximity:"
      )
      st.dataframe(expired_items[["name", "batch", "expiry"]], hide_index=True)
    else:
      st.success("No critical expiry alerts found for current month.")

  with col2:
    st.markdown("#### 📑 Schedule H1 Narcotic / Habit-Forming Registry")
    h1_items = st.session_state.inventory[
        st.session_state.inventory["salt"].str.contains(
            "Schedule H1|Alprazolam", case=False, na=False
        )
    ]
    st.dataframe(h1_items[["name", "salt", "stock"]], hide_index=True)
    st.info(
        "Note: As per Pharmacy Act, maintaining patient ID & doctor prescription"
        " records for Schedule H1 drugs is mandatory."
    )

# ----------------- TAB 4: REPORTS & GST -----------------
with tab4:
  st.subheader("📊 Sales Reports & Tax Invoicing")
  if len(st.session_state.sales_history) > 0:
    sales_df = pd.DataFrame([
        {
            "Invoice ID": s["invoice_id"],
            "Patient": s["patient"],
            "Doctor": s["doctor"],
            "Total Amount (₹)": s["total"],
            "Date/Time": s["date"],
        }
        for s in st.session_state.sales_history
    ])
    st.dataframe(sales_df, use_container_width=True)

    # Download button for Excel/CSV format
    csv = sales_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Sales Report (CSV)",
        data=csv,
        file_name="pharma_sales_report.csv",
        mime="text/csv",
    )
  else:
    st.info(
        "No sales recorded yet. Generate an invoice from the Smart Billing tab"
        " to view reports."
    )
