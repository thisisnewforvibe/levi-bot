package com.levi.reminders;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;
import android.util.Log;

import androidx.core.app.NotificationCompat;

/**
 * BroadcastReceiver that plays alarm sound and vibrates when notification is received
 * This is triggered by AlarmManager for reliable background alarms
 */
public class AlarmReceiver extends BroadcastReceiver {
    private static final String TAG = "LeviAlarmReceiver";
    private static final String CHANNEL_ID = "levi_alarm_channel";
    public static final String ACTION_ALARM_TRIGGER = "com.levi.reminders.ALARM_TRIGGER";
    public static final String ACTION_DONE = "com.levi.reminders.ACTION_DONE";
    public static final String ACTION_SNOOZE = "com.levi.reminders.ACTION_SNOOZE";
    public static final String ACTION_STOP = "com.levi.reminders.ACTION_STOP";
    
    private static MediaPlayer mediaPlayer;
    private static Vibrator vibrator;
    private static PowerManager.WakeLock wakeLock;
    private static int currentAlarmId = 0;
    
    @Override
    public void onReceive(Context context, Intent intent) {
        // Acquire wake lock to ensure we complete our work
        PowerManager powerManager = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK | PowerManager.ACQUIRE_CAUSES_WAKEUP,
            "LeviAlarm:WakeLock"
        );
        wakeLock.acquire(60000); // 60 seconds max
        
        try {
            String action = intent.getAction();
            int id = intent.getIntExtra("id", 0);
            String title = intent.getStringExtra("title");
            String body = intent.getStringExtra("body");
            
            Log.d(TAG, "=== AlarmReceiver.onReceive ===");
            Log.d(TAG, "Action: " + action);
            Log.d(TAG, "ID: " + id);
            Log.d(TAG, "Title: " + title);
            Log.d(TAG, "Body: " + body);
            
            // Handle button actions
            if (ACTION_DONE.equals(action)) {
                Log.d(TAG, "Done button pressed for alarm: " + id);
                stopAlarm();
                dismissNotification(context, id);
                releaseWakeLock();
                return;
            }
            
            if (ACTION_SNOOZE.equals(action)) {
                Log.d(TAG, "Snooze button pressed for alarm: " + id);
                stopAlarm();
                dismissNotification(context, id);
                // Schedule snooze alarm in 10 minutes
                scheduleSnooze(context, id, title, body, 10);
                releaseWakeLock();
                return;
            }
            
            if (ACTION_STOP.equals(action)) {
                Log.d(TAG, "Stop button pressed");
                stopAlarm();
                dismissNotification(context, id);
                releaseWakeLock();
                return;
            }
            
            // This is a new alarm trigger (action is null or ALARM_TRIGGER)
            Log.d(TAG, "*** ALARM TRIGGERED! Playing sound and showing notification ***");
            
            if (title == null) title = "🔔 Eslatma";
            if (body == null) body = "Vaqt keldi!";
            
            currentAlarmId = id;
            
            // Launch full-screen alarm activity
            launchAlarmActivity(context, id, title, body);
            
            // Also show notification with action buttons as backup
            showNotificationWithActions(context, id, title, body);
            
            // Then play alarm sound
            playAlarmSound(context);
            
            // Then vibrate
            vibrateDevice(context);
            
            Log.d(TAG, "Alarm fully triggered - full-screen activity launched, sound playing, vibrating");
            
        } catch (Exception e) {
            Log.e(TAG, "Error in onReceive: " + e.getMessage());
            e.printStackTrace();
        }
        
