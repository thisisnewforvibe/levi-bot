import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Phone, Bell, Volume2, HelpCircle, LogOut, ChevronRight, Crown } from 'lucide-react'
import styles from './ProfilePage.module.css'
import { authAPI } from '../services/api'

export default function ProfilePage() {
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState(true)
  const [userName, setUserName] = useState('Foydalanuvchi')
  const [userPhone, setUserPhone] = useState('')

  // Load user data from localStorage
  useEffect(() => {
    try {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        const user = JSON.parse(userStr)
        if (user.name) setUserName(user.name)
        if (user.phone) setUserPhone(user.phone)
      }
    } catch (e) {
      console.error('Failed to load user:', e)
    }
  }, [])

  const handleLogout = () => {
    authAPI.logout()
    navigate('/login')
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button className={styles.backButton} onClick={() => navigate(-1)}>
          <ArrowLeft size={24} />
        </button>
        <h1 className={styles.title}>Profil</h1>
      </header>

      {/* Profile Info */}
      <div className={styles.profileCard}>
        <div className={styles.avatar}>
          <User size={32} />
        </div>
        <div className={styles.profileInfo}>
          <h2 className={styles.userName}>{userName}</h2>
          <p className={styles.userPhone}>{userPhone}</p>
        </div>
        <button className={styles.editButton} onClick={() => navigate('/edit-profile')}>
          Tahrirlash
        </button>
      </div>

      {/* Settings */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>SOZLAMALAR</h3>
        
        <div className={styles.menuItem} onClick={() => navigate('/subscription')} style={{cursor: 'pointer'}}>
          <div className={styles.menuIcon} style={{color: '#FFB800'}}>
            <Crown size={20} />
          </div>
          <span className={styles.menuText}>Obuna</span>
          <ChevronRight size={20} className={styles.menuArrow} />
        </div>
        
        <div className={styles.menuItem} onClick={() => navigate('/personal-info')} style={{cursor: 'pointer'}}>
          <div className={styles.menuIcon}>
            <User size={20} />
          </div>
          <span className={styles.menuText}>Shaxsiy ma'lumotlar</span>
          <ChevronRight size={20} className={styles.menuArrow} />
        </div>

        <div className={styles.menuItem} onClick={() => navigate('/change-phone')} style={{cursor: 'pointer'}}>
          <div className={styles.menuIcon}>
            <Phone size={20} />
          </div>
          <span className={styles.menuText}>Telefon raqamni o'zgartirish</span>
          <ChevronRight size={20} className={styles.menuArrow} />
        </div>

        <div className={styles.menuItem}>
          <div className={styles.menuIcon}>
            <Bell size={20} />
          </div>
          <span className={styles.menuText}>Bildirishnomalar</span>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={notifications}
              onChange={(e) => setNotifications(e.target.checked)}
            />
            <span className={styles.toggleSlider}></span>
          </label>
        </div>

        <div className={styles.menuItem} onClick={() => navigate('/alarm-settings')} style={{cursor: 'pointer'}}>
          <div className={styles.menuIcon}>
            <Volume2 size={20} />
          </div>
          <span className={styles.menuText}>Alarm ovozini sozlash</span>
          <ChevronRight size={20} className={styles.menuArrow} />
        </div>
      </div>

      {/* Support */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>YORDAM</h3>
        
        <div className={styles.menuItem} onClick={() => navigate('/help-center')} style={{cursor: 'pointer'}}>
          <div className={styles.menuIcon}>
            <HelpCircle size={20} />
          </div>
          <span className={styles.menuText}>Yordam markazi</span>
          <ChevronRight size={20} className={styles.menuArrow} />
        </div>
      </div>

      {/* Logout */}
      <button className={styles.logoutButton} onClick={handleLogout}>
        <LogOut size={20} />
        <span>Chiqish</span>
      </button>

      <p className={styles.version}>Versiya 1.0.0</p>
    </div>
  )
}
