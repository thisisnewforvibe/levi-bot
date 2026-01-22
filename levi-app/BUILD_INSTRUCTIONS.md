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
