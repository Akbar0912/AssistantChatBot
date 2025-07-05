import streamlit as st
import plotly.express as px
import pandas as pd
from langchain_utils import invoke_chain

st.title("Generative Business Intelligence")

if "model_llm" not in st.session_state:
    st.session_state["model_llm"] = "llama3.2"
    
if "messages" not in st.session_state:
    print("creating session state")
    st.session_state.messages = []

if "data_for_chart" not in st.session_state:
    st.session_state["data_for_chart"] = None

# Display chat history count
if st.session_state.messages:
    st.sidebar.write(f"💬 Total pesan: {len(st.session_state.messages)}")

# Render chat history
chat_container = st.container()
with chat_container:
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Re-display data table and visualization for assistant messages
            if message["role"] == "assistant" and f"data_history_{i}" in st.session_state:
                data = st.session_state[f"data_history_{i}"]
                if data and data.get("rows") and len(data["rows"]) > 0:
                    try:
                        df = pd.DataFrame(data["rows"], columns=data["columns"])
                        
                        # Show table for single column or when data is not suitable for charts
                        if len(df.columns) == 1 or len(df) > 20:
                            st.subheader("📊 Data Hasil Query")
                            st.dataframe(df, use_container_width=True, height=min(400, len(df) * 35 + 38))
                        else:
                            # Show both table and chart for multi-column data
                            st.subheader("📊 Data Hasil Query")
                            st.dataframe(df, use_container_width=True, height=min(300, len(df) * 35 + 38))
                            
                            st.subheader("📈 Visualisasi Data")
                            try:
                                if len(df.columns) < 2:
                                    st.info("💡 Data hanya memiliki 1 kolom, sehingga tidak cocok untuk visualisasi grafik.")
                                else:
                                    # Check if second column is numeric
                                    second_col_numeric = pd.to_numeric(df.iloc[:, 1], errors='coerce')
                                    if second_col_numeric.notna().any():
                                        # Buat bar chart untuk data numerik
                                        fig = px.bar(df, x=df.columns[0], y=df.columns[1], 
                                                    title=f"Grafik: {df.columns[1]} berdasarkan {df.columns[0]}")
                                        fig.update_layout(xaxis_tickangle=45, height=500)
                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        # Buat chart distribusi (frekuensi) jika bukan numerik
                                        value_counts = df.iloc[:, 0].value_counts().head(20)
                                        fig = px.bar(x=value_counts.index, y=value_counts.values,
                                                    title=f"Distribusi {df.columns[0]} (Top 20)",
                                                    labels={'x': df.columns[0], 'y': 'Jumlah'})
                                        fig.update_layout(xaxis_tickangle=45, height=500)
                                        st.plotly_chart(fig, use_container_width=True)
                            except Exception as viz_error:
                                print(f"Error in visualization: {viz_error}")
                                st.warning("⚠️ Tidak dapat membuat visualisasi untuk data ini.")
                    except Exception as df_error:
                        st.error(f"Error menampilkan data: {df_error}")

