# Google AI Studio Prompt for Levi Web App

## 🌐 Copy and paste this entire prompt into Google AI Studio:

---

# BUILD WEB SPA: "LEVI" - Voice Reminder App

## PROJECT OVERVIEW

Build a complete Single Page Application (SPA) called **"Levi"** - an AI-powered voice reminder application for Uzbekistan users. The app allows users to record voice messages, automatically transcribes them, extracts reminder tasks and times using AI, and sends browser/push notifications.

**Target Platform:** Web SPA (Progressive Web App - PWA)
**Framework:** React + TypeScript + Vite
**Languages:** Uzbek and Russian (bilingual UI)
**Design Style:** Clean, minimal, modern - inspired by SpeakApp and Voicenotes apps

---

## DESIGN SYSTEM

### Color Palette
```css
:root {
  /* Primary Colors */
  --primary-blue: #4A90E2;      /* Main accent (like SpeakApp banner) */
  --primary-green: #4CAF50;     /* Success/Done button */
  --primary-red: #E57373;       /* Cancel/Delete */
  --background-white: #FAFAFA;  /* Main background */
  --card-white: #FFFFFF;        /* Card backgrounds */
  --text-primary: #1A1A1A;      /* Main text */
  --text-secondary: #757575;    /* Secondary text */
  --divider-gray: #E0E0E0;      /* Dividers */
  
  /* Gradient for premium banner */
  --premium-gradient: linear-gradient(90deg, #4A90E2, #7B68EE);
}
```

### Typography
```css
/* Use Google Fonts - Inter */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

/* Headlines: Bold, 24-28px */
/* Body: Regular, 16px */
/* Caption: Regular, 14px */
/* Small: Regular, 12px */
```

### Design Principles
1. **Generous whitespace** - Like Voicenotes
2. **Rounded corners** - 12-16px radius on cards and buttons
3. **Subtle shadows** - Elevation 2-4 for cards
4. **Large touch targets** - Minimum 48x48 for buttons
5. **Floating action button** - Large microphone button at bottom center

---

## APP STRUCTURE & SCREENS

### 1. SPLASH SCREEN
```
┌─────────────────────────────────┐
│                                 │
│                                 │
│           [Levi Logo]           │
│                                 │
│        "Ovozli eslatmalar"      │
│     "Голосовые напоминания"     │
│                                 │
│         [Loading...]            │
│                                 │
└─────────────────────────────────┘
```

### 2. ONBOARDING SCREENS (3 screens with PageView)

**Screen 1: Voice Recording**
```
┌─────────────────────────────────┐
│                                 │
│     [Microphone Illustration]   │
│                                 │
│    "Ovozingiz bilan eslatma     │
│         yarating"               │
│   "Создавайте напоминания       │
│         голосом"                │
│                                 │
│         ● ○ ○                   │
│                                 │
│      [Keyingi / Далее →]        │
└─────────────────────────────────┘
```

**Screen 2: AI Parsing**
```
┌─────────────────────────────────┐
│                                 │
│       [AI Brain Illustration]   │
│                                 │
│   "AI avtomatik vaqtni aniqlaydi"│
│   "ИИ автоматически определяет  │
│            время"               │
│                                 │
│         ○ ● ○                   │
│                                 │
│      [Keyingi / Далее →]        │
└─────────────────────────────────┘
```

**Screen 3: Alarm Notifications**
```
┌─────────────────────────────────┐
│                                 │
│      [Bell/Alarm Illustration]  │
│                                 │
│   "Hech qachon unutmaysiz!"     │
│   "Никогда не забудете!"        │
│                                 │
│         ○ ○ ●                   │
│                                 │
│      [Boshlash / Начать]        │
└─────────────────────────────────┘
```

