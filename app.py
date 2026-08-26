import datetime
import requests
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

BURSA_DISTRICTS = {
    "Osmangazi": {"lat": 40.1828, "lon": 29.0669, "crop": "Şeftali, Siyah İncir, Sebze"},
    "Nilüfer": {"lat": 40.2117, "lon": 28.8311, "crop": "Çilek, Enginar, Bağcılık"},
    "Yıldırım": {"lat": 40.1925, "lon": 29.0944, "crop": "Meyve Yetiştiriciliği, Süs Bitkileri"},
    "Gemlik": {"lat": 40.4312, "lon": 29.1574, "crop": "Gemlik Zeytini, Narenciye"},
    "İnegöl": {"lat": 40.0781, "lon": 29.5133, "crop": "Ayçekirdeği, İnegöl Köftelik Tahıl, Meyve"},
    "İznik": {"lat": 40.4286, "lon": 29.7215, "crop": "Zeytin, Üzüm, Domates, Kivi"},
    "Karacabey": {"lat": 40.2144, "lon": 28.3572, "crop": "Salçalık Domates, Mısır, Soğan, Soja"},
    "Mustafakemalpaşa": {"lat": 40.0353, "lon": 28.4117, "crop": "Tatlı Biber, Domates, Biber, Çeltik"},
    "Mudanya": {"lat": 40.3753, "lon": 28.8822, "crop": "Zeytin, Bağcılık, Incir"},
    "Orhangazi": {"lat": 40.4897, "lon": 29.3092, "crop": "Zeytin, Turşuluk Hıyar, Kiwi"},
    "Yenişehir": {"lat": 40.2644, "lon": 29.6531, "crop": "Biber, Taze Fasulye, Hububat, Bezelye"},
    "Büyükorhan": {"lat": 39.7744, "lon": 28.8803, "crop": "Gölet Sulamalı Ceviz, Bakliyat, Hayvancılık"},
    "Harmancık": {"lat": 39.6953, "lon": 29.1558, "crop": "Ceviz, Çörek Otu, Hububat"},
    "Keles": {"lat": 39.9125, "lon": 29.1394, "crop": "Aronya, Kiraz, Çilek, Gölet Sulamalı Meyve"},
    "Orhaneli": {"lat": 39.8925, "lon": 28.9922, "crop": "Mermer Yöresi Çilek, Vişne, Madımak"},
    "Gürsu": {"lat": 40.2175, "lon": 29.1936, "crop": "Deveci Armudu, Şeftali, Nar"},
    "Kestel": {"lat": 40.1969, "lon": 29.2125, "crop": "Bursa Siyahı İncir, Fidan Üretimi, Şeftali"}
}

# Veri ve zaman kontrol hafızası
cache_data = {
    "districts": {},
    "last_update": None,
    "last_fetch_time": None
}

def evaluate_agri_alerts(temp, humidity, soil_moisture, wind_speed, weather_code):
    alerts = []
    if temp <= 2:
        alerts.append({"type": "danger", "title": "❄️ ZİRAİ DON UYARISI", "msg": "Sıcaklık kritiğin altında! Serada ısıtıcıları çalıştırın veya üst örtü kullanın."})
    elif temp > 35:
        alerts.append({"type": "warning", "title": "🔥 AŞIRI SICAK STRESİ", "msg": "Polenlenme olumsuz etkilenebilir. Gece sulaması tercih edilmelidir."})
        
    if 15 <= temp <= 26 and humidity >= 80:
        alerts.append({"type": "warning", "title": "🍄 MANTARİ HASTALIK RİSKİ", "msg": "Nem ve sıcaklık Külleme/Mildiyö için uygun. Koruyucu ilaçlama değerlendirilmeli."})
        
    if soil_moisture < 15:
        alerts.append({"type": "info", "title": "💧 TOPRAK KURAKLIĞI", "msg": "Kök bölgesindeki nem yetersiz. Sulama programını devreye alın."})
        
    if wind_speed > 20:
        alerts.append({"type": "danger", "title": "💨 ŞİDDETLİ RÜZGAR", "msg": "Rüzgar > 20 km/s. Yapraktan gübreleme veya pestisit ilaçlaması YAPMAYIN."})
        
    if weather_code in [61, 63, 65, 80, 81, 82]:
        alerts.append({"type": "primary", "title": "🌧️ YAĞIŞ VAR", "msg": "Toprak işleme yapmayın, makinelerin tarlaya girmesi toprağı sıkıştırabilir."})

    if not alerts:
        alerts.append({"type": "success", "title": "✅ KOŞULLAR UYGUN", "msg": "Bölgede tarlasında rutin tarımsal faaliyetler sürdürülebilir."})
        
    return alerts

def get_weather_animation_type(weather_code, temp, wind):
    if weather_code in [0, 1]: return "sunny"
    elif weather_code in [2, 3]: return "cloudy"
    elif weather_code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: return "rainy"
    elif weather_code in [71, 73, 75, 77, 85, 86]: return "snowy"
    elif wind > 25: return "windy"
    return "sunny"

