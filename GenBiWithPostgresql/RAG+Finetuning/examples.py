examples = [
    {
        "question": "Siapa saja pelanggan yang kredit limit nya di atas 20000 di negara France",
        "query": "SELECT customerNumber, customerName, city, creditLimit FROM customers WHERE country = 'France' AND creditLimit > 20000;"
    },
    {
        "question": "Daftar pelanggan di Australia dengan kredit limit lebih dari 20000",
        "query": "SELECT customerName, contactLastName FROM customers WHERE country = 'Australia' AND creditLimit > 20000;"
    },
    {
        "question": "Berapa pembayaran tertinggi dari pelanggan?",
        "query": "SELECT MAX(amount) AS max_payment FROM payments;"
    },
    {
        "question": "Berapa jumlah pesanan yang diterima pada tahun 2003?",
        "query": "SELECT COUNT(*) AS order_count FROM orders WHERE YEAR(orderDate) = 2003;"
    },
    {
        "question": "Ada berapa pelanggan yang kredit limit nya tinggi?",
        "query": "SELECT COUNT(*) AS pelanggan_tinggi_kredit FROM customers WHERE creditLimit > 20000;"
    },
    {
        "question": "Siapa saja pelanggan yang bernama Atelier graphique?",
        "query": "SELECT * FROM customers WHERE customerName = 'Atelier graphique';"
    },
    {
        "question": "Berikan nomor telepon dan alamat pelanggan tersebut",
        "query": "SELECT customerNumber, customerName, phone, addressLine1, addressLine2 FROM customers WHERE customerName = 'Atelier graphique';"
    },
    {
        "question": "Daftar produk yang dipesan oleh pelanggan dari USA",
        "query": "SELECT DISTINCT p.productName FROM products p JOIN orderdetails od ON p.productCode = od.productCode JOIN orders o ON od.orderNumber = o.orderNumber JOIN customers c ON o.customerNumber = c.customerNumber WHERE c.country = 'USA';"
    },
    {
        "question": "Siapa karyawan yang menangani pelanggan di kota New York?",
        "query": "SELECT e.firstName, e.lastName FROM employees e JOIN customers c ON e.employeeNumber = c.salesRepEmployeeNumber WHERE c.city = 'NYC';"
    },
    {
        "question": "Berapa total pembayaran dari pelanggan Atelier graphique?",
        "query": "SELECT SUM(p.amount) AS total_pembayaran FROM payments p JOIN customers c ON p.customerNumber = c.customerNumber WHERE c.customerName = 'Atelier graphique';"
    },
    {
        "question": "Coba berikan data lengkap terkait nama pelanggan tersebut",
        "query": "SELECT * FROM customers WHERE customerName IN ('Australian Collectors, Co.', 'Anna''s Decorations, Ltd', 'Souveniers And Things Co.', 'Australian Gift Network, Co', 'Australian Collectables, Ltd');"
    },
    {
        "question": "Buatkan visualisasi dari jumlah produk yang dipesan",
        "query": "SELECT p.productName, SUM(od.quantityOrdered) AS total_ordered FROM products p JOIN orderdetails od ON p.productCode = od.productCode GROUP BY p.productName;"
    },
    {
        "question": "Apa itu AI?",
        "query": "AI adalah kecerdasan buatan yang memungkinkan mesin belajar dan membuat keputusan seperti manusia."
    },
    {
        "question": "Saya ingin tahu jumlah pelanggan",
        "query": "Pertanyaan tidak cukup jelas. Silakan beri detail lebih lanjut."
    }
]

for e in examples:
    assert isinstance(e["question"], str), f"Input harus string, ditemukan {type(e['question'])}"
    assert isinstance(e["query"], str), f"Query harus string, ditemukan {type(e['query'])}"

from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
import streamlit as st

@st.cache_resource
def get_example_selector():
    with st.spinner("Embedding sedang berlangsung..."):
        print("🧠 Mulai embed example")
        embeddings = OllamaEmbeddings(model="all-minilm")
        print("✅ Embedding model siap")
        print("➡️ Membuat FAISS vectorstore")
        vectorstore = FAISS.from_texts(
            texts=[e["question"] for e in examples],
            embedding=embeddings,
            metadatas=examples
        )
        print("✅ FAISS vectorstore siap")
        print("➡️ Membuat selector")
        selector = SemanticSimilarityExampleSelector(
            vectorstore=vectorstore,
            k=3,
            input_keys=["question"]
        )
        print("✅ Selesai membuat selector")
    return selector