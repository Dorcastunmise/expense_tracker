import sqlite3
import streamlit as st
from datetime import datetime
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

DB_NAME = "expenses.db"
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Database connection
def get_conn():
  #I'm setting check_same_thread to False to allow multiple threads to access the database connection. This is necessary for Streamlit apps, which can run in a multi-threaded environment.
  return sqlite3.connect(DB_NAME, check_same_thread=False)

#Database table creation
def init_db():
    with get_conn() as conn:
      conn.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
      ''')
    conn.commit()
    conn.close()

# Expense insertion
def insert_expense(note, category, amount, created_at):
    with get_conn() as conn:
      conn.execute('''
          INSERT INTO expenses (note, category, amount, created_at)
          VALUES (?, ?, ?, ?)
      ''', (note, category, amount, created_at))
    conn.commit()
    conn.close()

# Expense deletion/removal
def delete_expense(expense_id):
    with get_conn() as conn:
      conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()

# Expense retrieval
def get_expenses():
  with get_conn() as conn:
    #pandas read_sql_query is used to execute the SQL query and return the result as a DataFrame. The fetchall() method I called is applied on the DataFrame to retrieve all rows of the result set as a list of tuples.
    exp_dataframe = pd.read_sql_query('SELECT * FROM expenses ORDER BY created_at DESC', conn)

    exp_dataframe['created_at'] = pd.to_datetime(exp_dataframe['created_at'])
    exp_dataframe['month'] = exp_dataframe['created_at'].dt.to_period('M').astype(str)

  return exp_dataframe

#Charts & visualizations
def monthly_trend_chart(mthly_total:pd.DataFrame):
  fig=plt.figure(figsize=(8, 4))
  plt.plot(mthly_total['month'], mthly_total['amount'], marker='o')
  plt.title('Monthly Expense Trend')
  plt.xlabel('Month')
  plt.ylabel('Total Amount')
  plt.xticks(rotation=45)
  plt.tight_layout()
  return fig

def category_bar_chart(category_total:pd.DataFrame, top_n=6):
  fig=plt.figure(figsize=(8, 4))
  top_categories = category_total.head(top_n)
  plt.bar(top_categories['category'], top_categories['amount'], color='skyblue')
  plt.title('Top Expense Categories')
  plt.xlabel('Category')
  plt.ylabel('Total Amount')
  plt.xticks(rotation=45)
  plt.tight_layout()
  return fig

#streamlit ui
st.set_page_config(page_title="Expense Tracker Dashboard", layout="wide")
init_db()
st.title("Expense Tracker Dashboard")

#sidebar
st.sidebar.header("Add New Expense")
amount = st.sidebar.number_input("Amount", min_value=0.01, step=0.01, format="%.2f")
category = st.sidebar.selectbox("Category", ["Delicacies", "Shopping", "Travel", "Entertainment", "Health", "Others"])
note = st.sidebar.text_input("Note(optional)")#note is optional, so it can be left blank because the user may not want to add a note for every expense.
expense_at = st.sidebar.date_input("Date", datetime.now())
expense_time = st.sidebar.time_input("Time")
created_at = datetime.combine(expense_at, expense_time).strftime("%Y-%m-%d %H:%M:%S")

if st.sidebar.button("Add Expense"):
  if amount > 0:
    insert_expense(note, category, amount, created_at)
    st.sidebar.success("Expense added successfully!")

    st.rerun() # I'm doing this to refresh the app to show the updated expenses
  else:
    st.sidebar.error("Amount must be greater than zero(0).")

st.sidebar.markdown("## Expense Records")
st.sidebar.info("Note: Add a few expenses to see the charts and visualizations.")

#main data
data_frm = get_expenses()

if data_frm.empty:
  st.error("No expenses recorded yet. Please add an expense before viewing the dashboard.")
  st.stop()

st.subheader("All Expenses")
col1, col2, col3 = st.columns(3)
with col1:
  mth_filter = st.selectbox("Select Month", options=["All"] + sorted(data_frm['month'].unique().tolist(), key=lambda x: datetime.strptime(x, "%Y-%m")))


with col2:
  cat_filter = st.selectbox("Select Category", options=["All"] + sorted(data_frm['category'].unique().tolist(), key=lambda x: x.lower()))

with col3:
  min_amt = st.number_input("Min Amount", min_value=0.0, step=10.0, format="%.2f", value=0.0)

filtered_data = data_frm.copy()
if mth_filter != "All":
  filtered_data = filtered_data[filtered_data['month'] == mth_filter]
if cat_filter != "All":
  filtered_data = filtered_data[filtered_data['category'] == cat_filter]
filtered_data = filtered_data[filtered_data['amount'] >= min_amt]

st.subheader("Expense Records")
k1, k2, k3 = st.columns(3)
k1.metric("Total Expenses", f"${filtered_data['amount'].sum():.2f}")
k2.metric("Number of Records", f"{len(filtered_data)}")
k3.metric("Average Expense", f"${filtered_data['amount'].mean():.2f}")
st.markdown("---")

mthly_total = filtered_data.groupby('month')['amount'].sum().reset_index().sort_values(by='month')
category_total = filtered_data.groupby('category')['amount'].sum().reset_index().sort_values(by='amount', ascending=False)

st.subheader("Dashboard Charts")
c1, c2 = st.columns(2)
with c1:
  st.pyplot(monthly_trend_chart(mthly_total)) #to display the monthly trend chart
with c2:
  st.pyplot(category_bar_chart(category_total)) #to display the category bar chart
st.markdown("---")

#Records Table
st.subheader("Expense Records Table")
st.dataframe(filtered_data[['id', 'note', 'category', 'amount', 'created_at']].sort_values(by='created_at', ascending=False), use_container_width=True)

#To download CSV
st.subheader("Download Expense Records")
report_dataframe = mthly_total.copy()
csv_data = report_dataframe.to_csv(index=False).encode('utf-8')
st.download_button(
  label="Download Monthly Expense Report as CSV",
  data=csv_data,
  file_name='monthly_expense_report.csv',
  mime='text/csv',
)

#Delete Expense Record in Streamlit
st.subheader("Delete Expense Record")
delete_id = st.number_input("Enter Expense ID to Delete", min_value=0, step=1)
if st.button("Delete Expense"):
    if delete_id > 0:
        delete_expense(int(delete_id))
        st.success(f"Expense with ID {delete_id} deleted successfully!")
        st.rerun()  # Refresh the app to show the updated expenses
    else:
        st.error("Please enter a valid Expense ID greater than zero(0).")