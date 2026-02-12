import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2 } from 'lucide-react'
import styles from './EditProfilePage.module.css'
import { userAPI } from '../services/api'

export default function EditProfilePage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [formData, setFormData] = useState({
    name: '',
  })

  useEffect(() => {
    try {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        const user = JSON.parse(userStr)
        if (user.name) setFormData({ name: user.name })
      }
    } catch (e) {
      console.error('Failed to load user:', e)
    }
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
    setError('')
    setSuccess('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.name.trim()) {
      setError('Ism kiritilishi shart')
      return
    }
    
    setIsLoading(true)
    setError('')
    
    try {
      const success = await userAPI.updateProfile({ name: formData.name })
      
      if (success) {
        // Update localStorage
        const userStr = localStorage.getItem('user')
        if (userStr) {
          const user = JSON.parse(userStr)
          user.name = formData.name
          localStorage.setItem('user', JSON.stringify(user))
        }
        setSuccess('Muvaffaqiyatli saqlandi!')
        setTimeout(() => navigate(-1), 1000)
      } else {
        setError('Saqlashda xatolik yuz berdi')
      }
    } catch (err) {
      console.error('Update profile error:', err)
      setError('Server bilan bog\'lanishda xatolik')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button className={styles.backButton} onClick={() => navigate(-1)}>
          <ArrowLeft size={24} />
        </button>
        <h1 className={styles.title}>Profilni tahrirlash</h1>
      </header>

      <form className={styles.form} onSubmit={handleSubmit}>
        {error && <div className={styles.error}>{error}</div>}
        {success && <div className={styles.success}>{success}</div>}

        <div className={styles.inputGroup}>
          <label className={styles.label}>Ismingiz</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            placeholder="Ismingizni kiriting"
            className={styles.input}
            disabled={isLoading}
          />
        </div>

        <button type="submit" className={styles.submitButton} disabled={isLoading}>
          {isLoading ? <Loader2 size={20} className="spin" /> : 'Saqlash'}
        </button>
      </form>
    </div>
  )
}