if prompt := st.chat_input("Apa Pertanyaanmu?"):
    print(f"Prompt dari pengguna: {prompt}")
    st.session_state.messages.append({"role": "user", "content": str(prompt)})
    
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)
    
    with st.spinner("Generating response..."):
        try:
            response = invoke_chain(prompt, st.session_state.messages)
            print(f"Streamlit response: {response}")
            
            with chat_container:
                with st.chat_message("assistant"):
                    # Check for errors
                    if "Error" in response:
                        st.error("❌ Terjadi kesalahan saat memproses pertanyaan Anda.")
                        st.markdown(response)
                    else:
                        # Add context-aware friendly message
                        if any(word in prompt.lower() for word in ["siapa", "nama", "daftar", "list"]):
                            st.markdown("📋 **Berikut adalah daftar yang sesuai dengan kriteria Anda:**")
                        elif any(word in prompt.lower() for word in ["berapa", "jumlah", "count", "total"]):
                            st.markdown("🔢 **Berikut adalah hasil perhitungan:**")
                        else:
                            st.markdown("💡 **Hasil pencarian:**")
                        
                        # Get current data for this response
                        current_data = st.session_state.get("data_for_chart", None)
                        print(f"Debug - Current data: {current_data}")
                        
                        if current_data and current_data.get("rows") and len(current_data["rows"]) > 0:
                            try:
                                df = pd.DataFrame(current_data["rows"], columns=current_data["columns"])
                                print(f"Debug - DataFrame shape: {df.shape}, columns: {df.columns.tolist()}")
                                
                                # Store data for history (using message index)
                                message_index = len(st.session_state.messages)
                                st.session_state[f"data_history_{message_index}"] = current_data
                                
                                # Decision logic for display
                                if len(df.columns) == 1:
                                    # Single column - show only table
                                    st.subheader("📊 Data Hasil Query")
                                    st.dataframe(df, use_container_width=True, height=min(400, len(df) * 35 + 38))
                                    st.info(f"💡 Menampilkan {len(df)} data dalam bentuk tabel karena hanya terdapat 1 kolom.")
                                    
                                elif len(df) > 50:
                                    # Too many rows - show only table
                                    st.subheader("📊 Data Hasil Query")
                                    st.dataframe(df, use_container_width=True, height=400)
                                    st.info(f"💡 Menampilkan {len(df)} data dalam bentuk tabel karena data terlalu banyak untuk divisualisasikan.")
                                    
                                else:
                                    # Multi-column with reasonable size - show both table and chart
                                    st.subheader("📊 Data Hasil Query")
                                    st.dataframe(df, use_container_width=True, height=min(300, len(df) * 35 + 38))
                                    
                                    st.subheader("📈 Visualisasi Data")
                                    try:
                                        # Check if second column is numeric
                                        second_col_numeric = pd.to_numeric(df.iloc[:, 1], errors='coerce')
                                        if second_col_numeric.notna().any():
                                            # Create bar chart for numeric data
                                            fig = px.bar(df, x=df.columns[0], y=df.columns[1], 
                                                       title=f"Grafik: {df.columns[1]} berdasarkan {df.columns[0]}")
                                            fig.update_layout(xaxis_tickangle=45, height=500)
                                            st.plotly_chart(fig, use_container_width=True)
                                        else:
                                            # Create frequency chart for non-numeric data
                                            value_counts = df.iloc[:, 0].value_counts().head(20)  # Limit to top 20
                                            fig = px.bar(x=value_counts.index, y=value_counts.values,
                                                       title=f"Distribusi {df.columns[0]} (Top 20)",
                                                       labels={'x': df.columns[0], 'y': 'Jumlah'})
                                            fig.update_layout(xaxis_tickangle=45, height=500)
                                            st.plotly_chart(fig, use_container_width=True)
                                    except Exception as viz_error:
                                        print(f"Error in visualization: {viz_error}")
                                        st.warning("⚠️ Tidak dapat membuat visualisasi untuk data ini.")
                                        
                            except Exception as df_error:
                                print(f"Error creating DataFrame: {df_error}")
                                st.error(f"❌ Error memproses data: {df_error}")
                        else:
                            print("Debug - No chart data available or data is empty")
                        
                        # Always display the formatted response
                        st.markdown("---")
                        st.markdown("**📝 Ringkasan:**")
                        st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            st.error(f"❌ {error_msg}")
            print(f"Error in Streamlit: {error_msg}")
            
            with chat_container:
                with st.chat_message("assistant"):
                    st.markdown(f"❌ Maaf, terjadi kesalahan: {error_msg}")
                    st.markdown("💡 **Saran:** Coba dengan pertanyaan yang lebih spesifik atau periksa koneksi database.")
            
            st.session_state.messages.append({"role": "assistant", "content": f"Error: {error_msg}"})

# Sidebar with helpful information
with st.sidebar:
    st.header("ℹ️ Informasi")
    st.markdown("""
    **Tips penggunaan:**
    - Gunakan pertanyaan yang spesifik
    - Contoh: "Siapa saja pelanggan dari USA?"
    - Contoh: "Berapa total pembayaran dari Australia?"
    
    **Fitur:**
    - 📊 Tabel data otomatis
    - 📈 Visualisasi untuk data numerik
    - 💬 Riwayat chat tersimpan
    - 🗑️ Tombol hapus riwayat
    """)
    
    if st.button("🔄 Refresh Data"):
        if "data_for_chart" in st.session_state:
            del st.session_state["data_for_chart"]
        st.success("Data refreshed!")
        
    # Clear session state on app restart
    if st.button("🗑️ Clear Chat History", help="Hapus riwayat chat untuk memulai percakapan baru"):
        st.session_state.clear()
        st.rerun()