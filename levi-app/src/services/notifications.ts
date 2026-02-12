/**
 * Alarm-style Notification Service for Levi App
 * Uses Capacitor Local Notifications with alarm-like behavior
 * Includes follow-up reminders with Yes/No action buttons
 */

import { LocalNotifications, ScheduleOptions, PendingLocalNotificationSchema } from '@capacitor/local-notifications';
import { Capacitor } from '@capacitor/core';
import LeviAlarm, { LeviAlarmManager } from './leviAlarm';

// Follow-up delay in milliseconds (30 minutes, same as Telegram bot)
export const FOLLOW_UP_DELAY_MS = 30 * 60 * 1000;

// ID offset for follow-up notifications (to differentiate from initial alarms)
const FOLLOW_UP_ID_OFFSET = 1000000;

export interface AlarmNotification {
  id: number;
  title: string;
  body: string;
  scheduledTime: Date;
  extra?: Record<string, unknown>;
}

// Callback types for handling notification actions
type NotificationActionCallback = (reminderId: number, action: 'done' | 'snooze' | 'yes' | 'no') => void;

class NotificationService {
  private initialized = false;
  private actionCallback: NotificationActionCallback | null = null;

  /**
   * Set callback for notification actions
   * This allows the app to respond to user interactions
   */
  setActionCallback(callback: NotificationActionCallback): void {
    this.actionCallback = callback;
  }

  /**
   * Initialize the notification service
   * Must be called when app starts
   */
  async initialize(): Promise<boolean> {
    if (!Capacitor.isNativePlatform()) {
      console.log('Notifications only work on native platforms');
      return false;
    }

    if (this.initialized) {
      return true;
    }

    try {
      // Check current permission status
      const permStatus = await LocalNotifications.checkPermissions();
      console.log('Notification permission status:', permStatus.display);
      
      if (permStatus.display === 'prompt') {
        // Request permission
        const result = await LocalNotifications.requestPermissions();
        console.log('Permission request result:', result.display);
        if (result.display !== 'granted') {
          console.warn('Notification permission denied');
          return false;
        }
      } else if (permStatus.display !== 'granted') {
        console.warn('Notification permission not granted:', permStatus.display);
        return false;
      }

      // Set up notification listeners
      await this.setupListeners();
      
      // Log pending notifications for debugging
      const pending = await LocalNotifications.getPending();
      console.log(`Currently ${pending.notifications.length} pending notifications`);
      pending.notifications.forEach(n => {
        console.log(`  - ID: ${n.id}, Title: ${n.title}, Schedule: ${JSON.stringify(n.schedule)}`);
      });
      
      this.initialized = true;
      console.log('Notification service initialized successfully');
      return true;
    } catch (error) {
      console.error('Failed to initialize notification service:', error);
      return false;
    }
  }

