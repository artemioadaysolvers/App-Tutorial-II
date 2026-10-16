import type { ExpoConfig } from 'expo/config';

const config: ExpoConfig = {
  name: 'Mensajes', slug: 'mensajes-google', version: '1.0.0',
  orientation: 'portrait', userInterfaceStyle: 'light', scheme: 'mensajes',
  platforms: ['android'],
  android: {
    package: process.env.APP_ANDROID_PACKAGE || 'com.artemio.mensajes',
    versionCode: 1, softwareKeyboardLayoutMode: 'resize', allowBackup: false,
  },
  plugins: ['@react-native-google-signin/google-signin', 'expo-secure-store'],
  ...(process.env.EAS_PROJECT_ID ? { extra: { eas: { projectId: process.env.EAS_PROJECT_ID } } } : {}),
};
export default config;