### 3. HOME SCREEN (Main Screen)
```
┌─────────────────────────────────┐
│ Levi                    [⚙️]    │
├─────────────────────────────────┤
│ ┌─────────────────────────────┐ │
│ │ 💎 Premium                  │ │
│ │ Cheksiz eslatmalar          │ │
│ │ Безлимитные напоминания     │ │
│ │               [Yangilash →] │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌──────┐ ┌──────┐ ┌──────┐     │
│ │ 📁   │ │ 🔍   │ │ 📊   │     │
│ │Hammasi│ │Qidirish│ │Statistika│ │
│ │ Все  │ │Поиск │ │Статистика│ │
│ └──────┘ └──────┘ └──────┘     │
│                                 │
│ Eslatmalar / Напоминания        │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ 🔔 Darsga borish            │ │
│ │    Bugun, 15:30             │ │
│ │    ⏱️ 2 soat qoldi          │ │
│ │                    [▶️ 0:05]│ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ 🔔 Dorixonaga borish        │ │
│ │    Ertaga, 09:00            │ │
│ │    ⏱️ 18 soat qoldi         │ │
│ │                    [▶️ 0:08]│ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ ✅ Namoz o'qish (Bajarildi) │ │
│ │    Bugun, 12:00             │ │
│ │                    [▶️ 0:03]│ │
│ └─────────────────────────────┘ │
│                                 │
│                                 │
│            ┌─────┐              │
│            │ 🎤  │              │
│            │     │              │
│            └─────┘              │
│         [Record Button]         │
└─────────────────────────────────┘
```

### 4. RECORDING SCREEN (Bottom Sheet / Modal)
```
┌─────────────────────────────────┐
│              ∨                  │
├─────────────────────────────────┤
│                                 │
│     ┌───────────────────┐       │
│     │   ◉◉◉◉◉◉◉◉◉◉◉◉   │       │
│     │   [Waveform]      │       │
│     └───────────────────┘       │
│                                 │
│          00:05 / 01:00          │
│                                 │
│   ┌─────────────────────────┐   │
│   │                         │   │
│   │    "Yozib olinmoqda..."  │   │
│   │    "Запись..."          │   │
│   │                         │   │
│   └─────────────────────────┘   │
│                                 │
│  ┌────────┐          ┌────────┐ │
│  │ Cancel │          │  ⏸️   │ │
│  │ Bekor  │          │ Pause  │ │
│  └────────┘          └────────┘ │
│                                 │
│         ┌──────────┐            │
│         │  ✓ Done  │            │
│         │  Tayyor  │            │
│         └──────────┘            │
└─────────────────────────────────┘
```

### 5. TRANSCRIPTION/PREVIEW SCREEN
```
┌─────────────────────────────────┐
│ ←  Yangi eslatma               │
│     Новое напоминание           │
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────┐    │
│  │ ▶️  0:00 / 0:08    1.0x │    │
│  │ ═══════════════════════ │    │
│  └─────────────────────────┘    │
│                                 │
│  Transkripsiya / Транскрипция   │
│  ┌─────────────────────────┐    │
│  │                         │    │
│  │ "Ertaga ertalab soat    │    │
│  │  8 da uyg'onishim       │    │
│  │  kerakligini eslatib    │    │
│  │  qo'y"                  │    │
│  │                         │    │
│  │          [✏️ Tahrirlash]│    │
│  └─────────────────────────┘    │
│                                 │
│  AI tahlili / AI анализ         │
│  ┌─────────────────────────┐    │
│  │ 📝 Vazifa: Uyg'onish    │    │
│  │ ⏰ Vaqt: Ertaga, 08:00   │    │
│  │ 🏷️ Kategoriya: Shaxsiy  │    │
│  │                         │    │
│  │    [Tahrirlash / Изменить]   │
│  └─────────────────────────┘    │
│                                 │
│                                 │
│  ┌─────────────────────────┐    │
│  │   ✅ Eslatma yaratish   │    │
│  │   Создать напоминание   │    │
│  └─────────────────────────┘    │
│                                 │
└─────────────────────────────────┘
```

### 6. REMINDER DETAIL SCREEN
```
┌─────────────────────────────────┐
│ ←  Eslatma                     │
│     Напоминание                 │
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────┐    │
│  │ 🔔                       │    │
│  │ Darsga borish            │    │
│  │ Идти на урок             │    │
│  └─────────────────────────┘    │
│                                 │
│  📅 Bugun                       │
│  ⏰ 15:30                       │
│  🏷️ Shaxsiy                     │
│  🔁 Bir martalik                │
│                                 │
│  Ovozli yozuv / Голосовая запись│
│  ┌─────────────────────────┐    │
│  │ ▶️  0:00 / 0:05         │    │
│  │ ═══════════════════════ │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │   ✅ Bajarildi / Готово │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │   ⏰ Kechiktirish        │    │
│  │      Отложить           │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │   🗑️ O'chirish / Удалить│    │
│  └─────────────────────────┘    │
│                                 │
└─────────────────────────────────┘
```