  /**
   * Set up notification event listeners
   */
  private async setupListeners(): Promise<void> {
    // When notification is received while app is in foreground
    // NOTE: We're using native AlarmManager now, so we don't need to play alarm here
    // The AlarmReceiver.java handles playing the alarm sound directly
    await LocalNotifications.addListener('localNotificationReceived', async (notification) => {
      console.log('Capacitor notification received (for logging only):', notification);
      // Don't play alarm here - native AlarmManager handles it
    });

    // When user taps on notification or action button
    await LocalNotifications.addListener('localNotificationActionPerformed', async (action) => {
      console.log('Notification action performed:', action);
      
      // Stop the alarm when user interacts with notification
      try {
        if (Capacitor.getPlatform() === 'android') {
          await LeviAlarm.stopAlarm();
        }
      } catch (error) {
        console.error('Failed to stop alarm:', error);
      }
      
      const actionId = action.actionId;
      const notificationId = action.notification.id;
      const extra = action.notification.extra as Record<string, unknown> || {};
      const reminderId = (extra.reminderId as number) || notificationId;
      const isFollowUp = extra.isFollowUp === true;
      
      // Handle different actions
      if (isFollowUp) {
        // Follow-up notification actions (Yes/No)
        if (actionId === 'yes') {
          // User confirmed task is completed - mark as done
          console.log('Task confirmed done via follow-up:', reminderId);
          this.actionCallback?.(reminderId, 'done');
        } else if (actionId === 'no' || actionId === 'tap') {
          // User didn't complete - schedule another follow-up in 30 minutes
          console.log('Task not done, scheduling another follow-up:', reminderId);
          await this.scheduleFollowUp(reminderId, extra.taskText as string);
          this.actionCallback?.(reminderId, 'no');
        } else {
          // Tapped notification without selecting action - treat as "no"
          console.log('Follow-up tapped, scheduling another follow-up:', reminderId);
          await this.scheduleFollowUp(reminderId, extra.taskText as string);
        }
      } else {
        // Initial alarm notification actions
        if (actionId === 'done') {
          // User clicked "Done" - NOW schedule follow-up to confirm in 30 minutes
          console.log('Done clicked, scheduling follow-up to confirm:', reminderId);
          await this.scheduleFollowUp(reminderId, extra.taskText as string);
          // Don't mark as done yet - wait for follow-up confirmation
        } else if (actionId === 'snooze') {
          // Snooze - reschedule initial alarm in 10 minutes (NO follow-up)
          console.log('Snooze clicked, rescheduling alarm:', reminderId);
          await this.snoozeInitialAlarm(reminderId, extra.taskText as string, 10);
          this.actionCallback?.(reminderId, 'snooze');
        } else {
          // User tapped notification without action - treat as snooze (reschedule)
          console.log('Alarm tapped without action, rescheduling:', reminderId);
          await this.snoozeInitialAlarm(reminderId, extra.taskText as string, 10);
        }
      }
    });
  }

  /**
   * Snooze initial alarm - reschedule with Done/Snooze buttons (no follow-up)
   */
  async snoozeInitialAlarm(reminderId: number, taskText: string, minutes: number = 10): Promise<boolean> {
    try {
      const snoozeTime = new Date(Date.now() + minutes * 60 * 1000);
      
      await LocalNotifications.schedule({
        notifications: [
          {
            id: reminderId,
            title: '🔔 Eslatma',
            body: taskText,
            schedule: {
              at: snoozeTime,
              allowWhileIdle: true,
            },
            sound: 'alarm.wav',
            smallIcon: 'ic_stat_icon_config_sample',
            largeIcon: 'ic_launcher',
            channelId: 'alarm_channel',
            extra: {
              reminderId: reminderId,
              taskText: taskText,
              isFollowUp: false,
            },
            actionTypeId: 'reminder_actions',
            ongoing: false,
            autoCancel: false,
          },
        ],
      });
      
      console.log(`Initial alarm snoozed for ${minutes} minutes`);
      return true;
    } catch (error) {
      console.error('Failed to snooze initial alarm:', error);
      return false;
    }
  }

  /**
   * Schedule an alarm-style notification (Done/Snooze buttons)
   * Follow-up is only scheduled when user clicks "Done"
   */
  async scheduleAlarm(alarm: AlarmNotification): Promise<boolean> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      const scheduleOptions: ScheduleOptions = {
        notifications: [
          {
            id: alarm.id,
            title: alarm.title,
            body: alarm.body,
            schedule: {
              at: alarm.scheduledTime,
              allowWhileIdle: true, // Important: fires even in doze mode
            },
            sound: 'alarm.wav', // Custom alarm sound
            smallIcon: 'ic_stat_icon_config_sample',
            largeIcon: 'ic_launcher',
            // Android-specific: make it more alarm-like
            channelId: 'alarm_channel',
            extra: { 
              ...alarm.extra,
              taskText: alarm.body,
              isFollowUp: false,
            },
            actionTypeId: 'reminder_actions',
            // These make it more prominent
            ongoing: false,
            autoCancel: false,
          },
        ],
      };

      await LocalNotifications.schedule(scheduleOptions);
      console.log(`Alarm scheduled for ${alarm.scheduledTime.toISOString()}:`, alarm.title);
      
