import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'
import LoginPage from './pages/LoginPage'
import OtpVerifyPage from './pages/OtpVerifyPage'
import EditProfilePage from './pages/EditProfilePage'
import PersonalInfoPage from './pages/PersonalInfoPage'
import ChangePhonePage from './pages/ChangePhonePage'
import AlarmSettingsPage from './pages/AlarmSettingsPage'
import HelpCenterPage from './pages/HelpCenterPage'
import SubscriptionPage from './pages/SubscriptionPage'
import { notificationService } from './services/notifications'
import { remindersAPI, authAPI, DEV_MOCK_AUTH } from './services/api'

// Protected Route component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = authAPI.isAuthenticated()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}

function App() {
  const [isReady, setIsReady] = useState(false)

  // Initialize notification service on app start
  useEffect(() => {
    const initApp = async () => {
      try {
        // If in dev mock mode, inject mock user data
        if (DEV_MOCK_AUTH) {
          localStorage.setItem('auth_token', 'mock_token_for_testing');
          localStorage.setItem('user', JSON.stringify({
            id: 1,
            phone: '+998901234567',
            name: 'Test User',
            timezone: 'Asia/Tashkent',
          }));
        }

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
      
      setIsReady(true)
    }

    initApp()
  }, [])

  if (!isReady) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        background: '#fff'
      }}>
        <div style={{ textAlign: 'center' }}>
          <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>Levi</h1>
          <p>Yuklanmoqda...</p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-otp" element={<OtpVerifyPage />} />
        <Route path="/" element={
          <ProtectedRoute>
            <HomePage />
          </ProtectedRoute>
        } />
        <Route path="/profile" element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        } />
        <Route path="/edit-profile" element={
          <ProtectedRoute>
            <EditProfilePage />
          </ProtectedRoute>
        } />
        <Route path="/personal-info" element={
          <ProtectedRoute>
            <PersonalInfoPage />
          </ProtectedRoute>
        } />
        <Route path="/change-phone" element={
          <ProtectedRoute>
            <ChangePhonePage />
          </ProtectedRoute>
        } />
        <Route path="/alarm-settings" element={
          <ProtectedRoute>
            <AlarmSettingsPage />
          </ProtectedRoute>
        } />
        <Route path="/help-center" element={
          <ProtectedRoute>
            <HelpCenterPage />
          </ProtectedRoute>
        } />
        <Route path="/subscription" element={
          <ProtectedRoute>
            <SubscriptionPage />
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  )
}

export default App
