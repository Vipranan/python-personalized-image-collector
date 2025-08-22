import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
from bs4 import BeautifulSoup
# Ensure the required packages are installed
# !pip install PyPDF2 streamlit beautifulsoup4

st.set_page_config(page_title="PDF Splitter Agent", layout="centered")

st.title("📄 PDF Splitter Agent")
st.markdown("Upload a PDF and get only the first few pages as a new file.")

uploaded_file = st.file_uploader("Upload your PDF", type=["pdf"])

if uploaded_file:
    st.success("PDF uploaded successfully.")
    
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)
    
    st.info(f"Total pages in uploaded PDF: **{total_pages}**")
    
    num_pages = st.number_input("Enter number of pages to keep from the start:", 
                                min_value=1, 
                                max_value=total_pages, 
                                value=2)
    
    if st.button("✂️ Split PDF"):
        writer = PdfWriter()
        
        for i in range(num_pages):
            writer.add_page(reader.pages[i])
        
        output_pdf = BytesIO()
        writer.write(output_pdf)
        output_pdf.seek(0)
        
        st.success(f"Successfully split first {num_pages} page(s)!")
        st.download_button(
            label="📥 Download Split PDF",
            data=output_pdf,
            file_name=f"split_first_{num_pages}_pages.pdf",
            mime="application/pdf"
        )
