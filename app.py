import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Set page configuration
st.set_page_config(
    page_title="Olist E-commerce Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS for styling ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .metric-title {
        color: #555;
        font-size: 14px;
        font-weight: bold;
    }
    .metric-value {
        color: #000;
        font-size: 24px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data
def load_data():
    """Loads and preprocesses data from CSV files."""
    try:
        # Define file paths (assuming they are in the same directory or adjust logic)
        path = "." 
        
        # Load Datasets
        orders = pd.read_csv(os.path.join(path, "olist_orders_dataset.csv"))
        items = pd.read_csv(os.path.join(path, "olist_order_items_dataset.csv"))
        products = pd.read_csv(os.path.join(path, "olist_products_dataset.csv"))
        payments = pd.read_csv(os.path.join(path, "olist_order_payments_dataset.csv"))
        reviews = pd.read_csv(os.path.join(path, "olist_order_reviews_dataset.csv"))
        customers = pd.read_csv(os.path.join(path, "olist_customers_dataset.csv"))
        sellers = pd.read_csv(os.path.join(path, "olist_sellers_dataset.csv"))
        geolocation = pd.read_csv(os.path.join(path, "olist_geolocation_dataset.csv"))
        category_translation = pd.read_csv(os.path.join(path, "product_category_name_translation.csv"))

        # --- Data Cleaning & Merging ---
        
        # 1. Date Conversions
        date_cols = ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date', 
                     'order_delivered_customer_date', 'order_estimated_delivery_date']
        for col in date_cols:
            orders[col] = pd.to_datetime(orders[col])
            
        reviews['review_creation_date'] = pd.to_datetime(reviews['review_creation_date'])
        reviews['review_answer_timestamp'] = pd.to_datetime(reviews['review_answer_timestamp'])

        # 2. Merge Product Category Translation
        products = products.merge(category_translation, on='product_category_name', how='left')
        products['product_category_name_english'] = products['product_category_name_english'].fillna(products['product_category_name'])

        # 3. Create a Master DataFrame (Orders + Items + Products + Customers)
        # We start with items to get product text, then join orders for time info, then customers.
        
        # Merge Orders and Items
        order_items = orders.merge(items, on='order_id', how='left')
        
        # Merge with Products
        master_df = order_items.merge(products, on='product_id', how='left')
        
        # Merge with Customers (to get location)
        master_df = master_df.merge(customers, on='customer_id', how='left')
        
        # Merge with Payments (Aggregated by order to avoid duplication rows for master if one order has multiple payments? 
        # Actually payments can be 1:N with orders. For specific analysis we might need separate df)
        # For Master DF involving product sales, we stick to line items.
        
        # Add basic time columns
        master_df['month_year'] = master_df['order_purchase_timestamp'].dt.to_period('M')
        master_df['year'] = master_df['order_purchase_timestamp'].dt.year
        master_df['day_of_week'] = master_df['order_purchase_timestamp'].dt.day_name()
        master_df['hour'] = master_df['order_purchase_timestamp'].dt.hour
        
        return {
            "orders": orders,
            "items": items,
            "master_df": master_df,
            "reviews": reviews,
            "payments": payments,
            "sellers": sellers,
            "products": products
        }

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

data = load_data()

if data is None:
    st.stop()

master_df = data["master_df"]
orders = data["orders"]
reviews = data["reviews"]

# --- Sidebar Controls ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Overview", "Sales Analysis", "Product Insights", "Customer Demographics", "Review Analysis", "Payment Analysis", "Delivery Analysis"])

st.sidebar.markdown("---")
st.sidebar.header("Filters")

# Date Filter
min_date = master_df['order_purchase_timestamp'].min().date()
max_date = master_df['order_purchase_timestamp'].max().date()

start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Filter Data based on selection
# Ensure start_date and end_date are converted to pd.Timestamp for comparison
filtered_df = master_df[
    (master_df['order_purchase_timestamp'].dt.date >= start_date) & 
    (master_df['order_purchase_timestamp'].dt.date <= end_date)
]

filtered_orders = orders[
    (orders['order_purchase_timestamp'].dt.date >= start_date) & 
    (orders['order_purchase_timestamp'].dt.date <= end_date)
]

