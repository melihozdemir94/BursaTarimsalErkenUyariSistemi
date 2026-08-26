import streamlit as st
import pandas as pd
import requests
import urllib3

# SSL uyarılarını gizlemek için (verify=False kullanıldığında konsolu temiz tutar)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. Sayfa Yapılandırması
st.set_page_config(
    page_title="Bursa Tarımsal Erken Uyarı Sistemi",
    layout="wide",
    page_icon="🌾"
)

# 2. Canlı Meteoroloji Verisi Çekme Fonksiyonu (SSL & Hata Yakalama Geliştirilmiş)
@st.cache_data(ttl=900)  # 15 dakikada bir veriyi yeniler
def get_live_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=auto"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # verify=False eklenerek Render Linux sunucularının SSL takılması engellenmiştir
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            return {
                "sicaklik": current.get("temperature_2m", "--"),
                "nem": current.get("relative_humidity_2m", "--"),
                "ruzgar": current.get("wind_speed_10m", "--"),
                "durum": "🟢 Canlı API Verisi"
            }
        else:
            return {
                "sicaklik": "--", 
                "nem": "--", 
                "ruzgar": "--", 
                "durum": f"🔴 API Yanıt Vermedi (Kod: {response.status_code})"
            }
            
    except Exception as e:
        # Hata gizlenmez, doğrudan arayüze basılır
        hata_mesaji = str(e)[:35]
        return {
            "sicaklik": "--", 
            "nem": "--", 
            "ruzgar": "--", 
            "durum": f"🔴 Bağlantı Hatası: {hata_mesaji}"
        }

# 3. Bursa İlçeleri Koordinat ve Tarımsal Erken Uyarı Veri Seti
@st.cache_data
def get_bursa_districts():
    return [
        {
            "ilce": "Nilüfer", 
            "lat": 40.2124, 
            "lon": 28.9802, 
            "hastalik": "Zeytin Halkalı Leke (Orta)", 
            "tavsiye": "Sulama takvimine uyulmalı, mantari hastalık riski takip edilmelidir."
        },
        {
            "ilce": "Osmangazi", 
            "lat": 40.1828, 
            "lon": 29.0669, 
            "hastalik": "Bağ Küllemesi (Düşük)", 
            "tavsiye": "Rutin saha kontrolleri yeterlidir."
        },
        {
            "ilce": "Mustafakemalpaşa", 
            "lat": 40.0350, 
            "lon": 28.4117, 
            "hastalik": "Domates Mildiyösü (Yüksek)", 
            "tavsiye": "⚠️ Yüksek nem ve sıcaklık sebebiyle koruyucu ilaçlama zamanlamasına dikkat edilmelidir."
        },
        {
            "ilce": "Gemlik", 
            "lat": 40.4312, 
            "lon": 29.1554, 
            "hastalik": "Zeytin Sineği (Yüksek)", 
            "tavsiye": "⚠️ Sahada sarı yapışkan tuzak takibi yapılmalı ve ilaçlama eşiği gözetlenmelidir."
        },
        {
            "ilce": "İnegöl", 
            "lat": 40.0784, 
            "lon": 29.5133, 
            "hastalik": "Elma Karalekesi (Orta)", 
            "tavsiye": "Gece sıcaklık düşüşleri ve nem artışına karşı dikkatli olunmalıdır."
        },
        {
            "ilce": "Mudanya", 
            "lat": 40.3752, 
            "lon": 28.8821, 
            "hastalik": "Zeytin Halkalı Leke (Yüksek)", 
            "tavsiye": "Rüzgar hızının uygun olduğu saatlerde koruyucu ilaçlama planlanmalıdır."
        },
        {
            "ilce": "Yıldırım", 
            "lat": 40.1917, 
            "lon": 29.0964, 
            "hastalik": "Düşük", 
            "tavsiye": "Meteorolojik koşullar tarımsal açıdan normal seyretmektedir."
        }
    ]

# Session State Yönetimi
if "secilen_ilce_detay" not in st.session_state:
    st.session_state.secilen_ilce_detay = None

# 4. Arayüz Tasarımı
st.title("🌾 Bursa Tarımsal Erken Uyarı Portalı")
st.caption("Bursa Büyükşehir Belediyesi & Tarım Peyzaj A.Ş. Saha Gözlem ve Erken Uyarı Paneli")
st.divider()

districts = get_bursa_districts()

# İlçe Kartları Dizilimi (3'lü Sütunlar Halinde)
cols_per_row = 3
for i in range(0, len(districts), cols_per_row):
    cols = st.columns(cols_per_row)
    for j in range(cols_per_row):
        if i + j < len(districts):
            d = districts[i + j]
            weather = get_live_weather(d["lat"], d["lon"])
            
            with cols[j]:
                with st.container(border=True):
                    st.markdown(f"### 📍 {d['ilce']}")
                    st.write(f"🌡️ **Sıcaklık:** {weather['sicaklik']} °C")
                    st.write(f"💧 **Bağıl Nem:** %{weather['nem']}")
                    st.write(f"💨 **Rüzgar Hızı:** {weather['ruzgar']} km/s")
                    st.write(f"⚠️ **Hastalık Riski:** {d['hastalik']}")
                    st.caption(f"Veri Durumu: {weather['durum']}")
                    
                    if st.button(f"🔍 {d['ilce']} Detay & Uyarı", key=f"btn_{d['ilce']}", use_container_width=True):
                        st.session_state.secilen_ilce_detay = {**d, **weather}

# İlçe Detay Pop-Up / Detay Paneli
if st.session_state.secilen_ilce_detay:
    detay = st.session_state.secilen_ilce_detay
    st.divider()
    st.warning(f"🚨 **{detay['ilce']} İlçesi Tarımsal Erken Uyarı Raporu**")
    
    d_col1, d_col2, d_col3 = st.columns(3)
    d_col1.metric("Anlık Sıcaklık", f"{detay['sicaklik']} °C")
    d_col2.metric("Bağıl Nem", f"%{detay['nem']}")
    d_col3.metric("Rüzgar Hızı", f"{detay['ruzgar']} km/s")

    st.info(f"📌 **Tarımsal Hastalık / Zararlı Riski:** {detay['hastalik']}")
    st.error(f"💡 **Saha Tavsiyesi ve Uyarı:** {detay['tavsiye']}")
