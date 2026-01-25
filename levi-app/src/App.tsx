import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'
import LoginPage from './pages/LoginPage'
import { notificationService } from './services/notifications'
import { remindersAPI } from './services/api'

function App() {
  // Initialize notification service on app start
  useEffect(() => {
    const initNotifications = async () => {
      try {
        // Create alarm channel (Android)
        await notificationService.createAlarmChannel()
        
        // Register action types (Done, Snooze, Yes, No buttons)
        await notificationService.registerActionTypes()
        
        // Set up action callback to handle user responses
        notificationService.setActionCallback(async (reminderId, action) => {
          console.log(`Notification action: ${action} for reminder ${reminderId}`)
          
          if (action === 'done' || action === 'yes') {
            // User completed the task - update status in backend
            try {
              const success = await remindersAPI.updateStatus(reminderId, 'done')
              if (success) {
                console.log(`✓ Reminder ${reminderId} marked as done`)
              }
            } catch (error) {
              console.error('Failed to update reminder status:', error)
            }
          }
          // For 'snooze' and 'no' - the notification service handles scheduling
        })
        
        // Initialize and request permissions
        const success = await notificationService.initialize()
        if (success) {
          console.log('✓ Alarm notifications with follow-ups ready')
        } else {
          console.warn('⚠ Notifications not available')
        }
      } catch (error) {
        console.error('Failed to initialize notifications:', error)
      }
    }

    initNotifications()
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
