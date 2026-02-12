# Levi App - Build Instructions

## Prerequisites

1. **Node.js** (v18+)
2. **Android Studio** (for building APK)
3. **Java JDK 17+**

## Setup

```bash
cd levi-app
npm install
```

## Development

```bash
# Run dev server
npm run dev

# Run API server (in another terminal)
cd ..
python api_server.py
```

## Building APK

### Step 1: Build the web app
```bash
npm run build
```

### Step 2: Sync with Capacitor
```bash
npx cap sync android
```

### Step 3: Open in Android Studio
```bash
npx cap open android
```

### Step 4: Build APK in Android Studio
1. Wait for Gradle sync to complete
2. Go to **Build > Build Bundle(s) / APK(s) > Build APK(s)**
3. Or for signed APK: **Build > Generate Signed Bundle / APK**

### Step 5: Find your APK
- Debug APK: `android/app/build/outputs/apk/debug/app-debug.apk`
- Release APK: `android/app/build/outputs/apk/release/app-release.apk`

## Alternative: Build via Command Line

If you have Android SDK installed and configured:

```bash
cd android
./gradlew assembleDebug
```

The APK will be at: `android/app/build/outputs/apk/debug/app-debug.apk`

## API Server

Run the backend API server:

```bash
cd reminder_bot
pip install fastapi uvicorn aiosqlite pyjwt
python api_server.py
```

The API will be available at `http://localhost:8000`

## Environment Variables

Create `.env` file in `levi-app` folder:

```env
VITE_API_URL=http://your-server-ip:8000/api
```

For production, use your deployed server URL.

## App Structure

```
levi-app/
├── src/
│   ├── pages/           # Page components
│   ├── components/      # Reusable components
│   ├── services/        # API services
│   └── styles/          # Global styles
├── android/             # Android native project
├── capacitor.config.ts  # Capacitor configuration
└── package.json
```

## Features

- ✅ User registration and login
- ✅ Voice reminders list
- ✅ Filter by status (All/Pending/Done)
- ✅ Mark reminders as done
- ✅ Profile management
- ✅ Smooth animations
- ✅ Native Android app via Capacitor
- ✅ **Alarm-style notifications** with snooze/done actions

## Alarm Notifications Setup

The app uses Capacitor Local Notifications for alarm-style reminders.

### Adding Custom Alarm Sound

1. Add your alarm sound file (`.wav` or `.mp3`) to:
   ```
   android/app/src/main/res/raw/alarm.wav
   ```

2. The sound file should be:
   - Format: WAV or MP3
   - Duration: 5-30 seconds (loops automatically)
   - Loud and attention-grabbing

3. If you don't add a custom sound, the system default notification sound will be used.

### Alarm Features

- **High-priority notifications** that show even in Do Not Disturb mode
- **Exact alarm timing** using Android's exact alarm APIs
- **Wake device** - alarms work even when screen is off
- **Action buttons** - "Bajarildi" (Done) and "10 daqiqa" (Snooze)
- **Lock screen visibility** - alarms show on lock screen

### Follow-up Reminders (Like Telegram Bot)

The app uses a smart follow-up system to ensure tasks get completed:

**Initial Alarm Flow:**
1. Alarm fires at scheduled time with two buttons:
   - "✅ Bajarildi" (Done) → Schedules follow-up in 30 minutes
   - "⏰ 10 daqiqa" (Snooze) → Reschedules alarm in 10 minutes (NO follow-up)

**Follow-up Flow (after user clicks Done):**
2. Follow-up asks "Vazifa bajarildimi?" with:
   - "✅ HA" → Marks task as complete in backend
   - "❌ YO'Q" → Schedules another follow-up in 30 minutes

**The Cycle:**
- **Snooze loop**: User keeps clicking Snooze → Alarm repeats every 10 min until Done is clicked
- **Follow-up loop**: After Done is clicked → Follow-ups repeat every 30 min until HA (Yes) is clicked

### Android Permissions (Auto-configured)

- `POST_NOTIFICATIONS` - Show notifications
- `SCHEDULE_EXACT_ALARM` - Precise alarm timing
- `WAKE_LOCK` - Wake device for alarm
- `VIBRATE` - Vibration with alarm