# --- Page: Overview ---
if page == "Overview":
    st.title("📊 Executive Overview")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    total_revenue = filtered_df['price'].sum()
    total_orders = filtered_orders['order_id'].nunique()
    if total_orders > 0:
        avg_order_value = total_revenue / total_orders
    else:
        avg_order_value = 0
        
    avg_delivery_days = (filtered_orders['order_delivered_customer_date'] - filtered_orders['order_purchase_timestamp']).dt.days.mean()
    
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Total Revenue</div><div class="metric-value">R$ {total_revenue:,.2f}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Total Orders</div><div class="metric-value">{total_orders:,}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Avg Order Value</div><div class="metric-value">R$ {avg_order_value:,.2f}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-title">Avg Delivery Time</div><div class="metric-value">{avg_delivery_days:.1f} days</div></div>', unsafe_allow_html=True)
        
    # Sales Trend Line Chart
    st.subheader("Revenue Over Time")
    sales_over_time = filtered_df.groupby(filtered_df['order_purchase_timestamp'].dt.to_period('M'))['price'].sum().reset_index()
    sales_over_time['order_purchase_timestamp'] = sales_over_time['order_purchase_timestamp'].astype(str)
    
    fig_line = px.line(sales_over_time, x='order_purchase_timestamp', y='price', markers=True, 
                       labels={'price': 'Revenue (R$)', 'order_purchase_timestamp': 'Month'},
                       template="plotly_white")
    st.plotly_chart(fig_line, use_container_width=True)

# --- Page: Sales Analysis ---
elif page == "Sales Analysis":
    st.title("📈 Sales Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sales by Day of Week")
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        sales_by_day = filtered_df.groupby('day_of_week')['price'].sum().reindex(day_order).reset_index()
        fig_day = px.bar(sales_by_day, x='day_of_week', y='price', 
                         title="Revenue by Day of Week",
                         color_discrete_sequence=['#3366CC'],
                         labels={'price': 'Revenue', 'day_of_week': 'Day'})
        st.plotly_chart(fig_day, use_container_width=True)
        
    with col2:
        st.subheader("Sales by Time of Day")
        sales_by_hour = filtered_df.groupby('hour')['price'].sum().reset_index()
        fig_hour = px.line(sales_by_hour, x='hour', y='price', 
                           title="Revenue by Hour",
                           markers=True)
        st.plotly_chart(fig_hour, use_container_width=True)

# --- Page: Product Insights ---
elif page == "Product Insights":
    st.title("🛍️ Product Insights")
    
    # Top Categories
    st.subheader("Top Product Categories")
    top_n = st.slider("Select Number of Top Categories", 5, 20, 10)
    
    category_sales = filtered_df.groupby('product_category_name_english')['price'].sum().sort_values(ascending=False).head(top_n).reset_index()
    
    fig_prod = px.bar(category_sales, y='product_category_name_english', x='price', orientation='h',
                      title=f"Top {top_n} Categories by Revenue",
                      color='price',
                      color_continuous_scale='Viridis')
    fig_prod.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_prod, use_container_width=True)
    
    # Expensive vs Cheap
    st.subheader("Price Distribution")
    fig_hist = px.histogram(filtered_df, x='price', nbins=100, title="Distribution of Product Prices", range_x=[0, 500])
    st.plotly_chart(fig_hist, use_container_width=True)

# --- Page: Customer Demographics ---
elif page == "Customer Demographics":
    st.title("👥 Customer Demographics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top States by Orders")
        state_counts = filtered_df['customer_state'].value_counts().head(10).reset_index()
        state_counts.columns = ['State', 'Orders']
        fig_state = px.bar(state_counts, x='State', y='Orders', color='Orders', title="Top 10 States")
        st.plotly_chart(fig_state, use_container_width=True)
        
    with col2:
        st.subheader("Top Cities by Orders")
        city_counts = filtered_df['customer_city'].value_counts().head(10).reset_index()
        city_counts.columns = ['City', 'Orders']
        fig_city = px.bar(city_counts, x='City', y='Orders', title="Top 10 Cities")
        st.plotly_chart(fig_city, use_container_width=True)

