import streamlit as st
import pandas as pd
import folium
from folium import plugins
from streamlit_folium import st_folium
import math
import io

st.set_page_config(page_title="Ops Control Center - Kalimantan", layout="wide", page_icon="📡")

# ==========================================
# --- 1. INISIALISASI SESSION STATE ---
# ==========================================
# Menyimpan data di memori aplikasi agar bisa di-update secara real-time
if 'df_tim' not in st.session_state:
    st.session_state.df_tim = pd.DataFrame()
if 'df_site' not in st.session_state:
    st.session_state.df_site = pd.DataFrame()

# ==========================================
# --- 2. FUNGSI HELPER (ANTI-ERROR & LOGIKA) ---
# ==========================================
def clean_coord(val):
    """
    Fungsi untuk membersihkan data koordinat.
    Mengubah koma (Indonesia) menjadi titik (Standar Global/Python),
    serta menolak data teks/kosong yang menyebabkan aplikasi crash.
    """
    try:
        if pd.isna(val):
            return None
        if isinstance(val, str):
            val = val.replace(',', '.').strip()
            if val == '' or val.lower() in ['tba', '-', 'menyusul']:
                return None
        return float(val)
    except:
        return None # Kembalikan None jika format gagal diubah jadi angka

def calculate_distance(lat1, lon1, lat2, lon2):
    """Menghitung jarak Haversine dalam Kilometer."""
    R = 6371.0 # Radius Bumi (KM)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def convert_df_to_excel(df, sheet_name="Data"):
    """Konversi DataFrame ke format Excel (Bytes) untuk didownload."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# ==========================================
# --- 3. TAMPILAN HEADER & UPLOAD AWAL ---
# ==========================================
st.title("📡 Engineering Project Control & Mapping System")
st.markdown("Dashboard interaktif untuk monitoring pergerakan tim, analisis coverage area, dan manajemen Master Data wilayah operasional Kalimantan.")

# Upload data awal jika session state kosong
if st.session_state.df_tim.empty or st.session_state.df_site.empty:
    st.info("💡 Sistem mendeteksi Master Data kosong. Silakan upload file inisial terlebih dahulu.")
    col1, col2 = st.columns(2)
    with col1:
        file_tim = st.file_uploader("Upload Master Data Tim (ROAD MAP FME)", type=['xlsx'])
    with col2:
        file_site = st.file_uploader("Upload Master Data Site (Sidata)", type=['xlsx'])
        
    if file_tim and file_site:
        st.session_state.df_tim = pd.read_excel(file_tim)
        st.session_state.df_site = pd.read_excel(file_site)
        st.success("✅ Data Master Berhasil Dimuat! Sedang menyiapkan dashboard...")
        st.rerun()

# ==========================================
# --- 4. TAMPILAN UTAMA (MULTI-TAB) ---
# ==========================================
if not st.session_state.df_tim.empty and not st.session_state.df_site.empty:
    
    tab_map, tab_tim, tab_site = st.tabs([
        "🗺️ Live Coverage & Mapping", 
        "👥 Update Master Data Tim", 
        "🗼 Update Master Data Site"
    ])

    # ----------------------------------------
    # TAB 1: LIVE MAP & COVERAGE ANALYSIS
    # ----------------------------------------
    with tab_map:
        st.subheader("Analisis Coverage Site Terhadap Titik Homebase Tim")
        
        coverage_data = []
        df_tim_current = st.session_state.df_tim
        df_site_current = st.session_state.df_site
        
        # PROSES PERHITUNGAN JARAK & COVERAGE
        for _, site in df_site_current.iterrows():
            # Ekstrak & bersihkan koordinat site
            site_lat = clean_coord(site.get('Latitude Tujuan'))
            site_long = clean_coord(site.get('Longtitude Tujuan'))
            site_id = site.get('Site ID', 'Unknown Site')
            
            # Abaikan site yang tidak punya koordinat valid
            if site_lat is None or site_long is None: 
                continue
                
            nearest_team, min_dist = None, float('inf')
            team_lat, team_long, team_attitude = None, None, None
            
            for _, team in df_tim_current.iterrows():
                # Ekstrak & bersihkan koordinat tim
                t_lat = clean_coord(team.get('Lat'))
                t_long = clean_coord(team.get('Long'))
                
                # Abaikan tim yang tidak punya koordinat valid
                if t_lat is None or t_long is None: 
                    continue
                    
                # Hitung jarak
                dist = calculate_distance(site_lat, site_long, t_lat, t_long)
                if dist < min_dist:
                    min_dist = dist
                    nearest_team = team.get('Nama', 'Unknown')
                    team_lat, team_long = t_lat, t_long
                    team_attitude = team.get('ATTITUDE TIM', 'UNKNOWN')
                    
            if nearest_team:
                coverage_data.append({
                    'Site ID': site_id, 'Site Lat': site_lat, 'Site Long': site_long,
                    'Nearest Team': nearest_team, 'Team Lat': team_lat, 'Team Long': team_long,
                    'Attitude': team_attitude, 'Jarak (KM)': round(min_dist, 2)
                })

        df_coverage = pd.DataFrame(coverage_data)

        # RENDER PETA FOLIUM (Jika data coverage berhasil diproses)
        if not df_coverage.empty:
            start_lat = df_coverage['Site Lat'].iloc[0]
            start_long = df_coverage['Site Long'].iloc[0]
            
            # Basemap Modern CartoDB Positron
            m = folium.Map(location=[start_lat, start_long], zoom_start=8, tiles='CartoDB positron')
            plugins.Fullscreen(position='topright').add_to(m)

            # A. Plot Marker Tim
            for _, team in df_tim_current.iterrows():
                t_lat = clean_coord(team.get('Lat'))
                t_long = clean_coord(team.get('Long'))
                
                if t_lat is not None and t_long is not None:
                    att = str(team.get('ATTITUDE TIM', '')).upper()
                    # Logika warna: Hijau untuk Good, Oranye untuk Middle, Merah untuk Issue
                    warna = "green" if "GOOD" in att else "orange" if "MIDLE" in att else "red"
                    
                    html_popup = f"""
                    <div style='font-family: Arial; width: 200px;'>
                        <h4 style='color: {warna}; margin-bottom: 2px;'>{team.get('Nama', 'Unknown')}</h4>
                        <b>Role:</b> {team.get('ROLE', '-')}<br>
                        <b>Status:</b> {team.get('STATUS', '-')}<br>
                        <b>Attitude:</b> {team.get('ATTITUDE TIM', '-')}
                    </div>
                    """
                    folium.Marker(
                        [t_lat, t_long],
                        popup=folium.Popup(html_popup, max_width=250),
                        icon=folium.Icon(color=warna, icon="wrench", prefix="fa")
                    ).add_to(m)

            # B. Plot Site & Garis Animasi AntPath
            for _, row in df_coverage.iterrows():
                # Bulatan Hitam untuk Site
                folium.CircleMarker(
                    location=[row['Site Lat'], row['Site Long']],
                    radius=5, color="black", fill=True, fill_color="black", fill_opacity=0.8,
                    popup=f"<b>{row['Site ID']}</b><br>Dihandle oleh: {row['Nearest Team']}<br>Jarak: {row['Jarak (KM)']} KM"
                ).add_to(m)
                
                # AntPath (Garis Animasi Bergerak dari Tim ke Site)
                plugins.AntPath(
                    locations=[[row['Team Lat'], row['Team Long']], [row['Site Lat'], row['Site Long']]],
                    color="blue", weight=2, opacity=0.6, dash_array=[10, 15], delay=1000,
                    tooltip=f"{row['Site ID']} ➔ {row['Nearest Team']} ({row['Jarak (KM)']} KM)"
                ).add_to(m)

            st_folium(m, width=1300, height=600)
            
            # Tombol export Analisa Coverage
            excel_cov = convert_df_to_excel(df_coverage, "Analisis_Coverage")
            st.download_button(
                label="📥 Download Laporan Coverage Area", 
                data=excel_cov, 
                file_name="Report_Coverage.xlsx", 
                type="primary"
            )
        else:
            st.warning("Peta tidak dapat ditampilkan karena tidak ada koordinat valid yang terdeteksi di data Anda.")

    # ----------------------------------------
    # TAB 2: UPDATE MASTER DATA TIM
    # ----------------------------------------
    with tab_tim:
        st.subheader("👥 Database Personel & Mapping Tim")
        st.markdown("Edit tabel di bawah ini. Anda bisa menambah koordinat baru atau mengubah data yang sudah ada.")
        
        # Editor Interaktif
        edited_tim = st.data_editor(st.session_state.df_tim, num_rows="dynamic", use_container_width=True, height=500)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Simpan Perubahan Tim", use_container_width=True):
                st.session_state.df_tim = edited_tim
                st.success("✅ Data Tim diperbarui! Peta telah menyesuaikan.")
                st.rerun()
        with col2:
            excel_tim = convert_df_to_excel(st.session_state.df_tim, "ROAD_MAP")
            st.download_button("📥 Download Master Tim Terbaru (Excel)", excel_tim, "UPDATE_ROAD_MAP_FME.xlsx")

    # ----------------------------------------
    # TAB 3: UPDATE MASTER DATA SITE
    # ----------------------------------------
    with tab_site:
        st.subheader("🗼 Database Site & Area Tujuan")
        st.markdown("Perbarui data koordinat dan informasi site di sini.")
        
        # Editor Interaktif
        edited_site = st.data_editor(st.session_state.df_site, num_rows="dynamic", use_container_width=True, height=500)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Simpan Perubahan Site", use_container_width=True):
                st.session_state.df_site = edited_site
                st.success("✅ Data Site diperbarui! Peta telah menyesuaikan.")
                st.rerun()
        with col2:
            excel_site = convert_df_to_excel(st.session_state.df_site, "SITE_DATA")
            st.download_button("📥 Download Master Site Terbaru (Excel)", excel_site, "UPDATE_Site_Sidata.xlsx")
