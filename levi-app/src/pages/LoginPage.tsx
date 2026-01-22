import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import styles from './LoginPage.module.css'

export default function LoginPage() {
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    phone: '',
    password: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement login logic
    console.log('Login:', formData)
    navigate('/')
  }

  return (
    <div className={styles.container}>
      {/* Welcome Text */}
      <div className={styles.welcomeSection}>
        <h2 className={styles.welcomeTitle}>Qaytib kelganingizdan xursandmiz! 👋</h2>
        <p className={styles.welcomeText}>
          Hisobingizga kiring va eslatmalaringizni boshqaring
        </p>
      </div>

      {/* Form Card */}
      <div className={styles.formCard}>
        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.inputGroup}>
            <input
              type="tel"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              placeholder="Telefon raqam"
              className={styles.input}
              required
            />
          </div>

          <div className={styles.inputGroup}>
            <div className={styles.passwordWrapper}>
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Parol"
                className={styles.input}
                required
              />
              <button
                type="button"
                className={styles.eyeButton}
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
              </button>
            </div>
          </div>

          <button type="submit" className={styles.submitButton}>
            Kirish
          </button>
        </form>

        <p className={styles.registerText}>
          Hisobingiz yo'qmi?{' '}
          <button
            type="button"
            className={styles.registerLink}
            onClick={() => navigate('/register')}
          >
            Ro'yxatdan o'tish
          </button>
        </p>
      </div>
    </div>
  )
}
