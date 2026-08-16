# 📈 BIST Kokpit

Borsa İstanbul için **karar-destek** aracı: izleme listesi, mum grafiği +
teknik göstergeler (RSI/MACD/hareketli ortalamalar), kural-tabanlı **tarama**
ve strateji **backtest**'i. Tarayıcıdan açılır.

> ⚠️ **Bu bir yatırım tavsiyesi aracı değildir.** Gösterilen "sinyaller",
> kullanıcının seçtiği bilinen teknik kuralların mekanik sonucudur. Araç
> **otomatik emir göndermez**; işlem kararını ve emri kullanıcı kendi aracı
> kurumunda (Midas/İş vb.) verir. Veriler Yahoo Finance kaynaklıdır ve BIST için
> **~15 dakika gecikmelidir** — günlük/haftalık işlem için yeterli, saniyelik
> alım-satım için değil.

---

## Özellikler

| Sekme | Ne yapar |
|-------|----------|
| 👀 **İzleme** | Seçili hisselerin son (gecikmeli) fiyatı, günlük/haftalık %, RSI, altın çapraz durumu |
| 📊 **Grafik** | Mum grafiği + SMA50/200, EMA20, RSI, MACD. Günlük **ve 15 dakikalık** (gecikmeli) zaman dilimleri |
| 🔎 **Teknik Tarama** | Fiyat/gösterge kurallarıyla filtrele (RSI eşiği, altın çapraz, fiyat > 50g, min. günlük %) — yfinance |
| 🧮 **Temel Tarama** | F/K, PD/DD, ROE, temettü verimi gibi TEMEL kriterlerle tüm BIST'i tara — borsapy / İş Yatırım verisi |
| 🧪 **Backtest** | SMA kesişimi / RSI dönüş / MACD stratejilerini geçmişte test et; komisyon dahil, al-tut ile kıyas |

İzleme listesine borsapy sayesinde **tüm BIST evreninden (797 hisse)** herhangi birini
ekleyebilirsin; borsapy kurulu değilse uygulama öne çıkan ~40 hisseyle sorunsuz çalışır.

## Yerelde çalıştırma

```bash
cd bist-kokpit
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` açılır.

### Parola (isteğe bağlı ama yayında şart)

`.streamlit/secrets.toml.example` dosyasını `.streamlit/secrets.toml` olarak
kopyalayın ve içine bir parola yazın:

```toml
app_password = "guclu-bir-parola"
```

Parola tanımlı değilse uygulama "geliştirme modu"nda açık geçer.

## Tarayıcıda yayınlama — Streamlit Community Cloud (ücretsiz)

1. Bu klasörü bir **GitHub reposuna** yükleyin (private olabilir).
2. [share.streamlit.io](https://share.streamlit.io) → **New app** → repoyu ve
   `bist-kokpit/app.py` dosyasını seçin.
3. **Advanced settings → Secrets** alanına şunu yapıştırın:
   ```toml
   app_password = "guclu-bir-parola"
   ```
4. Deploy. Kayınpederinize verdiğiniz URL'den açar, parolayı girer.

> Ücretsiz katmanda uygulama uzun süre kullanılmazsa "uykuya" geçer, açılışta
> birkaç saniyede uyanır. Her gün kullanılan bir araçta sorun olmaz.

### Ne zaman VPS'e geçmeli?

Sadece **uygulama kapalıyken bile bildirim/alarm** (örn. "şu hisse hedefe geldi")
göndermek isterseniz 7/24 açık bir yer gerekir → ~€4/ay Hetzner/DigitalOcean.
Kod birebir taşınır. Sırf ekranı açıp bakmak için buna gerek yok.

## Mimarî

```
app.py                 Streamlit arayüzü (4 sekme)
src/data.py            yfinance veri çekme + önbellek (10 dk)
src/indicators.py      RSI, MACD, SMA, EMA, Bollinger (saf pandas, C bağımlılığı yok)
src/screener.py        tarama metrikleri + filtreler
src/backtest.py        şeffaf vektörel backtest + 3 strateji
src/auth.py            basit parola kapısı
src/symbols.py         BIST hisse listesi
```

## Sonraki adımlar / yükseltme yolları

- **Daha zengin BIST verisi & tarama:** [`borsapy`](https://github.com/saidsurucu/borsapy)
  (40+ kriterli tarama, temel/bilanço, KAP haberleri). `src/data.py` içine ikinci
  kaynak olarak eklenebilir.
- **borsa-mcp:** [`borsa-mcp`](https://github.com/saidsurucu/borsa-mcp) sunucusunu
  Claude'a MCP olarak bağlarsanız tarama/KAP haberlerini kod yazmadan sorabilirsiniz.
- **Daha çok gösterge:** `pandas-ta-classic` (saf Python) veya `TA-Lib` (C, 150+
  gösterge + mum formasyonları). Uyarı: eski `pandas-ta` (twopirllc) 2025'te
  GitHub'dan kaldırıldı — `pandas-ta-classic` fork'unu kullanın.
- **Gelişmiş emir modeli:** `backtesting.py` (daha gerçekçi emir/stop/komisyon).
- **Gün-içi geçmiş:** `tvDatafeed` (TradingView, 15m/5m barlar).

## Veri ve sorumluluk notları

- Yahoo/yfinance gayriresmî bir kaynaktır; aşırı istekte geçici engel (HTTP 429)
  gelebilir. Uygulama bu yüzden veriyi **10 dk önbelleğe** alır.
- BIST **gerçek zamanlı** verisi lisanslı ve ücretlidir (borsa veri paketi).
  Bu araç bilinçli olarak ücretsiz **gecikmeli** veriyle çalışır.
- Backtest sonuçları geçmişe dayalı ve **varsayımsaldır**; geleceği garanti etmez.
