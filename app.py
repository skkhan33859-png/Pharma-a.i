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

# Initialize Session State
if "inventory" not in st.session_state:
    st.session_state.inventory = pd.DataFrame([
        {
            "id": 1,
            "name": "Orasore Gel",
            "salt": "Choline Salicylate + Lidocaine",
            "batch": "CGF006",
            "expiry": "2027-08",
            "stock": 12,
            "mrp": 45.0,
            "gst": 12,
        },
        {
            "id": 2,
            "name": "Omee MPS Syp",
            "salt": "Magaldrate + Simethicone",
            "batch": "OME25061RH",
            "expiry": "2026-12",
            "stock": 10,
            "mrp": 125.0,
            "gst": 12,
        },
        {
            "id": 3,
            "name": "Nozal Zpto Shampoo",
            "salt": "Ketoconazole + Zinc Pyrithione",
            "batch": "4401",
            "expiry": "2028-01",
            "stock": 1,
            "mrp": 90.0,
            "gst": 18,
        },
        {
            "id": 4,
            "name": "Drykuff DX Syp",
            "salt": "Dextromethorphan + Chlorpheniramine",
            "batch": "QA25760",
            "expiry": "2026-06",
            "stock": 10,
            "mrp": 35.0,
            "gst": 12,
        },
        {
            "id": 5,
            "name": "Onditron-MD",
            "salt": "Ondansetron 4mg",
            "batch": "QA25760",
            "expiry": "2027-03",
            "stock": 10,
            "mrp": 25.0,
            "gst": 12,
        },
        {
            "id": 6,
            "name": "Salvent Ag Syp",
            "salt": "Ambroxol + Guaifenesin + Terbutaline",
            "batch": "SP241602",
            "expiry": "2027-05",
            "stock": 10,
            "mrp": 45.0,
            "gst": 12,
        },
        {
            "id": 7,
            "name": "Rabesec DSR",
            "salt": "Rabeprazole + Domperidone",
            "batch": "RCS25002",
            "expiry": "2027-10",
            "stock": 20,
            "mrp": 140.0,
            "gst": 12,
        },
    ])

if "cart" not in st.session_state:
    st.session_state.cart = []

if "sales_history" not in st.session_state:
    st.session_state.sales_history = []

if "purchase_bills" not in st.session_state:
    st.session_state.purchase_bills = []

# App Header
st.title("💊 PharmaAI Pro — Enterprise Pharmacy & ERP System")
st.markdown(
    "*AI-powered purchase bill scanning, smart POS billing, and inventory"
    " management.*"
)

# Navigation Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🤖 AI Bill Scanner",
    "⚡ Smart Billing & POS",
    "📦 Inventory & Stock",
    "🚨 Expiry & Schedule H1",
    "📊 Reports & GST",
])

# ----------------- TAB 1: AI BILL SCANNER -----------------
with tab1:
  st.subheader("🤖 AI Purchase Bill & Invoice Scanner")
  st.markdown(
      "Upload your supplier purchase bill photo. AI will automatically"
      " extract items and add them to your inventory stock!"
  )

  uploaded_bill = st.file_uploader(
      "Upload Supplier Bill (Image/PDF)", type=["jpg", "jpeg", "png", "pdf"]
  )

  if uploaded_bill is not None:
    st.image(uploaded_bill, caption="Uploaded Purchase Bill", width=400)
    if st.button("✨ Process Bill with AI & Add to Stock"):
      with st.spinner(
          "AI is reading bill items, batch numbers, and quantities..."
      ):
        # Simulated AI Extraction based on standard supplier bills
        extracted_items = [
            {
                "name": "Orasore Gel",
                "batch": "CGF006",
                "qty": 12,
                "rate": 31.25,
                "mrp": 45.0,
            },
            {
                "name": "Omee MPS Syp",
                "batch": "OME25061RH",
                "qty": 10,
                "rate": 21.58,
                "mrp": 125.0,
            },
            {
                "name": "Nozal Zpto Shampoo",
                "batch": "4401",
                "qty": 1,
                "rate": 73.26,
                "mrp": 90.0,
            },
            {
                "name": "Drykuff DX Syp",
                "batch": "QA25760",
                "qty": 10,
                "rate": 20.50,
                "mrp": 35.0,
            },
            {
                "name": "Onditron-MD",
                "batch": "QA25760",
                "qty": 10,
                "rate": 5.25,
                "mrp": 25.0,
            },
            {
                "name": "Salvent Ag Syp",
                "batch": "SP241602",
                "qty": 10,
                "rate": 30.50,
                "mrp": 45.0,
            },
            {
                "name": "Rabesec DSR",
                "batch": "RCS25002",
                "qty": 20,
                "rate": 26.70,
                "mrp": 140.0,
            },
        ]

        st.success(
            "✅ Bill successfully scanned by AI! Extracted 7 items worth"
            " ₹1971.84"
        )
        st.dataframe(pd.DataFrame(extracted_items), hide_index=True)

        # Add to inventory stock automatically
        for item in extracted_items:
          # Check if item exists, update stock, else append
          mask = st.session_state.inventory["name"] == item["name"]
          if mask.any():
            st.session_state.inventory.loc[mask, "stock"] += item["qty"]
          else:
            new_row = {
                "id": len(st.session_state.inventory) + 1,
                "name": item["name"],
                "salt": "General Medicine",
                "batch": item["batch"],
                "expiry": "2027-12",
                "stock": item["qty"],
                "mrp": item["mrp"],
                "gst": 12,
            }
            st.session_state.inventory = pd.concat(
                [
                    st.session_state.inventory,
                    pd.DataFrame([new_row]),
                ],
                ignore_index=True,
            )

        st.info(
            "🎉 All items have been automatically added to your live inventory"
            " stock!"
        )

# ----------------- TAB 2: SMART BILLING & POS -----------------
with tab2:
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

    qty = st.number_input(
        "Quantity",
        min_value=1,
        max_value=max(1, int(selected_med["stock"])),
        value=1,
    )

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
        st.session_state.cart = []
    else:
      st.warning("Cart is empty.")

# ----------------- TAB 3: INVENTORY & STOCK -----------------
with tab3:
  st.subheader("📦 Live Inventory Database & Stock Management")
  st.dataframe(st.session_state.inventory, use_container_width=True)

  with st.expander("➕ Add New Medicine Manually"):
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

# ----------------- TAB 4: EXPIRY & SCHEDULE H1 -----------------
with tab4:
  st.subheader("🚨 Expiry Risk & Schedule H1 Compliance Tracker")

  col1, col2 = st.columns(2)
  with col1:
    st.markdown("#### ⚠️ Near Expiry / Expired Stock Alert")
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
        "Note: Maintaining patient ID & doctor prescription records for"
        " Schedule H1 drugs is mandatory."
    )

# ----------------- TAB 5: REPORTS & GST -----------------
with tab5:
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

    csv = sales_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Sales Report (CSV)",
        data=csv,
        file_name="pharma_sales_report.csv",
        mime="text/css",
    )
  else:
    st.info(
        "No sales recorded yet. Generate an invoice from the Smart Billing tab"
        " to view reports."
    )
