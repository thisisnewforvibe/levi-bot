import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.levi.reminders',
  appName: 'Levi',
  webDir: 'dist',
  server: {
    androidScheme: 'https'
  },
  plugins: {
    StatusBar: {
      style: 'light',
      backgroundColor: '#FFFFFF'
    },
    LocalNotifications: {
      smallIcon: 'ic_stat_icon_config_sample',
      iconColor: '#1A1A1A',
      // Alarm-style sound (louder, more persistent)
      sound: 'alarm.wav'
    }
  },
  android: {
    allowMixedContent: true,
    // Enable exact alarms for precise reminder timing
    useLegacyBridge: false
  },
  ios: {
    scheme: 'Levi',
    contentInset: 'never',
    backgroundColor: '#FFFFFF',
    scrollEnabled: true,
    allowsLinkPreview: false
  }
};

export default config;
