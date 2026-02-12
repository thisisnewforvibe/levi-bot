import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Loader2 } from 'lucide-react'
import styles from './OtpVerifyPage.module.css'
import { authAPI } from '../services/api'

export default function OtpVerifyPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [resendTimer, setResendTimer] = useState(60)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])
  
  // Get data from navigation state
  const { phone, name, password, isLogin } = location.state || {}
  
  // Demo phone if no state (for testing)
  const displayPhone = phone || '+998 ** *** ** **'
  
  // Countdown timer for resend
  useEffect(() => {
    if (resendTimer > 0) {
      const timer = setTimeout(() => setResendTimer(resendTimer - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [resendTimer])
  
  // Format phone for display
  const formatPhone = (phoneNum: string) => {
    if (!phoneNum) return ''
    // Show last 4 digits
    return `***${phoneNum.slice(-4)}`
  }

  const handleChange = (index: number, value: string) => {
    // Only allow numbers
    if (!/^\d*$/.test(value)) return
    
    const newOtp = [...otp]
    newOtp[index] = value.slice(-1) // Only take last character
    setOtp(newOtp)
    setError('')
    
    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus()
    }
    
    // Auto-submit when all filled
    if (newOtp.every(digit => digit !== '') && newOtp.join('').length === 6) {
      handleVerify(newOtp.join(''))
    }
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    const newOtp = [...otp]
    for (let i = 0; i < pastedData.length; i++) {
      newOtp[i] = pastedData[i]
    }
    setOtp(newOtp)
    
    // Focus last filled input or next empty
    const lastIndex = Math.min(pastedData.length - 1, 5)
    inputRefs.current[lastIndex]?.focus()
    
    // Auto-submit if complete
    if (pastedData.length === 6) {
      handleVerify(pastedData)
    }
  }

  const handleVerify = async (otpCode: string) => {
    setIsLoading(true)
    setError('')
    
    try {
      const response = await authAPI.verifyOtp({
        phone,
        otp: otpCode,
        name,
        password,
        isLogin
      })
      
      if (response.success && response.token) {
        if (response.user) {
          localStorage.setItem('user', JSON.stringify(response.user))
        }
        navigate('/')
      } else {
        setError(response.message || 'Kod noto\'g\'ri')
        setOtp(['', '', '', '', '', ''])
        inputRefs.current[0]?.focus()
      }
    } catch (err) {
      console.error('OTP verification error:', err)
      setError('Server bilan bog\'lanishda xatolik')
      setOtp(['', '', '', '', '', ''])
      inputRefs.current[0]?.focus()
    } finally {
      setIsLoading(false)
    }
  }

  const handleResend = async () => {
    if (resendTimer > 0) return
    
    setIsLoading(true)
    setError('')
    
    try {
      const response = await authAPI.sendOtp({ phone })
      if (response.success) {
        setResendTimer(60)
        setOtp(['', '', '', '', '', ''])
        inputRefs.current[0]?.focus()
      } else {
        setError(response.message || 'Kod yuborishda xatolik')
      }
    } catch (err) {
      console.error('Resend OTP error:', err)
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
      </header>

      <div className={styles.content}>
        <h1 className={styles.title}>Tasdiqlash kodi</h1>
        <p className={styles.subtitle}>
          {formatPhone(displayPhone)} raqamiga yuborilgan 6 xonali kodni kiriting
        </p>

        {error && (
          <div className={styles.error}>
            {error}
          </div>
        )}

        <div className={styles.otpContainer} onPaste={handlePaste}>
          {otp.map((digit, index) => (
            <input
              key={index}
              ref={el => inputRefs.current[index] = el}
              type="tel"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              className={styles.otpInput}
              disabled={isLoading}
              autoFocus={index === 0}
            />
          ))}
        </div>

        <button 
          className={styles.verifyButton} 
          onClick={() => handleVerify(otp.join(''))}
          disabled={isLoading || otp.some(d => !d)}
        >
          {isLoading ? <Loader2 size={20} className="spin" /> : 'Tasdiqlash'}
        </button>

        <div className={styles.resendSection}>
          {resendTimer > 0 ? (
            <p className={styles.resendTimer}>
              Qayta yuborish: <span>{resendTimer}s</span>
            </p>
          ) : (
            <button className={styles.resendButton} onClick={handleResend} disabled={isLoading}>
              Kodni qayta yuborish
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