def fetch_weather_data_if_needed():
    """Son güncellemeden bu yana 5 dakikadan fazla geçtiyse API'den yeni veri çeker"""
    global cache_data
    now = datetime.datetime.now()
    
    # Eğer son 5 dakika içinde çekilmiş veri varsa tekrar API'ye gitme
    if cache_data["last_fetch_time"] and (now - cache_data["last_fetch_time"]).total_seconds() < 300:
        return

    now_str = now.strftime("%H:%M:%S")
    temp_db = {}
    
    for district, info in BURSA_DISTRICTS.items():
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={info['lat']}&longitude={info['lon']}&"
            f"current=temperature_2m,relative_humidity_2m,wind_speed_10m,soil_moisture_0_to_1cm,weather_code"
        )
        try:
            res = requests.get(url, timeout=5).json()
            curr = res.get("current", {})
            
            temp = curr.get("temperature_2m", 0)
            hum = curr.get("relative_humidity_2m", 0)
            wind = curr.get("wind_speed_10m", 0)
            soil = round((curr.get("soil_moisture_0_to_1cm", 0) or 0) * 100, 1)
            w_code = curr.get("weather_code", 0)
            
            anim_type = get_weather_animation_type(w_code, temp, wind)
            
            temp_db[district] = {
                "temp": temp,
                "humidity": hum,
                "wind": wind,
                "soil_moisture": soil,
                "crop": info["crop"],
                "anim_type": anim_type,
                "alerts": evaluate_agri_alerts(temp, hum, soil, wind, w_code)
            }
        except Exception as e:
            print(f"{district} hatası: {e}")

    cache_data["districts"] = temp_db
    cache_data["last_update"] = now_str
    cache_data["last_fetch_time"] = now

