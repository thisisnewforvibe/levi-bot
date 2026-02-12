import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Phone, Calendar, Globe } from 'lucide-react'
import styles from './PersonalInfoPage.module.css'

export default function PersonalInfoPage() {
  const navigate = useNavigate()
  const [userData, setUserData] = useState({
    name: 'Foydalanuvchi',
    phone: '',
    timezone: 'Asia/Tashkent',
    createdAt: ''
  })

  useEffect(() => {
    try {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        const user = JSON.parse(userStr)
        setUserData({
          name: user.name || 'Foydalanuvchi',
          phone: user.phone || '',
          timezone: user.timezone || 'Asia/Tashkent',
          createdAt: user.created_at || ''
        })
      }
    } catch (e) {
      console.error('Failed to load user:', e)
    }
  }, [])

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "Noma'lum"
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString('uz-UZ', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button className={styles.backButton} onClick={() => navigate(-1)}>
          <ArrowLeft size={24} />
        </button>
        <h1 className={styles.title}>Shaxsiy ma'lumotlar</h1>
      </header>

      <div className={styles.content}>
        <div className={styles.infoCard}>
          <div className={styles.infoItem}>
            <div className={styles.infoIcon}>
              <User size={20} />
            </div>
            <div className={styles.infoContent}>
              <span className={styles.infoLabel}>Ism</span>
              <span className={styles.infoValue}>{userData.name}</span>
            </div>
          </div>

          <div className={styles.divider} />

          <div className={styles.infoItem}>
            <div className={styles.infoIcon}>
              <Phone size={20} />
            </div>
            <div className={styles.infoContent}>
              <span className={styles.infoLabel}>Telefon raqam</span>
              <span className={styles.infoValue}>{userData.phone || "Kiritilmagan"}</span>
            </div>
          </div>

          <div className={styles.divider} />

          <div className={styles.infoItem}>
            <div className={styles.infoIcon}>
              <Globe size={20} />
            </div>
            <div className={styles.infoContent}>
              <span className={styles.infoLabel}>Vaqt zonasi</span>
              <span className={styles.infoValue}>{userData.timezone}</span>
            </div>
          </div>

          <div className={styles.divider} />

          <div className={styles.infoItem}>
            <div className={styles.infoIcon}>
              <Calendar size={20} />
            </div>
            <div className={styles.infoContent}>
              <span className={styles.infoLabel}>Ro'yxatdan o'tgan sana</span>
              <span className={styles.infoValue}>{formatDate(userData.createdAt)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