# --- Page: Review Analysis ---
elif page == "Review Analysis":
    st.title("⭐ Review Analysis")
    
    # Review Score Distribution
    st.subheader("Review Score Distribution")
    # Need to link reviews to filtered orders if we want date filtering to apply strictly to purchase date, 
    # but reviews have their own dates. Simpler to filter reviews that link to the filtered orders.
    
    # Get order_ids from filtered_orders
    relevant_order_ids = filtered_orders['order_id']
    relevant_reviews = reviews[reviews['order_id'].isin(relevant_order_ids)]
    
    review_dist = relevant_reviews['review_score'].value_counts().sort_index().reset_index()
    review_dist.columns = ['Score', 'Count']
    
    fig_pie = px.pie(review_dist, values='Count', names='Score', 
                     title="Distribution of Review Scores",
                     color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Delivery Time vs Review
    st.subheader("Delivery Time vs Review Score")
    # Join reviews with orders to get delivery time
    reviews_orders = relevant_reviews.merge(filtered_orders, on='order_id')
    reviews_orders['delivery_days'] = (reviews_orders['order_delivered_customer_date'] - reviews_orders['order_purchase_timestamp']).dt.days
    
    # Filter out outliers for clearer plot
    reviews_orders = reviews_orders[reviews_orders['delivery_days'] < 50]
    
    fig_box = px.box(reviews_orders, x='review_score', y='delivery_days', 
                     title="Delivery Time Distribution by Review Score",
                     labels={'review_score': 'Stars', 'delivery_days': 'Days to Deliver'},
                     color='review_score')
    st.plotly_chart(fig_box, use_container_width=True)

# --- Page: Payment Analysis ---
elif page == "Payment Analysis":
    st.title("💳 Payment Analysis")
    
    payments = data["payments"]
    relevant_order_ids = filtered_orders['order_id']
    relevant_payments = payments[payments['order_id'].isin(relevant_order_ids)]

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Payment Method Distribution")
        payment_counts = relevant_payments['payment_type'].value_counts().reset_index()
        payment_counts.columns = ['Payment Type', 'Count']
        
        fig_pay_pie = px.pie(payment_counts, values='Count', names='Payment Type', 
                             title="Orders by Payment Type",
                             hole=0.4)
        st.plotly_chart(fig_pay_pie, use_container_width=True)
        
    with col2:
        st.subheader("Installments Distribution")
        # Filter out 0 or 1 installments for clarity if dominance is high? No, show all.
        fig_install = px.histogram(relevant_payments, x='payment_installments', 
                                   title="Distribution of Installments",
                                   nbins=24)
        st.plotly_chart(fig_install, use_container_width=True)
        
    st.subheader("Payment Value by Type")
    # Filter outliers for visualization
    safe_payments = relevant_payments[relevant_payments['payment_value'] < 1000]
    fig_pay_box = px.box(safe_payments, x='payment_type', y='payment_value', 
                         title="Payment Value Distribution by Type (Values < R$1000)",
                         color='payment_type')
    st.plotly_chart(fig_pay_box, use_container_width=True)

# --- Page: Delivery Analysis ---
elif page == "Delivery Analysis":
    st.title("🚚 Delivery Analysis")
    
    # Use filtered_orders for delivery time
    df_delivery = filtered_orders.copy()
    df_delivery['delivery_days'] = (df_delivery['order_delivered_customer_date'] - df_delivery['order_purchase_timestamp']).dt.days
    df_delivery = df_delivery.dropna(subset=['delivery_days'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Delivery Time Distribution")
        fig_del_hist = px.histogram(df_delivery, x='delivery_days', 
                                    nbins=50, 
                                    title="Days to Deliver",
                                    range_x=[0, 50])
        st.plotly_chart(fig_del_hist, use_container_width=True)
        
    with col2:
        st.subheader("Freight Cost vs Product Weight")
        # Need items with weights
        items = data["items"]
        products = data["products"] # products has weight
        
        # Merge items with products to get weight
        items_products = items.merge(products[['product_id', 'product_weight_g']], on='product_id', how='left')
        
        # Filter for current orders
        relevant_items = items_products[items_products['order_id'].isin(filtered_orders['order_id'])]
        
        # Sample if too large to avoid slow plotting
        if len(relevant_items) > 5000:
            plot_data = relevant_items.sample(5000)
        else:
            plot_data = relevant_items
            
        fig_scat = px.scatter(plot_data, x='product_weight_g', y='freight_value', 
                              title="Freight Value vs Product Weight (Sampled)",
                              opacity=0.5)
        st.plotly_chart(fig_scat, use_container_width=True)
        
    st.subheader("Average Freight Value by State")
    # Master DF has state and freight (embedded in price? No, freight is in items)
    # Actually master_df merged orders, items, products, customers.
    # It has 'freight_value' and 'customer_state'.
    
    state_freight = filtered_df.groupby('customer_state')['freight_value'].mean().sort_values(ascending=False).reset_index()
    
    fig_state_freight = px.bar(state_freight, x='customer_state', y='freight_value',
                               title="Average Freight Cost by Customer State",
                               color='freight_value')
    st.plotly_chart(fig_state_freight, use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown("Created with ❤️ using Streamlit")
