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

const LeviAlarm = registerPlugin<LeviAlarmPlugin>('LeviAlarm');
const LeviAlarmManager = registerPlugin<LeviAlarmManagerPlugin>('LeviAlarmManager');

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

export { LeviAlarm, LeviAlarmManager };
export default LeviAlarm;
