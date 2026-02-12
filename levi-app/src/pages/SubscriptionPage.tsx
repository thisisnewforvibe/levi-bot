import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Crown, Check, AlertCircle } from 'lucide-react'
import styles from './SubscriptionPage.module.css'

export default function SubscriptionPage() {
  const navigate = useNavigate()
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [subscriptionEnd, setSubscriptionEnd] = useState<string | null>(null)
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)

  useEffect(() => {
    // Check subscription status from localStorage
    const subStatus = localStorage.getItem('subscription')
    if (subStatus) {
      const sub = JSON.parse(subStatus)
      setIsSubscribed(sub.active)
      setSubscriptionEnd(sub.endDate)
    }
  }, [])

  const handleSubscribe = () => {
    // In production, integrate with payment provider (Click, Payme, etc.)
    // For now, simulate subscription
    const endDate = new Date()
    endDate.setMonth(endDate.getMonth() + 1)
    
    const subscription = {
      active: true,
      startDate: new Date().toISOString(),
      endDate: endDate.toISOString()
    }
    
    localStorage.setItem('subscription', JSON.stringify(subscription))
    setIsSubscribed(true)
    setSubscriptionEnd(endDate.toISOString())
    
    alert('Obuna muvaffaqiyatli faollashtirildi! ✅')
  }

  const handleCancelSubscription = () => {
    localStorage.removeItem('subscription')
    setIsSubscribed(false)
    setSubscriptionEnd(null)
    setShowCancelConfirm(false)
    alert('Obuna bekor qilindi')
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const day = date.getDate()
    const year = date.getFullYear()
    const months = [
      'yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun',
      'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'
    ]
    const month = months[date.getMonth()]
    return `${day} ${month} ${year}`
  }

  const features = [
    'Cheksiz eslatmalar',
    'Takrorlanuvchi eslatmalar',
    'Bulutda sinxronizatsiya',
    'Reklamansiz',
    'Ustuvor yordam',
  ]

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button className={styles.backButton} onClick={() => navigate(-1)}>
          <ArrowLeft size={24} />
        </button>
        <h1 className={styles.title}>Obuna</h1>
      </header>

      <div className={styles.content}>
        {isSubscribed ? (
          <>
            {/* Active Subscription Card */}
            <div className={styles.activeCard}>
              <div className={styles.activeBadge}>
                <Crown size={20} />
                <span>Premium</span>
              </div>
              <h2 className={styles.activeTitle}>Obuna faol</h2>
              <p className={styles.activeDate}>
                {subscriptionEnd && `${formatDate(subscriptionEnd)} gacha`}
              </p>
            </div>

            <ul className={styles.features}>
              {features.map((feature, index) => (
                <li key={index} className={styles.featureItem}>
                  <Check size={18} className={styles.checkIcon} />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>

            <button 
              className={styles.cancelButton}
              onClick={() => setShowCancelConfirm(true)}
            >
              Obunani bekor qilish
            </button>
          </>
        ) : (
          <>
            {/* Premium Offer */}
            <div className={styles.iconWrapper}>
              <Crown size={48} className={styles.crownIcon} />
            </div>

            <h2 className={styles.offerTitle}>Premium obuna</h2>
            <p className={styles.offerDescription}>
              Barcha imkoniyatlardan cheksiz foydalaning
            </p>

            <div className={styles.priceCard}>
              <span className={styles.price}>19 900</span>
              <span className={styles.currency}>so'm/oy</span>
            </div>

            <ul className={styles.features}>
              {features.map((feature, index) => (
                <li key={index} className={styles.featureItem}>
                  <Check size={18} className={styles.checkIcon} />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>

            <div className={styles.freeInfo}>
              <AlertCircle size={18} />
              <span>Bepul rejada faqat 1 ta eslatma</span>
            </div>

            <button className={styles.subscribeButton} onClick={handleSubscribe}>
              Obuna bo'lish
            </button>
          </>
        )}
      </div>

      {/* Cancel Confirmation Modal */}
      {showCancelConfirm && (
        <div className={styles.overlay} onClick={() => setShowCancelConfirm(false)}>
          <div className={styles.confirmModal} onClick={e => e.stopPropagation()}>
            <h3 className={styles.confirmTitle}>Obunani bekor qilish</h3>
            <p className={styles.confirmText}>
              Haqiqatan ham obunani bekor qilmoqchimisiz? Barcha premium imkoniyatlar o'chiriladi.
            </p>
            <div className={styles.confirmButtons}>
              <button 
                className={styles.confirmCancel}
                onClick={() => setShowCancelConfirm(false)}
              >
                Yo'q, saqlab qolish
              </button>
              <button 
                className={styles.confirmDelete}
                onClick={handleCancelSubscription}
              >
                Ha, bekor qilish
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
