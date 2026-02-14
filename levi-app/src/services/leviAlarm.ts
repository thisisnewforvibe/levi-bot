import { registerPlugin } from '@capacitor/core';

export interface LeviAlarmPlugin {
  playAlarm(): Promise<{ success: boolean }>;
  stopAlarm(): Promise<{ success: boolean }>;
}

export interface AlarmScheduleOptions {
  id: number;
  title: string;
  body: string;
  triggerTime: number; // Unix timestamp in milliseconds
}

export interface LeviAlarmManagerPlugin {
  canScheduleExactAlarms(): Promise<{ canSchedule: boolean; androidVersion: number }>;
  openAlarmSettings(): Promise<{ opened: boolean; message?: string }>;
  canDrawOverlays(): Promise<{ canDraw: boolean }>;
  openOverlaySettings(): Promise<{ opened: boolean; message?: string }>;
  scheduleAlarm(options: AlarmScheduleOptions): Promise<{ success: boolean; id: number }>;
  scheduleMultiple(options: { alarms: AlarmScheduleOptions[] }): Promise<{ success: boolean; scheduled: number }>;
  scheduleTestAlarm(): Promise<{ success: boolean; message: string }>;
  cancelAlarm(options: { id: number }): Promise<{ success: boolean }>;
  cancelAll(): Promise<{ success: boolean }>;
  playAlarm(): Promise<{ success: boolean }>;
  stopAlarm(): Promise<{ success: boolean }>;
}

// iOS 26+ AlarmKit plugin interface (real alarm with full-screen UI)
export interface LeviAlarmKitPlugin {
  isAvailable(): Promise<{ available: boolean }>;
  requestAuthorization(): Promise<{ authorized: boolean; state: string }>;
  scheduleAlarm(options: { id: number; title: string; body: string; triggerTime: number; reminderId?: number }): Promise<{ success: boolean; id: number; uuid: string }>;
  scheduleMultiple(options: { alarms: AlarmScheduleOptions[] }): Promise<{ success: boolean; scheduled: number; total: number; errors: string[] }>;
  cancelAlarm(options: { id: number }): Promise<{ success: boolean }>;
  cancelAll(): Promise<{ success: boolean; cancelled: number }>;
  stopAlarm(options: { id: number }): Promise<{ success: boolean }>;
}

const LeviAlarm = registerPlugin<LeviAlarmPlugin>('LeviAlarm');
const LeviAlarmManager = registerPlugin<LeviAlarmManagerPlugin>('LeviAlarmManager');
const LeviAlarmKit = registerPlugin<LeviAlarmKitPlugin>('LeviAlarmKit');

/**
 * Check if iOS 26+ AlarmKit is available
 */
export async function isAlarmKitAvailable(): Promise<boolean> {
  try {
    const result = await LeviAlarmKit.isAvailable();
    console.log('AlarmKit available:', result.available);
    return result.available;
  } catch (error) {
    console.log('AlarmKit not available (not iOS 26+)');
    return false;
  }
}

/**
 * Request AlarmKit authorization (iOS 26+)
 */
export async function requestAlarmKitAuthorization(): Promise<boolean> {
  try {
    const result = await LeviAlarmKit.requestAuthorization();
    console.log('AlarmKit authorization:', result);
    return result.authorized;
  } catch (error) {
    console.error('AlarmKit authorization error:', error);
    return false;
  }
}

/**
 * Check if exact alarms are allowed and prompt user to enable if not
 */
export async function ensureExactAlarmPermission(): Promise<boolean> {
  try {
    const result = await LeviAlarmManager.canScheduleExactAlarms();
    console.log('Exact alarm permission check:', result);
    
    if (!result.canSchedule) {
      console.log('Exact alarm permission NOT granted - opening settings...');
      await LeviAlarmManager.openAlarmSettings();
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('Error checking exact alarm permission:', error);
    return false;
  }
}

/**
 * Check if overlay permission is granted (for full-screen alarm)
 */
export async function checkOverlayPermission(): Promise<boolean> {
  try {
    const result = await LeviAlarmManager.canDrawOverlays();
    console.log('Overlay permission check:', result);
    return result.canDraw;
  } catch (error) {
    console.error('Error checking overlay permission:', error);
    return false;
  }
}

/**
 * Open settings to grant overlay permission
 */
export async function requestOverlayPermission(): Promise<void> {
  try {
    await LeviAlarmManager.openOverlaySettings();
  } catch (error) {
    console.error('Error opening overlay settings:', error);
  }
}

export { LeviAlarm, LeviAlarmManager, LeviAlarmKit };
export default LeviAlarm;
