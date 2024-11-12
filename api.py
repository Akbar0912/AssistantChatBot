import pandas as pd
import streamlit as st
import pydeck as pdk

# Membuat data dummy
data = {
    "latitude": [-6.2, -6.21, -6.22, -6.23, -6.24],
    "longitude": [106.8, 106.81, 106.82, 106.83, 106.84],
    "nilai_kinerja": [20, 40, 60, 80, 100]  # Variasi nilai kinerja
}

df_dummy = pd.DataFrame(data)

# Fungsi create_map_visualization yang telah disesuaikan
def create_map_visualization(df):
    
    lat_column = 'latitude'
    lon_column = 'longitude'
    kinerja_column = 'nilai_kinerja'
    
    df[lat_column] = pd.to_numeric(df[lat_column], errors='coerce')
    df[lon_column] = pd.to_numeric(df[lon_column], errors='coerce')
    df[kinerja_column] = pd.to_numeric(df[kinerja_column], errors='coerce')
    df = df.dropna(subset=[lat_column, lon_column, kinerja_column])
    
    if df.empty:
        st.error("Tidak ada data valid untuk divisualisasikan.")
        return None
    
    min_kinerja = df[kinerja_column].min()
    max_kinerja = df[kinerja_column].max()
    
    # Untuk memastikan bahwa elevation range berfungsi dengan benar
    st.write(f"Min nilai kinerja: {min_kinerja}, Max nilai kinerja: {max_kinerja}")
    
    view_state = pdk.ViewState(
        latitude=df[lat_column].mean(),
        longitude=df[lon_column].mean(),
        zoom=11,
        pitch=50,
    )
    
    layer = [
        pdk.Layer(
            "HexagonLayer",
            data=df,
            get_position=f"[{lon_column}, {lat_column}]",
            get_elevation=kinerja_column,
            elevation_scale=5,
            elevation_range=[min_kinerja, max_kinerja],
            radius=200,
            pickable=True,
            extruded=True,
            auto_highlight=True,
            coverage=1,
            color_range=[
                [255, 0, 0, 140],      # Merah untuk kinerja rendah
                [255, 165, 0, 140],    # Oranye
                [255, 255, 0, 140],    # Kuning
                [173, 255, 47, 140],   # Kuning Hijau
                [0, 128, 0, 140]       # Hijau untuk kinerja tinggi
            ],
        ),
        pdk.Layer(
            "ScatterplotLayer",
            df,
            get_position=f"[{lon_column}, {lat_column}]",
            get_color=f"[200, (255 - 200 * ({kinerja_column} - {min_kinerja}) / ({max_kinerja} - {min_kinerja})), 0, 160]",
            elevation_scale=10,
            get_radius=500,
            pickable=True,
        )
    ]
    
    return pdk.Deck(
        layers=layer,
        initial_view_state=view_state,
        tooltip={
            "html": "<b>Latitude:</b> {latitude}<br>"
                    "<b>Longitude:</b> {longitude}<br>"
                    f"<b>Nilai Kinerja:</b> {{{kinerja_column}}}",
            "style": {
                "backgroundColor": "steelblue",
                "color": "white"
            }
        },
    )

# Menjalankan visualisasi dengan data dummy
deck = create_map_visualization(df_dummy)
if deck:
    st.pydeck_chart(deck)
