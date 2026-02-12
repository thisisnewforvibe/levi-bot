import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2 } from 'lucide-react'
import styles from './ChangePhonePage.module.css'
import { authAPI } from '../services/api'

type Step = 'phone' | 'otp'

export default function ChangePhonePage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('phone')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [newPhone, setNewPhone] = useState('')
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [resendTimer, setResendTimer] = useState(0)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [resendTimer])

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!newPhone.trim()) {
      setError('Telefon raqam kiritilishi shart')
      return
    }
    
    setIsLoading(true)
    setError('')
    
    try {
      const response = await authAPI.sendOtp({ phone: newPhone })
      if (response.success) {
        setStep('otp')
        setResendTimer(60)
        inputRefs.current[0]?.focus()
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

  const handleOtpChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return
    
    const newOtp = [...otp]
    newOtp[index] = value.slice(-1)
    setOtp(newOtp)
    setError('')
    
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus()
    }
    
    if (newOtp.every(digit => digit !== '') && newOtp.join('').length === 6) {
      handleVerifyOtp(newOtp.join(''))
    }
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handleVerifyOtp = async (_otpCode: string) => {
    setIsLoading(true)
    setError('')
    
    try {
      // For now, just simulate success - in production, call API to verify and update phone
      // const response = await userAPI.changePhone({ phone: newPhone, otp: _otpCode })
      
      // Update localStorage
      const userStr = localStorage.getItem('user')
      if (userStr) {
        const user = JSON.parse(userStr)
        user.phone = newPhone
        localStorage.setItem('user', JSON.stringify(user))
      }
      
      setSuccess('Telefon raqam muvaffaqiyatli o\'zgartirildi!')
      setTimeout(() => navigate(-1), 1500)
    } catch (err) {
      console.error('Verify OTP error:', err)
      setError('Kod noto\'g\'ri')
      setOtp(['', '', '', '', '', ''])
      inputRefs.current[0]?.focus()
    } finally {
      setIsLoading(false)
    }
  }

  const handleResend = async () => {
    if (resendTimer > 0) return
    
    setIsLoading(true)
    try {
      const response = await authAPI.sendOtp({ phone: newPhone })
      if (response.success) {
        setResendTimer(60)
        setOtp(['', '', '', '', '', ''])
        inputRefs.current[0]?.focus()
      }
    } catch (err) {
      setError('Kod yuborishda xatolik')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button className={styles.backButton} onClick={() => step === 'otp' ? setStep('phone') : navigate(-1)}>
          <ArrowLeft size={24} />
        </button>
        <h1 className={styles.title}>Telefon raqamni o'zgartirish</h1>
      </header>

      <div className={styles.content}>
        {error && <div className={styles.error}>{error}</div>}
        {success && <div className={styles.success}>{success}</div>}

        {step === 'phone' ? (
          <form onSubmit={handleSendOtp}>
            <p className={styles.description}>
              Yangi telefon raqamingizni kiriting. Tasdiqlash kodi yuboriladi.
            </p>
            
            <div className={styles.inputGroup}>
              <label className={styles.label}>Yangi telefon raqam</label>
              <input
                type="tel"
                value={newPhone}
                onChange={(e) => { setNewPhone(e.target.value); setError('') }}
                placeholder="+998 90 123 45 67"
                className={styles.input}
                disabled={isLoading}
              />
            </div>

            <button type="submit" className={styles.submitButton} disabled={isLoading}>
              {isLoading ? <Loader2 size={20} className="spin" /> : 'Davom etish'}
            </button>
          </form>
        ) : (
          <div className={styles.otpSection}>
            <p className={styles.description}>
              {newPhone} raqamiga yuborilgan 6 xonali kodni kiriting
            </p>

            <div className={styles.otpContainer}>
              {otp.map((digit, index) => (
                <input
                  key={index}
                  ref={el => inputRefs.current[index] = el}
                  type="tel"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleOtpChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  className={styles.otpInput}
                  disabled={isLoading}
                />
              ))}
            </div>

            <button 
              className={styles.submitButton} 
              onClick={() => handleVerifyOtp(otp.join(''))}
              disabled={isLoading || otp.some(d => !d)}
            >
              {isLoading ? <Loader2 size={20} className="spin" /> : 'Tasdiqlash'}
            </button>

            <div className={styles.resendSection}>
              {resendTimer > 0 ? (
                <p className={styles.resendTimer}>Qayta yuborish: {resendTimer}s</p>
              ) : (
                <button className={styles.resendButton} onClick={handleResend} disabled={isLoading}>
                  Kodni qayta yuborish
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
