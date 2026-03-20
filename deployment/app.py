import streamlit as st

def home_page():
    st.title("VDSS Streamlit App")

home = st.Page(home_page, title="Home", default=True)
nav = st.navigation([home], position="hidden")

with st.sidebar:
    st.page_link(home, label="Home")
    st.page_link("https://vdss.cboss.dev/", label="Documentation")

nav.run()