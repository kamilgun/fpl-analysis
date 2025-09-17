import streamlit as st

st.set_page_config(page_title="FPL Analysis", layout="wide")

# Debug mesajı: deploy sırasında buraya kadar gelindi mi?
st.write("✅ Streamlit app started!")

# Örnek buton - deploy test
if st.button("Say hello"):
    st.success("Hello from Streamlit Cloud!")

# Sonradan visuals.py'den import edebilirsin
# from visuals import grafik_value_vs_points
# grafik_value_vs_points()
