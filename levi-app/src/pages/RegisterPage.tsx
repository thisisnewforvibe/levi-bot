import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Loader2, Check } from 'lucide-react'
import styles from './RegisterPage.module.css'
import { authAPI } from '../services/api'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
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
    
    if (!acceptedTerms) {
      setError('Oferta shartlarini qabul qilishingiz kerak')
      return
    }
    
    setIsLoading(true)
    setError('')
    
    try {
      // Send OTP to phone number
      const response = await authAPI.sendOtp({ phone: formData.phone })
      
      if (response.success) {
        // Navigate to OTP verification with form data
        navigate('/verify-otp', { 
          state: { 
            phone: formData.phone,
            name: formData.name,
            password: formData.password,
            isLogin: false
          }
        })
      } else {
        setError(response.message || "Kod yuborishda xatolik")
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
        <h2 className={styles.welcomeTitle}>Levi'ga Xush kelibsiz! 👋</h2>
        <p className={styles.welcomeText}>
          Eslatmalaringizni ovoz bilan yarating va hech qachon muhim ishlarni unutmang
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
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="Ismingiz"
              className={styles.input}
              required
              disabled={isLoading}
            />
          </div>

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
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          {/* Oferta Checkbox */}
          <div className={styles.checkboxGroup}>
            <label className={styles.checkboxLabel}>
              <div 
                className={`${styles.checkbox} ${acceptedTerms ? styles.checked : ''}`}
                onClick={() => setAcceptedTerms(!acceptedTerms)}
              >
                {acceptedTerms && <Check size={14} strokeWidth={3} />}
              </div>
              <span className={styles.checkboxText}>
                <a href="#" className={styles.ofertaLink} onClick={(e) => {
                  e.preventDefault()
                  // TODO: Open oferta page
                  alert('Oferta sahifasi')
                }}>Oferta shartlari</a>ni qabul qilaman
              </span>
            </label>
          </div>

          <button type="submit" className={styles.submitButton} disabled={isLoading}>
            {isLoading ? <Loader2 size={20} className="spin" /> : 'Davom etish'}
          </button>
        </form>

        <p className={styles.loginText}>
          Hisobingiz bormi?{' '}
          <button
            type="button"
            className={styles.loginLink}
            onClick={() => navigate('/login')}
          >
            Kirish
          </button>
        </p>
      </div>
    </div>
  )
}