HTML_LAYOUT = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Bursa Tarımsal Meteoroloji Ve Erken Uyarı Portalı</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f0f4f8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .card-district { border-radius: 15px; transition: all 0.25s ease; border: none; cursor: pointer; }
        .card-district:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.1) !important; border: 1px solid #198754; }
        .click-hint { font-size: 0.75rem; color: #198754; font-weight: 600; }
        
        .anim-box { height: 160px; border-radius: 12px; position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center; margin-bottom: 20px; color: white; text-shadow: 1px 1px 4px rgba(0,0,0,0.6); }
        .bg-sunny { background: linear-gradient(135deg, #ff9900, #ff5500); }
        .sun-icon { width: 70px; height: 70px; background: #fff700; border-radius: 50%; box-shadow: 0 0 40px #fff700; animation: pulse 2s infinite alternate; }
        @keyframes pulse { 0% { transform: scale(0.9); box-shadow: 0 0 20px #fff700; } 100% { transform: scale(1.1); box-shadow: 0 0 50px #fff700; } }
        .bg-rainy { background: linear-gradient(135deg, #3a7bd5, #3a6073); }
        .rain-drop { position: absolute; background: rgba(255,255,255,0.8); width: 2px; height: 15px; animation: drop 0.6s linear infinite; }
        @keyframes drop { 0% { transform: translateY(-80px); opacity: 1; } 100% { transform: translateY(80px); opacity: 0.2; } }
        .bg-cloudy { background: linear-gradient(135deg, #757f9a, #d7dde8); }
        .cloud-icon { font-size: 4rem; animation: floatCloud 3s ease-in-out infinite alternate; }
        @keyframes floatCloud { 0% { transform: translateX(-15px); } 100% { transform: translateX(15px); } }
        .bg-windy { background: linear-gradient(135deg, #4ac29a, #bdfff3); color: #333; }
        .wind-line { font-size: 3.5rem; animation: blowWind 1.5s ease-in-out infinite; }
        @keyframes blowWind { 0% { transform: translateX(-30px); opacity: 0.3; } 50% { opacity: 1; } 100% { transform: translateX(30px); opacity: 0.3; } }
        .bg-snowy { background: linear-gradient(135deg, #83a4d4, #b6fbff); color: #333; }
    </style>
</head>
<body>
<div class="container py-4">
    <div class="d-flex justify-content-between align-items-center mb-4 bg-white p-3 rounded-3 shadow-sm">
        <div>
            <h2 class="fw-bold text-success mb-0">🌱 Bursa Tarımsal Meteoroloji Takip Portalı</h2>
            <p class="text-muted mb-0 small">İlçe detayları ve canlı animasyonlu tarımsal uyarılar için kartlara tıklayın.</p>
        </div>
        <div class="text-end">
            <span class="badge bg-success p-2 fs-6" id="live-timer">Yükleniyor...</span>
        </div>
    </div>

    <div class="row g-3" id="districts-container"></div>
</div>

<div class="modal fade" id="districtModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered modal-lg">
    <div class="modal-content" style="border-radius: 18px; overflow: hidden;">
      <div class="modal-header bg-dark text-white">
        <h5 class="modal-title fw-bold" id="modalTitle">İlçe Adı</h5>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Kapat"></button>
      </div>
      <div class="modal-body p-4">
        <div id="animContainer" class="anim-box"></div>
        <div class="row text-center g-2 mb-4">
            <div class="col-3"><div class="p-2 border rounded bg-light"><small class="text-muted d-block">Sıcaklık</small><strong class="fs-5 text-dark" id="modalTemp">0 °C</strong></div></div>
            <div class="col-3"><div class="p-2 border rounded bg-light"><small class="text-muted d-block">Hava Nemi</small><strong class="fs-5 text-dark" id="modalHum">%0</strong></div></div>
            <div class="col-3"><div class="p-2 border rounded bg-light"><small class="text-muted d-block">Toprak Nemi</small><strong class="fs-5 text-dark" id="modalSoil">%0</strong></div></div>
            <div class="col-3"><div class="p-2 border rounded bg-light"><small class="text-muted d-block">Rüzgar Hızı</small><strong class="fs-5 text-dark" id="modalWind">0 km/s</strong></div></div>
        </div>
        <div class="mb-3">
            <h6 class="fw-bold text-secondary">🌾 Hakim Ürün Desenleri:</h6>
            <p id="modalCrop" class="badge bg-light text-dark border p-2 fs-6">Ürünler...</p>
        </div>
        <div>
            <h6 class="fw-bold text-danger">⚠️ Tarımsal Meteorolojik Uyarısı & Tavsiyeler:</h6>
            <div id="modalAlerts"></div>
        </div>
      </div>
      <div class="modal-footer bg-light">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Kapat</button>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
let globalDistrictsData = {};

async function updateDashboard() {
    try {
        const res = await fetch('/api/data');
        const payload = await res.json();
        
        globalDistrictsData = payload.districts;
        const container = document.getElementById('districts-container');
        container.innerHTML = '';

        for (const [district, info] of Object.entries(globalDistrictsData)) {
            const card = `
                <div class="col-md-6 col-lg-4">
                    <div class="card card-district shadow-sm p-3 bg-white" onclick="openDistrictModal('${district}')">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h5 class="fw-bold mb-0 text-dark">${district}</h5>
                            <span class="badge bg-primary fs-6">${info.temp} °C</span>
                        </div>
                        <div class="row text-muted small g-2 mb-2">
                            <div class="col-6">💧 Nem: <b>%${info.humidity}</b></div>
                            <div class="col-6">🌱 Toprak: <b>%${info.soil_moisture}</b></div>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-2 pt-2 border-top">
                            <span class="click-hint">🔍 Animasyon & Detaylar İçin Tıklayın</span>
                            <span class="badge bg-outline-secondary text-dark border">Uyarı (${info.alerts.length})</span>
                        </div>
                    </div>
                </div>
            `;
            container.innerHTML += card;
        }
        
        document.getElementById('live-timer').innerText = 'Son Güncelleme: ' + payload.last_update;
    } catch (e) {
        console.error("Veri alınamadı:", e);
    }
}

function openDistrictModal(districtName) {
    const data = globalDistrictsData[districtName];
    if(!data) return;

    document.getElementById('modalTitle').innerText = districtName + " - Tarımsal Meteoroloji Analizi";
    document.getElementById('modalTemp').innerText = data.temp + " °C";
    document.getElementById('modalHum').innerText = "%" + data.humidity;
    document.getElementById('modalSoil').innerText = "%" + data.soil_moisture;
    document.getElementById('modalWind').innerText = data.wind + " km/s";
    document.getElementById('modalCrop').innerText = data.crop;

    const animBox = document.getElementById('animContainer');
    animBox.className = "anim-box bg-" + data.anim_type;
    
    if (data.anim_type === "sunny") {
        animBox.innerHTML = '<div class="sun-icon"></div>';
    } else if (data.anim_type === "rainy") {
        let drops = '';
        for(let i=0; i<15; i++) {
            let left = Math.random() * 100;
            let delay = Math.random() * 0.5;
            drops += `<div class="rain-drop" style="left:${left}%; animation-delay:${delay}s;"></div>`;
        }
        animBox.innerHTML = drops + '<span style="z-index:2; font-size: 2rem; font-weight:bold;">🌧️ Yağışlı Hava</span>';
    } else if (data.anim_type === "cloudy") {
        animBox.innerHTML = '<div class="cloud-icon">☁️</div>';
    } else if (data.anim_type === "windy") {
        animBox.innerHTML = '<div class="wind-line">💨 Rüzgarlı Hava</div>';
    } else {
        animBox.innerHTML = '<span style="font-size: 2rem;">❄️ Karlı / Soğuk Hava</span>';
    }

    const alertsBox = document.getElementById('modalAlerts');
    alertsBox.innerHTML = '';
    data.alerts.forEach(a => {
        alertsBox.innerHTML += `<div class="alert alert-${a.type} mb-2"><strong>${a.title}:</strong> ${a.msg}</div>`;
    });

    const myModal = new bootstrap.Modal(document.getElementById('districtModal'));
    myModal.show();
}

updateDashboard();
setInterval(updateDashboard, 15000);
</script>
</body>
</html>
'''

@app.route('/')
def home():
    fetch_weather_data_if_needed()
    return render_template_string(HTML_LAYOUT)

@app.route('/api/data')
def get_data():
    fetch_weather_data_if_needed()
    return jsonify({
        "districts": cache_data["districts"],
        "last_update": cache_data["last_update"]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
