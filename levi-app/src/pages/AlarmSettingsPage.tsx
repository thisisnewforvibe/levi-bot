import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Volume2, Vibrate, Clock, ChevronRight } from 'lucide-react'
import { Capacitor } from '@capacitor/core'
import styles from './AlarmSettingsPage.module.css'

export default function AlarmSettingsPage() {
  const navigate = useNavigate()
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [vibrationEnabled, setVibrationEnabled] = useState(true)
  const [snoozeDuration, setSnoozeDuration] = useState(10)

  const openSystemSettings = async () => {
    if (Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android') {
      try {
        const { App } = await import('@capacitor/app')
        const appInfo = await App.getInfo()
        const packageName = appInfo.id
        window.open(`intent://settings/channel_notifications/${packageName}/alarm_channel#Intent;scheme=android-app;package=com.android.settings;end`, '_system')
      } catch (e) {
        alert('Sozlamalar → Ilovalar → Levi → Bildirishnomalar → "Eslatmalar" kanaliga boring')
      }
    } else {
      alert('Sozlamalar → Ilovalar → Levi → Bildirishnomalar ga boring')
    }
  }

  const saveSnoozeDuration = (duration: number) => {
    setSnoozeDuration(duration)
    localStorage.setItem('snoozeDuration', String(duration))
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button className={styles.backButton} onClick={() => navigate(-1)}>
          <ArrowLeft size={24} />
        </button>
        <h1 className={styles.title}>Alarm sozlamalari</h1>
      </header>

      <div className={styles.content}>
        {/* Sound Settings */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>OVOZ SOZLAMALARI</h3>
          
          <div className={styles.card}>
            <div className={styles.menuItem}>
              <div className={styles.menuIcon}>
                <Volume2 size={20} />
              </div>
              <span className={styles.menuText}>Ovoz</span>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={soundEnabled}
                  onChange={(e) => setSoundEnabled(e.target.checked)}
                />
                <span className={styles.toggleSlider}></span>
              </label>
            </div>

            <div className={styles.divider} />

            <div className={styles.menuItem}>
              <div className={styles.menuIcon}>
                <Vibrate size={20} />
              </div>
              <span className={styles.menuText}>Tebranish</span>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={vibrationEnabled}
                  onChange={(e) => setVibrationEnabled(e.target.checked)}
                />
                <span className={styles.toggleSlider}></span>
              </label>
            </div>
          </div>
        </div>

        {/* Snooze Settings */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>QAYTA ESLATISH</h3>
          
          <div className={styles.card}>
            <div className={styles.menuItem}>
              <div className={styles.menuIcon}>
                <Clock size={20} />
              </div>
              <span className={styles.menuText}>Kechiktirish vaqti</span>
              <span className={styles.menuValue}>{snoozeDuration} daqiqa</span>
            </div>

            <div className={styles.divider} />

            <div className={styles.snoozeOptions}>
              {[5, 10, 15, 30].map(duration => (
                <button
                  key={duration}
                  className={`${styles.snoozeButton} ${snoozeDuration === duration ? styles.active : ''}`}
                  onClick={() => saveSnoozeDuration(duration)}
                >
                  {duration} daq
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* System Settings */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>TIZIM SOZLAMALARI</h3>
          
          <div className={styles.card}>
            <div className={styles.menuItem} onClick={openSystemSettings} style={{ cursor: 'pointer' }}>
              <div className={styles.menuIcon}>
                <Volume2 size={20} />
              </div>
              <div className={styles.menuContent}>
                <span className={styles.menuText}>Tizim bildirishnoma sozlamalari</span>
                <span className={styles.menuSubtext}>Ovoz va tebranishni sozlash</span>
              </div>
              <ChevronRight size={20} className={styles.menuArrow} />
            </div>
          </div>
        </div>

        <p className={styles.note}>
          💡 Eslatma: Ovoz balandligi telefon sozlamalariga bog'liq. Alarm to'liq ishlashi uchun "Bezovta qilmaslik" rejimini o'chiring.
        </p>
      </div>
    </div>
  )
}
