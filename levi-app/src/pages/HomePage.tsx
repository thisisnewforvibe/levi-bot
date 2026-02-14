import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Check, User, Loader2 } from 'lucide-react'
import styles from './HomePage.module.css'
import RecordingModal from '../components/RecordingModal'
import SubscriptionModal from '../components/SubscriptionModal'
import { voiceAPI, remindersAPI, Reminder as APIReminder } from '../services/api'
import { notificationService, reminderToAlarm } from '../services/notifications'
import { LeviAlarmManager, checkOverlayPermission, requestOverlayPermission } from '../services/leviAlarm'
import { App } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'

interface Reminder {
  id: string
  title: string
  description: string
  duration: string
  date: string
  time: string
  timestamp: number
  isToday: boolean
  isDone: boolean
  notes?: string
  location?: string
  recurrence_type?: string
}

type FilterType = 'all' | 'pending' | 'done'

export default function HomePage() {
  const navigate = useNavigate()
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [userName, setUserName] = useState('Foydalanuvchi')
  const [alarmPermissionNeeded, setAlarmPermissionNeeded] = useState(false)
  const [overlayPermissionNeeded, setOverlayPermissionNeeded] = useState(false)
  const [showSubscriptionModal, setShowSubscriptionModal] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const filters: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'Hammasi' },
    { key: 'pending', label: 'Kutilmoqda' },
    { key: 'done', label: 'Bajarildi' },
  ]

  // Recheck permissions when app resumes (after returning from settings)
  useEffect(() => {
    const listener = App.addListener('appStateChange', async ({ isActive }) => {
      if (isActive && Capacitor.getPlatform() === 'android') {
        // Recheck overlay permission (Android only)
        const hasOverlay = await checkOverlayPermission()
        if (hasOverlay) {
          setOverlayPermissionNeeded(false)
        }
        // Recheck alarm permission (Android only)
        try {
          const result = await LeviAlarmManager.canScheduleExactAlarms()
          if (result.canSchedule) {
            setAlarmPermissionNeeded(false)
          }
        } catch (e) {
          console.error('Error rechecking alarm permission:', e)
        }
      }
    })
    
    return () => {
      listener.then(l => l.remove())
    }
  }, [])

  // Check alarm permission and load data on mount
  useEffect(() => {
    // Android-only: Check exact alarm and overlay permissions
    if (Capacitor.getPlatform() === 'android') {
      const checkAlarmPermission = async () => {
        try {
          const result = await LeviAlarmManager.canScheduleExactAlarms()
          console.log('Alarm permission check:', result)
          if (!result.canSchedule) {
            setAlarmPermissionNeeded(true)
          }
        } catch (e) {
          console.error('Error checking alarm permission:', e)
        }
      }
      checkAlarmPermission()
      
      const checkOverlay = async () => {
        try {
          const hasOverlay = await checkOverlayPermission()
          console.log('Overlay permission check:', hasOverlay)
          if (!hasOverlay) {
            setOverlayPermissionNeeded(true)
            
            const overlayAsked = localStorage.getItem('overlayPermissionAsked')
            if (!overlayAsked) {
              localStorage.setItem('overlayPermissionAsked', 'true')
              setTimeout(async () => {
                alert('⚠️ To\'liq ekran eslatma uchun ruxsat kerak!\n\nSozlamalarda "Levi" ilovasini toping va "Boshqa ilovalar ustida ko\'rsatish" ni yoqing.')
                await requestOverlayPermission()
              }, 500)
            }
          }
        } catch (e) {
          console.error('Error checking overlay permission:', e)
        }
      }
      checkOverlay()
    }
    
    // Get user name from localStorage
    try {
      const userStr = localStorage.getItem('user')
      if (userStr) {
        const user = JSON.parse(userStr)
        if (user.name) {
          setUserName(user.name)
        }
      }
    } catch (e) {
      console.error('Failed to parse user:', e)
    }
    
    loadReminders()
  }, [])

  // Handle opening alarm settings
  const handleEnableAlarms = async () => {
    try {
      await LeviAlarmManager.openAlarmSettings()
      setSuccessMessage('⚙️ Sozlamalarda "Levi" uchun ruxsat bering')
      setTimeout(() => setSuccessMessage(null), 5000)
    } catch (e) {
      console.error('Error opening alarm settings:', e)
    }
  }

  // Handle opening overlay settings
  const handleEnableOverlay = async () => {
    try {
      await requestOverlayPermission()
      setSuccessMessage('⚙️ "Boshqa ilovalar ustida ko\'rsatish" ni yoqing')
      setTimeout(() => setSuccessMessage(null), 5000)
    } catch (e) {
      console.error('Error opening overlay settings:', e)
    }
  }

  const loadReminders = async () => {
    try {
      setIsLoading(true)
      const apiReminders = await remindersAPI.getAll()
      const mapped = apiReminders.map((r: APIReminder) => mapAPIReminder(r))
      setReminders(mapped)
      
      // Schedule alarms for all pending reminders
      const pendingReminders = apiReminders.filter(r => r.status === 'pending')
      await scheduleAlarmsForReminders(pendingReminders)
    } catch (error) {
      console.error('Failed to load reminders:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Schedule alarm notifications for reminders
  const scheduleAlarmsForReminders = async (apiReminders: APIReminder[]) => {
    try {
      // Cancel existing alarms first to avoid duplicates
      console.log('Cancelling all existing alarms...')
      await notificationService.cancelAllAlarms()
      
      // Schedule alarms for future reminders only
      // Must be at least 10 seconds in the future to avoid race conditions
      const now = new Date()
      const minBufferMs = 10000  // 10 seconds minimum
      console.log(`Current time: ${now.toLocaleString()} (timestamp: ${now.getTime()})`)
      
      const futureReminders = apiReminders.filter(r => {
        // Ensure UTC time is parsed correctly
        let utcTimeStr = r.scheduled_time_utc
        if (!utcTimeStr.endsWith('Z') && !utcTimeStr.includes('+')) {
          utcTimeStr = utcTimeStr + 'Z'
        }
        const scheduledTime = new Date(utcTimeStr)
        const diffMs = scheduledTime.getTime() - now.getTime()
        const isFuture = diffMs > minBufferMs  // Must be more than 10 seconds in future
        console.log(`Reminder ${r.id}: "${r.task_text}"`)
        console.log(`  - UTC string: ${r.scheduled_time_utc}`)
        console.log(`  - Parsed time: ${scheduledTime.toLocaleString()} (timestamp: ${scheduledTime.getTime()})`)
        console.log(`  - Diff: ${diffMs}ms (${Math.round(diffMs/1000)}s, ${Math.round(diffMs/60000)}min)`)
        console.log(`  - Is future (>10s): ${isFuture}`)
        return isFuture
      })

      if (futureReminders.length > 0) {
        const alarms = futureReminders.map(r => reminderToAlarm(r))
        console.log(`Scheduling ${alarms.length} alarms with native AlarmManager...`)
        await notificationService.scheduleMultipleAlarms(alarms)
        console.log(`✓ Scheduled ${alarms.length} alarm notifications`)
      } else {
        console.log('No future reminders to schedule (all are past or too close)')
      }
    } catch (error) {
      console.error('Failed to schedule alarms:', error)
    }
  }

  const mapAPIReminder = (r: APIReminder): Reminder => {
    // Ensure the UTC time is parsed correctly by adding Z suffix if not present
    let utcTimeStr = r.scheduled_time_utc
    if (!utcTimeStr.endsWith('Z') && !utcTimeStr.includes('+')) {
      utcTimeStr = utcTimeStr + 'Z'
    }
    const scheduledDate = new Date(utcTimeStr)
    const now = new Date()
    const isToday = scheduledDate.toDateString() === now.toDateString()
    
    // Get yesterday's date
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const isYesterday = scheduledDate.toDateString() === yesterday.toDateString()
    
    // Format date text
    let dateText = scheduledDate.toLocaleDateString('uz-UZ')
    if (isToday) {
      dateText = 'Bugun'
    } else if (isYesterday) {
      dateText = 'Kecha'
    }
    
    return {
      id: String(r.id),
      title: r.task_text,
      description: r.notes || r.task_text,
      duration: '00:00',
      date: dateText,
      time: scheduledDate.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' }),
      timestamp: new Date(r.created_at).getTime(),
      isToday,
      isDone: r.status === 'done',
    }
  }

  // Check if user has active subscription
  const isSubscribed = (): boolean => {
    try {
      const sub = localStorage.getItem('subscription')
      if (sub) {
        const { active } = JSON.parse(sub)
        return active === true
      }
    } catch (e) {
      console.error('Failed to check subscription:', e)
    }
    return false
  }

  // Count pending (non-done) reminders
  const getPendingReminderCount = (): number => {
    return reminders.filter(r => !r.isDone).length
  }

  const handleRecordClick = () => {
    // Check subscription - only 1 free reminder allowed
    const pendingCount = getPendingReminderCount()
    if (pendingCount >= 1 && !isSubscribed()) {
      setShowSubscriptionModal(true)
      return
    }
    setIsRecording(true)
  }

  const handleRecordingClose = () => {
    setIsRecording(false)
  }

  const handleRecordingStop = async (audioBlob: Blob, duration: number) => {
    console.log('Recording stopped, blob size:', audioBlob.size, 'duration:', duration)
    setIsRecording(false)
    setIsProcessing(true)

    try {
      // Send audio to voice API
      const result = await voiceAPI.createFromVoice(audioBlob, 'uz')
      
      if (result.success && result.reminders) {
        console.log('Transcription:', result.transcription)
        console.log('Created reminders:', result.reminders)
        
        // Show success message
        const count = result.reminders?.length || 0
        setSuccessMessage(`✅ ${count} ta eslatma yaratildi!`)
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
          setSuccessMessage(null)
        }, 3000)
        
        // Reload reminders from API
        await loadReminders()
      } else {
        // Show error message
        setSuccessMessage(`❌ ${result.message || 'Eslatma yaratib bo\'lmadi'}`)
        setTimeout(() => {
          setSuccessMessage(null)
        }, 3000)
      }
    } catch (error) {
      console.error('Voice processing failed:', error)
      setSuccessMessage('❌ Ovozni qayta ishlashda xatolik yuz berdi')
      setTimeout(() => {
        setSuccessMessage(null)
      }, 3000)
    } finally {
      setIsProcessing(false)
    }
  }

  const toggleReminderDone = async (id: string) => {
    const reminder = reminders.find(r => r.id === id)
    if (!reminder) return
    
    const newStatus = reminder.isDone ? 'pending' : 'done'
    
    // Update locally first for instant feedback
    setReminders(prev => 
      prev.map(r => r.id === id ? { ...r, isDone: !r.isDone } : r)
    )
    
    // Update on server
    try {
      await remindersAPI.updateStatus(Number(id), newStatus)
    } catch (error) {
      console.error('Failed to update reminder status:', error)
      // Revert on error
      setReminders(prev => 
        prev.map(r => r.id === id ? { ...r, isDone: reminder.isDone } : r)
      )
    }
  }

  const filteredReminders = reminders.filter(r => {
    if (activeFilter === 'pending') return !r.isDone
    if (activeFilter === 'done') return r.isDone
    return true
  })

  // Sort: active first, then by creation date (newest created at top)
  const sortedReminders = [...filteredReminders].sort((a, b) => {
    if (a.isDone !== b.isDone) return a.isDone ? 1 : -1
    return b.timestamp - a.timestamp
  })

  const groupedReminders = sortedReminders.reduce((acc, reminder) => {
    const key = reminder.isToday ? 'Bugun' : reminder.date
    if (!acc[key]) acc[key] = []
    acc[key].push(reminder)
    return acc
  }, {} as Record<string, Reminder[]>)

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.profileSection}>
          <div className={styles.greetingText}>
            <div className={styles.greetingLabel}>XUSH KELIBSIZ</div>
            <div className={styles.greetingName}>Salom, {userName}</div>
          </div>
          <button className={styles.profileButton} onClick={() => navigate('/profile')}>
            <User size={22} strokeWidth={1.5} />
          </button>
        </div>
      </header>

      {/* Alarm Permission Warning */}
      {alarmPermissionNeeded && (
        <div style={{
          background: '#ff4444',
          color: 'white',
          padding: '12px 16px',
          margin: '0 16px 16px',
          borderRadius: '8px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px'
        }}>
          <span style={{ fontSize: '14px' }}>
            ⚠️ Eslatmalar ishlashi uchun ruxsat kerak!
          </span>
          <button
            onClick={handleEnableAlarms}
            style={{
              background: 'white',
              color: '#ff4444',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              fontWeight: 'bold',
              fontSize: '13px',
              whiteSpace: 'nowrap'
            }}
          >
            Yoqish
          </button>
        </div>
      )}

      {/* Overlay Permission Warning (for full-screen alarm) */}
      {overlayPermissionNeeded && (
        <div style={{
          background: '#f59e0b',
          color: 'white',
          padding: '12px 16px',
          margin: '0 16px 16px',
          borderRadius: '8px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px'
        }}>
          <span style={{ fontSize: '14px' }}>
            📱 To'liq ekran eslatma uchun ruxsat kerak
          </span>
          <button
            onClick={handleEnableOverlay}
            style={{
              background: 'white',
              color: '#f59e0b',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              fontWeight: 'bold',
              fontSize: '13px',
              whiteSpace: 'nowrap'
            }}
          >
            Yoqish
          </button>
        </div>
      )}

      {/* Search */}
      <div className={styles.searchContainer}>
        <div className={styles.searchBox}>
          <Search size={18} className={styles.searchIcon} />
          <input
            type="text"
            placeholder="Qidirish"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
        </div>
      </div>

      {/* Filter Tabs */}
      <div className={styles.filters}>
        {filters.map((filter) => (
          <button
            key={filter.key}
            className={`${styles.filterButton} ${activeFilter === filter.key ? styles.filterActive : ''}`}
            onClick={() => setActiveFilter(filter.key)}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Reminders List */}
      <div className={styles.remindersList}>
        {/* Success Message Toast */}
        {successMessage && (
          <div className={styles.successToast}>
            <span>{successMessage}</span>
          </div>
        )}

        {/* Skeleton Loading */}
        {isLoading && (
          <div className={styles.skeletonGroup}>
            <div className={styles.skeletonDateHeader}>
              <div className={styles.skeletonLine} style={{ width: '60px', height: '14px' }} />
              <div className={styles.skeletonLine} style={{ width: '40px', height: '14px' }} />
            </div>
            {[1, 2, 3].map((i) => (
              <div key={i} className={styles.skeletonCard}>
                <div className={styles.skeletonLine} style={{ width: '70%', height: '17px', marginBottom: '8px' }} />
                <div className={styles.skeletonLine} style={{ width: '100%', height: '14px', marginBottom: '6px' }} />
                <div className={styles.skeletonLine} style={{ width: '85%', height: '14px', marginBottom: '14px' }} />
                <div className={styles.skeletonFooter}>
                  <div className={styles.skeletonLine} style={{ width: '60px', height: '14px' }} />
                  <div className={styles.skeletonCircle} />
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && Object.entries(groupedReminders).map(([date, reminders]) => (
          <div key={date} className={styles.reminderGroup}>
            <div className={styles.dateHeader}>
              <span className={styles.dateText}>{date}</span>
              <span className={styles.timeText}>{reminders[0]?.time}</span>
            </div>
            {reminders.map((reminder) => (
              <div key={reminder.id} className={`${styles.reminderCard} ${reminder.isDone ? styles.reminderDone : ''}`}>
                <h3 className={styles.reminderTitle}>{reminder.title}</h3>
                <p className={styles.reminderDescription}>{reminder.description}</p>
                <div className={styles.reminderFooter}>
                  <span className={styles.reminderTime}>⏰ {reminder.time}</span>
                  <button 
                    className={`${styles.checkButton} ${reminder.isDone ? styles.checkButtonDone : ''}`}
                    onClick={() => toggleReminderDone(reminder.id)}
                  >
                    {reminder.isDone && <Check size={14} strokeWidth={3} />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Record Button */}
      <div className={styles.recordContainer}>
        <button 
          className={styles.recordButton}
          onClick={handleRecordClick}
          disabled={isProcessing}
        >
          {isProcessing ? (
            <>
              <Loader2 size={16} className={styles.spinner} />
              <span>Yuklanmoqda...</span>
            </>
          ) : (
            <>
              <div className={styles.recordDot} />
              <span>Yozib olish</span>
            </>
          )}
        </button>
      </div>

      {/* Recording Modal */}
      <RecordingModal
        isOpen={isRecording}
        onClose={handleRecordingClose}
        onStop={handleRecordingStop}
      />

      {/* Subscription Modal */}
      <SubscriptionModal
        isOpen={showSubscriptionModal}
        onClose={() => setShowSubscriptionModal(false)}
        onSubscribe={() => {
          setShowSubscriptionModal(false)
          navigate('/subscription')
        }}
      />
    </div>
  )
}