### 7. FULL-SCREEN ALARM NOTIFICATION
```
┌─────────────────────────────────┐
│                                 │
│                                 │
│            🔔                   │
│                                 │
│        ESLATMA!                 │
│      НАПОМИНАНИЕ!               │
│                                 │
│    ┌───────────────────┐        │
│    │                   │        │
│    │   Darsga borish   │        │
│    │   Идти на урок    │        │
│    │                   │        │
│    └───────────────────┘        │
│                                 │
│         ⏰ 15:30                 │
│                                 │
│                                 │
│                                 │
│  ┌──────────┐  ┌──────────┐    │
│  │          │  │          │    │
│  │  ⏰      │  │    ✅    │    │
│  │ Snooze   │  │  Done    │    │
│  │ 10 min   │  │ Tayyor   │    │
│  │          │  │          │    │
│  └──────────┘  └──────────┘    │
│                                 │
│         [Swipe to dismiss]      │
└─────────────────────────────────┘
```

### 8. SETTINGS SCREEN
```
┌─────────────────────────────────┐
│ ←  Sozlamalar / Настройки      │
├─────────────────────────────────┤
│                                 │
│ HISOBIM / МОЙ АККАУНТ           │
│ ┌─────────────────────────────┐ │
│ │ 👤 Profil                   │ │
│ │ 💎 Premium (Bepul / Бесплатно)│ │
│ │    [Yangilash / Обновить →] │ │
│ └─────────────────────────────┘ │
│                                 │
│ ESLATMA SOZLAMALARI             │
│ ┌─────────────────────────────┐ │
│ │ 🔔 Ovoz turi         [Alarm]│ │
│ │ 📳 Tebranish            [ON]│ │
│ │ 🔁 Takrorlash intervali [30m]│ │
│ │ ⏰ Snooze vaqti         [10m]│ │
│ └─────────────────────────────┘ │
│                                 │
│ TIL / ЯЗЫК                      │
│ ┌─────────────────────────────┐ │
│ │ 🌐 Til / Язык    [O'zbek 🇺🇿]│ │
│ └─────────────────────────────┘ │
│                                 │
│ BOSHQA / ДРУГОЕ                 │
│ ┌─────────────────────────────┐ │
│ │ 📤 Eksport qilish            │ │
│ │ 🔗 Telegram bot ulanish      │ │
│ │ ℹ️ Dastur haqida             │ │
│ │ 📝 Fikr bildirish            │ │
│ └─────────────────────────────┘ │
│                                 │
│           v1.0.0                │
└─────────────────────────────────┘
```

### 9. PREMIUM/PAYWALL SCREEN
```
┌─────────────────────────────────┐
│ ✕                               │
├─────────────────────────────────┤
│                                 │
│            💎                   │
│                                 │
│      Levi Premium               │
│                                 │
│  ┌─────────────────────────┐    │
│  │ ✓ Cheksiz eslatmalar    │    │
│  │   Безлимитные напоминания│    │
│  │                         │    │
│  │ ✓ Takroriy eslatmalar   │    │
│  │   Повторяющиеся         │    │
│  │                         │    │
│  │ ✓ Kategoriyalar         │    │
│  │   Категории             │    │
│  │                         │    │
│  │ ✓ Reklama yo'q          │    │
│  │   Без рекламы           │    │
│  │                         │    │
│  │ ✓ Bulutga sinxronlash   │    │
│  │   Облачная синхронизация│    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │   💎 Yillik - 59,000 UZS │    │
│  │      (4,900/oy)          │    │
│  │      -40% CHEGIRMA       │    │
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │   Oylik - 9,900 UZS      │    │
│  └─────────────────────────┘    │
│                                 │
│  [Davom etish / Продолжить]     │
│                                 │
│  7 kunlik bepul sinov           │
│  7-дневный бесплатный период    │
└─────────────────────────────────┘
```

