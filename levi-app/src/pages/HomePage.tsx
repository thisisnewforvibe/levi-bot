import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Play, Check, User, Loader2 } from 'lucide-react'
import styles from './HomePage.module.css'
import RecordingModal from '../components/RecordingModal'
import { voiceAPI, remindersAPI, Reminder as APIReminder } from '../services/api'

interface Reminder {
  id: string
  title: string
  description: string
  duration: string
  date: string
  time: string
  isToday: boolean
  isDone: boolean
  notes?: string
  location?: string
  recurrence_type?: string
}

// Mock data for demonstration
const initialReminders: Reminder[] = [
  {
    id: '1',
    title: 'Darsga borish',
    description: 'Bugun soat 15:30 da darsga borishim kerak, matematika darsi bo\'ladi.',
    duration: '00:13',
    date: 'Bugun',
    time: '13:18',
    isToday: true,
    isDone: false,
  },
  {
    id: '2',
    title: 'Dorixonaga borish',
    description: 'Ertaga ertalab dorixonaga borib, dori olishim kerak. Aspirin va vitamin D.',
    duration: '00:08',
    date: 'Kecha',
    time: '16:31',
    isToday: false,
    isDone: false,
  },
  {
    id: '3',
    title: 'Namoz o\'qish',
    description: 'Peshin namozini o\'qishni unutma.',
    duration: '00:05',
    date: 'Kecha',
    time: '12:00',
    isToday: false,
    isDone: false,
  },
]

type FilterType = 'all' | 'pending' | 'done'

export default function HomePage() {
  const navigate = useNavigate()
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [reminders, setReminders] = useState<Reminder[]>(initialReminders)

  const filters: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'Hammasi' },
    { key: 'pending', label: 'Kutilmoqda' },
    { key: 'done', label: 'Bajarildi' },
  ]

  // Load reminders from API on mount
  useEffect(() => {
    loadReminders()
  }, [])

  const loadReminders = async () => {
    try {
      const apiReminders = await remindersAPI.getAll()
      const mapped = apiReminders.map((r: APIReminder) => mapAPIReminder(r))
      if (mapped.length > 0) {
        setReminders(mapped)
      }
    } catch (error) {
      console.error('Failed to load reminders:', error)
    }
  }

  const mapAPIReminder = (r: APIReminder): Reminder => {
    const scheduledDate = new Date(r.scheduled_time_utc)
    const now = new Date()
    const isToday = scheduledDate.toDateString() === now.toDateString()
    
    return {
      id: String(r.id),
      title: r.task_text,
      description: r.task_text,
      duration: '00:00',
      date: isToday ? 'Bugun' : scheduledDate.toLocaleDateString('uz-UZ'),
      time: scheduledDate.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' }),
      isToday,
      isDone: r.status === 'done',
    }
  }

  const handleRecordClick = () => {
    setIsRecording(true)
  }

  const handleRecordingClose = () => {
    setIsRecording(false)
  }

  const handleRecordingStop = async (audioBlob: Blob) => {
    console.log('Recording stopped, blob size:', audioBlob.size)
    setIsRecording(false)
    setIsProcessing(true)

    try {
      // Send audio to voice API
      const result = await voiceAPI.createFromVoice(audioBlob, 'uz')
      
      if (result.success && result.reminders) {
        console.log('Transcription:', result.transcription)
        console.log('Created reminders:', result.reminders)
        
        // Reload reminders from API
        await loadReminders()
        
        // Show success message
        alert(`✅ ${result.reminders.length} ta eslatma yaratildi!\n\n"${result.transcription}"`)
      } else {
        alert(`❌ ${result.message || 'Eslatma yaratib bo\'lmadi'}`)
      }
    } catch (error) {
      console.error('Voice processing failed:', error)
      alert('❌ Ovozni qayta ishlashda xatolik yuz berdi')
    } finally {
      setIsProcessing(false)
    }
  }

  const toggleReminderDone = (id: string) => {
    setReminders(prev => 
      prev.map(r => r.id === id ? { ...r, isDone: !r.isDone } : r)
    )
  }

  const filteredReminders = reminders.filter(r => {
    if (activeFilter === 'pending') return !r.isDone
    if (activeFilter === 'done') return r.isDone
    return true
  })

  const groupedReminders = filteredReminders.reduce((acc, reminder) => {
    const key = reminder.isToday ? 'Bugun' : reminder.date
    if (!acc[key]) acc[key] = []
    acc[key].push(reminder)
    return acc
  }, {} as Record<string, Reminder[]>)

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <h1 className={styles.title}>Levi</h1>
        <div className={styles.profileSection}>
          <div className={styles.greetingText}>
            <div className={styles.greetingLabel}>XUSH KELIBSIZ</div>
            <div className={styles.greetingName}>Salom, Aziz</div>
          </div>
          <button className={styles.profileButton} onClick={() => navigate('/profile')}>
            <User size={22} strokeWidth={1.5} />
          </button>
        </div>
      </header>

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
        {Object.entries(groupedReminders).map(([date, reminders]) => (
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
                  <button className={styles.playButton}>
                    <Play size={14} fill="currentColor" />
                    <span>{reminder.duration}</span>
                  </button>
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
              <span>Record</span>
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
    </div>
  )
}