      // NOTE: Follow-up is NOT auto-scheduled here
      // Follow-up is only scheduled when user clicks "Done" on the alarm
      
      return true;
    } catch (error) {
      console.error('Failed to schedule alarm:', error);
      return false;
    }
  }

  /**
   * Schedule a follow-up notification with Yes/No buttons
   */
  private async scheduleFollowUpNotification(reminderId: number, taskText: string, scheduledTime: Date): Promise<boolean> {
    try {
      const followUpId = reminderId + FOLLOW_UP_ID_OFFSET;
      
      await LocalNotifications.schedule({
        notifications: [
          {
            id: followUpId,
            title: '⏰ Vazifa bajarildimi?',
            body: taskText,
            schedule: {
              at: scheduledTime,
              allowWhileIdle: true,
            },
            sound: 'alarm.wav',
            smallIcon: 'ic_stat_icon_config_sample',
            largeIcon: 'ic_launcher',
            channelId: 'followup_channel',
            extra: {
              reminderId: reminderId,
              taskText: taskText,
              isFollowUp: true,
            },
            actionTypeId: 'followup_actions',
            ongoing: false,
            autoCancel: false,
          },
        ],
      });
      
      console.log(`Follow-up scheduled for ${scheduledTime.toISOString()}:`, taskText);
      return true;
    } catch (error) {
      console.error('Failed to schedule follow-up:', error);
      return false;
    }
  }

  /**
   * Schedule a follow-up from now (30 minutes later)
   */
  async scheduleFollowUp(reminderId: number, taskText: string): Promise<boolean> {
    const followUpTime = new Date(Date.now() + FOLLOW_UP_DELAY_MS);
    return this.scheduleFollowUpNotification(reminderId, taskText, followUpTime);
  }

  /**
   * Schedule multiple alarms at once using NATIVE Android AlarmManager
   * This ensures alarms play sound and vibrate even when app is closed
   * Follow-ups are only scheduled when user clicks "Done"
   */
  async scheduleMultipleAlarms(alarms: AlarmNotification[]): Promise<boolean> {
    if (!this.initialized) {
      const initSuccess = await this.initialize();
      if (!initSuccess) {
        console.error('Failed to initialize notification service');
        return false;
      }
    }

    try {
      // Log what we're scheduling
      console.log(`Scheduling ${alarms.length} alarms:`);
      alarms.forEach(alarm => {
        const timestamp = alarm.scheduledTime.getTime();
        const now = Date.now();
        console.log(`  - ID: ${alarm.id}, "${alarm.body}"`);
        console.log(`    Time: ${alarm.scheduledTime.toLocaleString()}`);
        console.log(`    Timestamp: ${timestamp}, Now: ${now}, Diff: ${timestamp - now}ms`);
      });
      
      // On Android, use native AlarmManager for reliable alarm with sound
      // On iOS, use Capacitor LocalNotifications (which uses UNUserNotificationCenter)
      if (Capacitor.getPlatform() === 'android') {
        const nativeAlarms = alarms.map(alarm => ({
          id: alarm.id,
          title: '🔔 Eslatma',
          body: alarm.body,
          triggerTime: alarm.scheduledTime.getTime(),
        }));
        
        console.log('Sending to native AlarmManager:', JSON.stringify(nativeAlarms));
        
        const result = await LeviAlarmManager.scheduleMultiple({ alarms: nativeAlarms });
        console.log(`Native AlarmManager scheduled ${result.scheduled} alarms`);
        console.log(`✓ ${alarms.length} alarms scheduled with native AlarmManager (sound guaranteed)`);
      } else {
        // iOS path - use Capacitor LocalNotifications
        const notifications = alarms.map((alarm) => ({
          id: alarm.id,
          title: '🔔 Eslatma',
          body: alarm.body,
          schedule: {
            at: alarm.scheduledTime,
            allowWhileIdle: true,
          },
          sound: 'alarm.wav',
          extra: { 
            ...alarm.extra,
            taskText: alarm.body,
            isFollowUp: false,
          },
          actionTypeId: 'reminder_actions',
        }));

        await LocalNotifications.schedule({ notifications });
        console.log(`✓ ${alarms.length} alarms scheduled via Capacitor LocalNotifications (iOS)`);
      }
      
      return true;
    } catch (error) {
      console.error('Failed to schedule alarms:', error);
      
      // Fallback to Capacitor-only if native fails
      try {
        console.log('Falling back to Capacitor-only notifications...');
        const notifications = alarms.map((alarm) => ({
          id: alarm.id,
          title: '🔔 Eslatma',
          body: alarm.body,
          schedule: {
            at: alarm.scheduledTime,
            allowWhileIdle: true,
          },
          smallIcon: 'ic_stat_icon_config_sample',
          largeIcon: 'ic_launcher',
          channelId: 'alarm_channel',
          extra: { 
            ...alarm.extra,
            taskText: alarm.body,
            isFollowUp: false,
          },
          actionTypeId: 'reminder_actions',
          ongoing: true,
          autoCancel: false,
        }));

        await LocalNotifications.schedule({ notifications });
        console.log('Fallback successful - alarms scheduled via Capacitor');
        return true;
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError);
        return false;
      }
    }
  }

  /**
   * Cancel a scheduled alarm
   */
  async cancelAlarm(id: number): Promise<boolean> {
    try {
      await LocalNotifications.cancel({ notifications: [{ id }] });
      console.log('Alarm cancelled:', id);
      return true;
    } catch (error) {
      console.error('Failed to cancel alarm:', error);
      return false;
    }
  }

  /**
   * Cancel all scheduled alarms
   */
  async cancelAllAlarms(): Promise<boolean> {
    try {
      const pending = await LocalNotifications.getPending();
      if (pending.notifications.length > 0) {
        await LocalNotifications.cancel({
          notifications: pending.notifications.map((n) => ({ id: n.id })),
        });
      }
      console.log('All alarms cancelled');
      return true;
    } catch (error) {
      console.error('Failed to cancel all alarms:', error);
      return false;
    }
  }

  /**
   * Snooze an alarm for specified minutes
   */
  async snoozeAlarm(id: number, minutes: number = 10): Promise<boolean> {
    try {
      // Get the pending notification to retrieve its details
      const pending = await LocalNotifications.getPending();
      const notification = pending.notifications.find((n) => n.id === id);
      
      if (notification) {
        // Cancel the original
        await this.cancelAlarm(id);
        
        // Schedule new one
        const snoozeTime = new Date(Date.now() + minutes * 60 * 1000);
        await this.scheduleAlarm({
          id: id,
          title: notification.title,
          body: notification.body,
          scheduledTime: snoozeTime,
          extra: notification.extra as Record<string, unknown>,
        });
        
        console.log(`Alarm snoozed for ${minutes} minutes`);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Failed to snooze alarm:', error);
      return false;
    }
  }

  /**
   * Get all pending alarms
   */
  async getPendingAlarms(): Promise<PendingLocalNotificationSchema[]> {
    try {
      const result = await LocalNotifications.getPending();
      return result.notifications;
    } catch (error) {
      console.error('Failed to get pending alarms:', error);
      return [];
    }
  }

  /**
   * Create notification channels for Android (alarm-style and follow-up)
   * Should be called once during app initialization
   */
  async createAlarmChannel(): Promise<void> {
    if (Capacitor.getPlatform() !== 'android') {
      return;
    }

    try {
      // Delete existing channels first to ensure fresh settings
      try {
        await LocalNotifications.deleteChannel({ id: 'alarm_channel' });
        await LocalNotifications.deleteChannel({ id: 'followup_channel' });
        console.log('Deleted old notification channels');
      } catch (e) {
        // Channels might not exist yet, that's fine
      }
      
      // Main alarm channel - MAX importance for heads-up + sound
      // Note: For Android 8+, sound must be a file in res/raw folder
      // If no sound file exists, system default will be used
      await LocalNotifications.createChannel({
        id: 'alarm_channel',
        name: 'Eslatmalar (Alarm)',
        description: 'Muhim eslatmalar - signal va tebranish bilan',
        importance: 5, // MAX - makes sound, vibrates, heads-up display
        visibility: 1, // Public - show on lock screen
        // Not specifying sound means it uses system default
        vibration: true,
        lights: true,
        lightColor: '#FF0000',
      });
      console.log('Alarm channel created with MAX importance (5)');
      
      // Follow-up channel  
      await LocalNotifications.createChannel({
        id: 'followup_channel',
        name: 'Tekshiruv',
        description: 'Vazifa bajarilganmi tekshirish',
        importance: 5, // MAX importance
        visibility: 1, // Public
        vibration: true,
        lights: true,
        lightColor: '#FFA500',
      });
      console.log('Follow-up channel created');
      
      // List channels to verify
      const channels = await LocalNotifications.listChannels();
      console.log('Created channels:', channels.channels.map(c => `${c.id}: importance=${c.importance}`));
    } catch (error) {
      console.error('Failed to create alarm channel:', error);
    }
  }

  /**
   * Register notification action types (initial + follow-up)
   */
  async registerActionTypes(): Promise<void> {
    try {
      await LocalNotifications.registerActionTypes({
        types: [
          // Initial reminder actions
          {
            id: 'reminder_actions',
            actions: [
              {
                id: 'done',
                title: '✅ Bajarildi',
                destructive: false,
              },
              {
                id: 'snooze',
                title: '⏰ 10 daqiqa',
                destructive: false,
              },
            ],
          },
          // Follow-up actions (Yes/No)
          {
            id: 'followup_actions',
            actions: [
              {
                id: 'yes',
                title: '✅ HA / Bajarildi',
                destructive: false,
              },
              {
                id: 'no',
                title: "❌ YO'Q / Hali yo'q",
                destructive: false,
              },
            ],
          },
        ],
      });
      console.log('Action types registered');
    } catch (error) {
      console.error('Failed to register action types:', error);
    }
  }
}