### 10. CATEGORIES/FILTER SCREEN
```
┌─────────────────────────────────┐
│ ←  Kategoriyalar / Категории   │
├─────────────────────────────────┤
│                                 │
│  ┌──────┐ ┌──────┐ ┌──────┐    │
│  │ 📁   │ │ 💼   │ │ 🏠   │    │
│  │Hammasi│ │ Ish  │ │ Uy   │    │
│  │ (12) │ │ (5)  │ │ (3)  │    │
│  └──────┘ └──────┘ └──────┘    │
│                                 │
│  ┌──────┐ ┌──────┐ ┌──────┐    │
│  │ 🏥   │ │ 📚   │ │ 🛒   │    │
│  │Salomatlik│ │O'qish│ │Xarid │    │
│  │ (2)  │ │ (1)  │ │ (1)  │    │
│  └──────┘ └──────┘ └──────┘    │
│                                 │
│  ┌─────────────────────────┐    │
│  │  + Yangi kategoriya     │    │
│  │    Новая категория      │    │
│  └─────────────────────────┘    │
│                                 │
└─────────────────────────────────┘
```

---

## TECHNICAL REQUIREMENTS

### Project Structure
```
src/
├── main.tsx
├── App.tsx
├── index.css
├── vite-env.d.ts
├── config/
│   ├── theme.ts
│   ├── constants.ts
│   └── routes.tsx
├── types/
│   ├── reminder.ts
│   ├── category.ts
│   └── user.ts
├── hooks/
│   ├── useAuth.ts
│   ├── useReminders.ts
│   ├── useRecording.ts
│   └── useNotifications.ts
├── services/
│   ├── api.ts
│   ├── audio.ts
│   ├── notifications.ts
│   └── storage.ts
├── pages/
│   ├── SplashPage.tsx
│   ├── OnboardingPage.tsx
│   ├── HomePage.tsx
│   ├── SettingsPage.tsx
│   ├── PremiumPage.tsx
│   └── CategoriesPage.tsx
├── components/
│   ├── ReminderCard.tsx
│   ├── RecordingButton.tsx
│   ├── RecordingModal.tsx
│   ├── TranscriptionModal.tsx
│   ├── ReminderDetailModal.tsx
│   ├── AlarmNotification.tsx
│   ├── Waveform.tsx
│   ├── PremiumBanner.tsx
│   ├── CategoryChip.tsx
│   └── AudioPlayer.tsx
├── contexts/
│   ├── AuthContext.tsx
│   ├── ReminderContext.tsx
│   └── LanguageContext.tsx
├── utils/
│   ├── i18n.ts
│   ├── dateFormatter.ts
│   └── helpers.ts
└── locales/
    ├── uz.json
    └── ru.json
```

### Required NPM Packages
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    
    "// State Management": "",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.4.0",
    
    "// Audio Recording & Playback": "",
    "recordrtc": "^5.6.0",
    "wavesurfer.js": "^7.4.0",
    "howler": "^2.2.0",
    
    "// Push Notifications (PWA)": "",
    "web-push": "^3.6.0",
    
    "// HTTP & API": "",
    "axios": "^1.6.0",
    
    "// Local Storage": "",
    "idb-keyval": "^6.2.0",
    "localforage": "^1.10.0",
    
    "// UI Components": "",
    "framer-motion": "^10.16.0",
    "lucide-react": "^0.294.0",
    "react-hot-toast": "^2.4.0",
    "@headlessui/react": "^1.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    
    "// PWA": "",
    "vite-plugin-pwa": "^0.17.0",
    "workbox-window": "^7.0.0",
    
    "// i18n": "",
    "i18next": "^23.7.0",
    "react-i18next": "^13.5.0",
    
    "// Utils": "",
    "date-fns": "^2.30.0",
    "uuid": "^9.0.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

### Key Features Implementation

#### 1. Voice Recording with Waveform
```typescript
// Use MediaRecorder API or RecordRTC for recording
// Use wavesurfer.js for visual waveform feedback
// Save as webm or wav format (Blob)
// Request microphone permission via navigator.mediaDevices.getUserMedia
```

#### 2. Push Notifications (PWA)
```typescript
// Use Service Workers for background notifications
// Use Notification API for browser notifications
// Request notification permission
// Persist scheduled reminders in IndexedDB
// Use Web Push for alarm-style alerts
// Implement notification sound using Howler.js
```

#### 3. Localization (Uzbek + Russian)
```typescript
// All UI text must be bilingual
// Use i18next with react-i18next
// Default: Uzbek
// Option to switch in settings
// Store preference in localStorage
```

