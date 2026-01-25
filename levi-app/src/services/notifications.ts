/**
 * Alarm-style Notification Service for Levi App
 * Uses Capacitor Local Notifications with alarm-like behavior
 * Includes follow-up reminders with Yes/No action buttons
 */

import { LocalNotifications, ScheduleOptions, PendingLocalNotificationSchema } from '@capacitor/local-notifications';
import { Capacitor } from '@capacitor/core';

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
      
      if (permStatus.display === 'prompt') {
        // Request permission
        const result = await LocalNotifications.requestPermissions();
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
    await LocalNotifications.addListener('localNotificationReceived', (notification) => {
      console.log('Notification received:', notification);
    });

    // When user taps on notification or action button
    await LocalNotifications.addListener('localNotificationActionPerformed', async (action) => {
      console.log('Notification action performed:', action);
      
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
   * Schedule multiple alarms at once (Done/Snooze buttons only)
   * Follow-ups are only scheduled when user clicks "Done"
   */
  async scheduleMultipleAlarms(alarms: AlarmNotification[]): Promise<boolean> {
    if (!this.initialized) {
      await this.initialize();
    }

    try {
      // Schedule initial alarms only (no auto follow-ups)
      const notifications = alarms.map((alarm) => ({
        id: alarm.id,
        title: alarm.title,
        body: alarm.body,
        schedule: {
          at: alarm.scheduledTime,
          allowWhileIdle: true,
        },
        sound: 'alarm.wav',
        smallIcon: 'ic_stat_icon_config_sample',
        largeIcon: 'ic_launcher',
        channelId: 'alarm_channel',
        extra: { 
          ...alarm.extra,
          taskText: alarm.body,
          isFollowUp: false,
        },
        actionTypeId: 'reminder_actions',
        ongoing: false,
        autoCancel: false,
      }));

      await LocalNotifications.schedule({ notifications });
      console.log(`${alarms.length} alarms scheduled (follow-ups will be scheduled when user clicks Done)`);
      
      // NOTE: Follow-ups are NOT auto-scheduled here
      // They are only scheduled when user clicks "Done" on the alarm
      
      return true;
    } catch (error) {
      console.error('Failed to schedule multiple alarms:', error);
      return false;
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
      // Main alarm channel
      await LocalNotifications.createChannel({
        id: 'alarm_channel',
        name: 'Eslatmalar',
        description: 'Muhim eslatmalar uchun signal',
        importance: 5, // Max importance - makes sound and shows heads-up
        visibility: 1, // Public - show on lock screen
        sound: 'alarm.wav',
        vibration: true,
        lights: true,
        lightColor: '#FF0000',
      });
      console.log('Alarm channel created');
      
      // Follow-up channel
      await LocalNotifications.createChannel({
        id: 'followup_channel',
        name: 'Tekshiruv',
        description: 'Vazifa bajarilganmi tekshirish',
        importance: 5, // Max importance
        visibility: 1, // Public
        sound: 'alarm.wav',
        vibration: true,
        lights: true,
        lightColor: '#FFA500', // Orange for follow-ups
      });
      console.log('Follow-up channel created');
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
  return {
    id: reminder.id,
    title: '🔔 Eslatma',
    body: reminder.task_text,
    scheduledTime: new Date(reminder.scheduled_time_utc),
    extra: { reminderId: reminder.id },
  };
}

export default notificationService;
