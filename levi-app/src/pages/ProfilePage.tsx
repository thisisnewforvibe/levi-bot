import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, User, Phone, Bell, Moon, HelpCircle, LogOut, ChevronRight } from 'lucide-react'
import styles from './ProfilePage.module.css'

export default function ProfilePage() {
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState(true)
  const [darkMode, setDarkMode] = useState(false)

  // Mock user data
  const user = {
    name: 'Aziz',
    phone: '+998 90 123 45 67',
  }

  const handleLogout = () => {
    // TODO: Implement logout logic
    console.log('Logout')
    navigate('/register')
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
          <h2 className={styles.userName}>{user.name}</h2>
          <p className={styles.userPhone}>{user.phone}</p>
        </div>
        <button className={styles.editButton}>
          Tahrirlash
        </button>
      </div>

      {/* Settings */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>SOZLAMALAR</h3>
        
        <div className={styles.menuItem}>
          <div className={styles.menuIcon}>
            <User size={20} />
          </div>
          <span className={styles.menuText}>Shaxsiy ma'lumotlar</span>
          <ChevronRight size={20} className={styles.menuArrow} />
        </div>

        <div className={styles.menuItem}>
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

        <div className={styles.menuItem}>
          <div className={styles.menuIcon}>
            <Moon size={20} />
          </div>
          <span className={styles.menuText}>Qorong'i rejim</span>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={darkMode}
              onChange={(e) => setDarkMode(e.target.checked)}
            />
            <span className={styles.toggleSlider}></span>
          </label>
        </div>
      </div>

      {/* Support */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>YORDAM</h3>
        
        <div className={styles.menuItem}>
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