        // Don't release wake lock here - let it timeout or be released when alarm stops
    }
    
    private static void releaseWakeLock() {
        try {
            if (wakeLock != null && wakeLock.isHeld()) {
                wakeLock.release();
                Log.d(TAG, "Wake lock released");
            }
        } catch (Exception e) {
            Log.e(TAG, "Error releasing wake lock: " + e.getMessage());
        }
    }
    
    /**
     * Schedule a snooze alarm
     */
    private void scheduleSnooze(Context context, int id, String title, String body, int minutes) {
        try {
            android.app.AlarmManager alarmManager = (android.app.AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            
            Intent intent = new Intent(context, AlarmReceiver.class);
            intent.setAction(ACTION_ALARM_TRIGGER);
            intent.putExtra("id", id);
            intent.putExtra("title", title != null ? title : "🔔 Eslatma");
            intent.putExtra("body", body != null ? body : "Snoozed reminder");
            
            PendingIntent pendingIntent = PendingIntent.getBroadcast(
                context,
                id,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );
            
            long triggerTime = System.currentTimeMillis() + (minutes * 60 * 1000);
            
            // Use setAlarmClock for guaranteed exact timing
            Intent showIntent = new Intent(context, MainActivity.class);
            PendingIntent showPendingIntent = PendingIntent.getActivity(
                context,
                id + 100000,
                showIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );
            
            android.app.AlarmManager.AlarmClockInfo alarmClockInfo = 
                new android.app.AlarmManager.AlarmClockInfo(triggerTime, showPendingIntent);
            alarmManager.setAlarmClock(alarmClockInfo, pendingIntent);
            
            Log.d(TAG, "Snooze scheduled for " + minutes + " minutes using setAlarmClock");
        } catch (Exception e) {
            Log.e(TAG, "Failed to schedule snooze: " + e.getMessage());
        }
    }
    
    /**
     * Launch full-screen alarm activity
     * Uses multiple flags to ensure it shows even on Samsung devices
     */
    private void launchAlarmActivity(Context context, int id, String title, String body) {
        try {
            Intent intent = new Intent(context, AlarmActivity.class);
            // Use all the flags needed to show over lock screen on Samsung
            intent.setFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK |
                Intent.FLAG_ACTIVITY_CLEAR_TOP |
                Intent.FLAG_ACTIVITY_SINGLE_TOP |
                Intent.FLAG_ACTIVITY_REORDER_TO_FRONT |
                Intent.FLAG_ACTIVITY_NO_USER_ACTION
            );
            intent.addFlags(Intent.FLAG_FROM_BACKGROUND);
            intent.putExtra("id", id);
            intent.putExtra("title", title);
            intent.putExtra("body", body);
            
            // For Android 10+, we need to check if we can draw overlays
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                if (android.provider.Settings.canDrawOverlays(context)) {
                    context.startActivity(intent);
                    Log.d(TAG, "Launched AlarmActivity with overlay permission");
                } else {
                    // Can't show overlay, just show high-priority notification
                    Log.w(TAG, "No overlay permission, relying on notification fullScreenIntent");
                }
            } else {
                context.startActivity(intent);
                Log.d(TAG, "Launched AlarmActivity for alarm: " + id);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to launch AlarmActivity: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    /**
     * Dismiss notification by ID
     */
    private void dismissNotification(Context context, int id) {
        NotificationManager notificationManager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        notificationManager.cancel(id);
    }
    
    /**
     * Show a high-priority notification with Done/Snooze/Stop buttons
     */
    private void showNotificationWithActions(Context context, int id, String title, String body) {
        NotificationManager notificationManager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        
        // Create notification channel for Android 8.0+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Levi Alarms",
                NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("Alarm notifications for Levi reminders");
            channel.enableVibration(true);
            channel.setVibrationPattern(new long[]{0, 500, 200, 500, 200, 500});
            channel.setBypassDnd(true); // Bypass Do Not Disturb
            notificationManager.createNotificationChannel(channel);
        }
        
        // Full-screen intent to launch AlarmActivity
        Intent fullScreenIntent = new Intent(context, AlarmActivity.class);
        fullScreenIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        fullScreenIntent.putExtra("id", id);
        fullScreenIntent.putExtra("title", title);
        fullScreenIntent.putExtra("body", body);
        PendingIntent fullScreenPendingIntent = PendingIntent.getActivity(
            context,
            id,
            fullScreenIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        
        // Done action - mark task as complete
        Intent doneIntent = new Intent(context, AlarmReceiver.class);
        doneIntent.setAction(ACTION_DONE);
        doneIntent.putExtra("id", id);
        doneIntent.putExtra("title", title);
        doneIntent.putExtra("body", body);
        PendingIntent donePendingIntent = PendingIntent.getBroadcast(
            context,
            id + 10000,
            doneIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        
        // Snooze action - remind again in 10 minutes
        Intent snoozeIntent = new Intent(context, AlarmReceiver.class);
        snoozeIntent.setAction(ACTION_SNOOZE);
        snoozeIntent.putExtra("id", id);
        snoozeIntent.putExtra("title", title);
        snoozeIntent.putExtra("body", body);
        PendingIntent snoozePendingIntent = PendingIntent.getBroadcast(
            context,
            id + 20000,
            snoozeIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        
        // Build the notification with action buttons (only Done and Snooze)
        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(false)
            .setOngoing(true) // Can't be swiped away
            .setContentIntent(fullScreenPendingIntent)
            .setFullScreenIntent(fullScreenPendingIntent, true) // Full-screen intent for alarm
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            // Add action buttons (removed To'xtatish, changed Bajarildi to Bajaraman)
            .addAction(android.R.drawable.ic_menu_send, "✓ Bajaraman", donePendingIntent)
            .addAction(android.R.drawable.ic_menu_recent_history, "⏰ 10 daqiqa", snoozePendingIntent);
        
        notificationManager.notify(id, builder.build());
        Log.d(TAG, "Notification shown with action buttons: " + title);
    }
    
    public static void playAlarmSound(Context context) {
        try {
            // Stop any existing playback
            stopAlarm();
            
            // Get default alarm sound
            Uri alarmUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
            if (alarmUri == null) {
                alarmUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
            }
            if (alarmUri == null) {
                alarmUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
            }
            
            mediaPlayer = new MediaPlayer();
            mediaPlayer.setDataSource(context, alarmUri);
            
            // Set audio attributes for alarm
            AudioAttributes audioAttributes = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ALARM)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build();
            mediaPlayer.setAudioAttributes(audioAttributes);
            
            // Set to play at max alarm volume
            AudioManager audioManager = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
            int maxVolume = audioManager.getStreamMaxVolume(AudioManager.STREAM_ALARM);
            audioManager.setStreamVolume(AudioManager.STREAM_ALARM, maxVolume, 0);
            
            mediaPlayer.setLooping(true); // Loop until stopped
            mediaPlayer.prepare();
            mediaPlayer.start();
            
            Log.d(TAG, "Alarm sound started at max volume");
            
            // Auto-stop after 30 seconds
            new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(() -> {
                stopAlarm();
            }, 30000);
            
        } catch (Exception e) {
            Log.e(TAG, "Error playing alarm sound: " + e.getMessage());
        }
    }
    
    public static void vibrateDevice(Context context) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                VibratorManager vibratorManager = (VibratorManager) context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE);
                vibrator = vibratorManager.getDefaultVibrator();
            } else {
                vibrator = (Vibrator) context.getSystemService(Context.VIBRATOR_SERVICE);
            }
            
            if (vibrator != null && vibrator.hasVibrator()) {
                // Vibration pattern: wait 0ms, vibrate 500ms, wait 200ms, vibrate 500ms, repeat
                long[] pattern = {0, 500, 200, 500, 200, 500, 200, 500};
                
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createWaveform(pattern, 0)); // 0 = repeat from start
                } else {
                    vibrator.vibrate(pattern, 0);
                }
                Log.d(TAG, "Vibration started");
            }
        } catch (Exception e) {
            Log.e(TAG, "Error vibrating: " + e.getMessage());
        }
    }
    
    public static void stopAlarm() {
        try {
            if (mediaPlayer != null) {
                if (mediaPlayer.isPlaying()) {
                    mediaPlayer.stop();
                }
                mediaPlayer.release();
                mediaPlayer = null;
                Log.d(TAG, "Alarm sound stopped");
            }
            
            if (vibrator != null) {
                vibrator.cancel();
                vibrator = null;
                Log.d(TAG, "Vibration stopped");
            }
            
            releaseWakeLock();
        } catch (Exception e) {
            Log.e(TAG, "Error stopping alarm: " + e.getMessage());
        }
    }
}
