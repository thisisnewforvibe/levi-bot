import { X, Crown, Check } from 'lucide-react'
import styles from './SubscriptionModal.module.css'

interface SubscriptionModalProps {
  isOpen: boolean
  onClose: () => void
  onSubscribe: () => void
}

export default function SubscriptionModal({ isOpen, onClose, onSubscribe }: SubscriptionModalProps) {
  if (!isOpen) return null

  const features = [
    'Cheksiz eslatmalar',
    'Takrorlanuvchi eslatmalar',
    'Bulutda sinxronizatsiya',
    'Reklamansiz',
    'Ustuvor yordam',
  ]

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <button className={styles.closeButton} onClick={onClose}>
          <X size={24} />
        </button>

        <div className={styles.iconWrapper}>
          <Crown size={40} className={styles.crownIcon} />
        </div>

        <h2 className={styles.title}>Premium obuna</h2>
        
        <p className={styles.description}>
          Bepul rejada faqat 1 ta eslatma yaratish mumkin. Ko'proq eslatmalar uchun Premium obunaga o'ting!
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

        <button className={styles.subscribeButton} onClick={onSubscribe}>
          Obuna bo'lish
        </button>

        <button className={styles.laterButton} onClick={onClose}>
          Keyinroq
        </button>
      </div>
    </div>
  )
}