#### 4. API Integration Points
```typescript
// POST /api/transcribe - Send audio file (FormData)
// POST /api/parse - Get AI parsed task/time
// GET /api/reminders - Fetch user reminders
// POST /api/reminders - Create reminder
// PUT /api/reminders/:id - Update reminder
// DELETE /api/reminders/:id - Delete reminder
// POST /api/reminders/:id/complete - Mark done
// POST /api/reminders/:id/snooze - Snooze reminder
```

---

## UI COMPONENT SPECIFICATIONS

### Reminder Card (Tailwind CSS)
```tsx
<div className="mx-4 my-2 p-4 bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow">
  <div className="flex items-center gap-3">
    {/* Status indicator (pending/done) */}
    {/* Task text */}
    {/* Time info */}
    {/* Audio duration badge */}
  </div>
</div>

// CSS equivalent
.reminder-card {
  margin: 8px 16px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
```

### Recording Button (FAB)
```tsx
<button className="w-18 h-18 bg-gray-900 rounded-full shadow-2xl flex items-center justify-center hover:scale-105 transition-transform">
  <Mic className="w-8 h-8 text-white" />
</button>

// CSS equivalent
.recording-button {
  width: 72px;
  height: 72px;
  background-color: #1A1A1A;
  border-radius: 50%;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}
```

### Premium Banner
```tsx
<div className="m-4 p-5 bg-gradient-to-r from-blue-500 to-purple-500 rounded-2xl">
  <div className="flex items-center gap-3">
    {/* Diamond icon */}
    {/* Text content */}
    {/* Arrow button */}
  </div>
</div>

// CSS equivalent
.premium-banner {
  margin: 16px;
  padding: 20px;
  background: linear-gradient(90deg, #4A90E2, #7B68EE);
  border-radius: 16px;
}
```

---

## ANIMATIONS

1. **Recording pulse** - Microphone button pulses while recording (CSS animation or Framer Motion)
2. **Waveform** - Real-time audio waveform during recording (wavesurfer.js)
3. **Card slide** - Swipe/click to delete/complete reminders (Framer Motion gestures)
4. **Page transitions** - Smooth route transitions (Framer Motion AnimatePresence)
5. **Loading shimmer** - Skeleton loading for lists (CSS shimmer effect)
6. **Alarm animation** - Bell shake animation on notification (CSS keyframes)

---

## GENERATE THE FOLLOWING FILES:

1. **main.tsx** - App entry point with providers
2. **App.tsx** - Router and layout setup
3. **theme.ts** - Tailwind theme configuration
4. **HomePage.tsx** - Main page with reminder list
5. **RecordingModal.tsx** - Voice recording modal/overlay
6. **TranscriptionModal.tsx** - Preview and edit transcription
7. **AlarmNotification.tsx** - Full-screen alarm notification component
8. **ReminderCard.tsx** - Reusable reminder card component
9. **RecordingButton.tsx** - FAB with animation
10. **PremiumBanner.tsx** - Premium upsell component
11. **SettingsPage.tsx** - App settings
12. **i18n.ts** - Uzbek/Russian translation setup
13. **uz.json & ru.json** - Translation files
14. **tailwind.config.js** - Tailwind configuration
15. **vite.config.ts** - Vite + PWA configuration

---

## PWA REQUIREMENTS:

1. **Service Worker** - For offline support and background sync
2. **Web App Manifest** - For "Add to Home Screen" functionality
3. **Push Notifications** - For reminder alerts
4. **Offline Storage** - IndexedDB for reminders and audio
5. **Install Prompt** - Custom install banner for PWA

---

## IMPORTANT NOTES:

1. **All text must be bilingual** (Uzbek on top, Russian below or switchable)
2. **Design must be pixel-perfect** matching the wireframes
3. **Use TypeScript** with strict mode
4. **Include proper error handling** with try-catch and error boundaries
5. **Make components reusable** with proper props typing
6. **Mobile-first responsive design** - Works on all screen sizes
7. **PWA compatible** - Installable, works offline
8. **Notifications must work** even when browser tab is closed (via Service Worker)

---

Generate complete, production-ready React TypeScript code for all pages and components. Start with the main.tsx, App.tsx and tailwind config, then proceed with each component in order.