// Export singleton instance
export const notificationService = new NotificationService();

// Helper function to convert reminder to alarm
export function reminderToAlarm(reminder: {
  id: number;
  task_text: string;
  scheduled_time_utc: string;
}): AlarmNotification {
  // Ensure UTC time is parsed correctly
  // Backend returns format like "2026-01-25 12:35" or "2026-01-25 12:35:42"
  // JavaScript requires ISO format with T separator: "2026-01-25T12:35:00Z"
  let utcTimeStr = reminder.scheduled_time_utc;
  
  // Replace space with T for proper ISO format
  if (utcTimeStr.includes(' ') && !utcTimeStr.includes('T')) {
    utcTimeStr = utcTimeStr.replace(' ', 'T');
  }
  
  // Add Z suffix if not present (to indicate UTC)
  if (!utcTimeStr.endsWith('Z') && !utcTimeStr.includes('+')) {
    utcTimeStr = utcTimeStr + 'Z';
  }
  
  const scheduledTime = new Date(utcTimeStr);
  
  // Validate the parsed time
  if (isNaN(scheduledTime.getTime())) {
    console.error(`Failed to parse scheduled_time_utc: "${reminder.scheduled_time_utc}" -> "${utcTimeStr}"`);
    // Fallback: try parsing as-is
    const fallbackTime = new Date(reminder.scheduled_time_utc);
    console.log(`Fallback parse result: ${fallbackTime.toISOString()}`);
  }
  
  console.log(`Creating alarm for: ${reminder.task_text}`);
  console.log(`  Original: "${reminder.scheduled_time_utc}" -> Parsed: "${utcTimeStr}"`);
  console.log(`  Timestamp: ${scheduledTime.getTime()}`);
  console.log(`  ISO: ${scheduledTime.toISOString()}`);
  console.log(`  Local: ${scheduledTime.toLocaleString()}`);
  
  return {
    id: reminder.id,
    title: '🔔 Eslatma',
    body: reminder.task_text,
    scheduledTime: scheduledTime,
    extra: { reminderId: reminder.id },
  };
}

export default notificationService;
