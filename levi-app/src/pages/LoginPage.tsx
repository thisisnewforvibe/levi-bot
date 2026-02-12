import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Loader2 } from 'lucide-react'
import styles from './LoginPage.module.css'
import { authAPI } from '../services/api'

export default function LoginPage() {
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    phone: '',
    password: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    
    try {
      // Send OTP to phone number
      const response = await authAPI.sendOtp({ phone: formData.phone })
      
      if (response.success) {
        // Navigate to OTP verification
        navigate('/verify-otp', { 
          state: { 
            phone: formData.phone,
            password: formData.password,
            isLogin: true
          }
        })
      } else {
        setError(response.message || 'Kod yuborishda xatolik')
      }
    } catch (err) {
      console.error('Send OTP error:', err)
      setError('Server bilan bog\'lanishda xatolik')
    } finally {
      setIsLoading(false)
    }
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
        {error && (
          <div style={{ 
            background: '#fee', 
            color: '#c00', 
            padding: '12px', 
            borderRadius: '8px', 
            marginBottom: '16px',
            fontSize: '14px'
          }}>
            {error}
          </div>
        )}
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
              disabled={isLoading}
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
                disabled={isLoading}
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

          <button type="submit" className={styles.submitButton} disabled={isLoading}>
            {isLoading ? <Loader2 size={20} className="spin" /> : 'Davom etish'}
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
