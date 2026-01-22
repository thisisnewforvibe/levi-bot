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
      sound: 'beep.wav'
    }
  },
  android: {
    allowMixedContent: true
  }
};

export default config;
