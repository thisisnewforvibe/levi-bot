import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import styles from './RegisterPage.module.css'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
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
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement registration logic
    console.log('Register:', formData)
    navigate('/')
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
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <button type="submit" className={styles.submitButton}>
            Boshlash
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
