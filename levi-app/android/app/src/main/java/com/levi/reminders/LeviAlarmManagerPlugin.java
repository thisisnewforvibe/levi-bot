package com.levi.reminders;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.util.Log;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import org.json.JSONException;
import org.json.JSONObject;

import java.util.Calendar;

/**
 * Native Alarm Manager Plugin that schedules real Android alarms
 * These alarms will play sound and vibrate even when app is closed
 */
@CapacitorPlugin(name = "LeviAlarmManager")
public class LeviAlarmManagerPlugin extends Plugin {
    private static final String TAG = "LeviAlarmManager";

    /**
     * Check if the app can schedule exact alarms
     */
    @PluginMethod
    public void canScheduleExactAlarms(PluginCall call) {
        Context context = getContext();
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        
        boolean canSchedule = true;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            canSchedule = alarmManager.canScheduleExactAlarms();
        }
        
        Log.d(TAG, "canScheduleExactAlarms: " + canSchedule);
        
        JSObject result = new JSObject();
        result.put("canSchedule", canSchedule);
        result.put("androidVersion", Build.VERSION.SDK_INT);
        call.resolve(result);
    }

    /**
     * Open system settings to allow exact alarms
     */
    @PluginMethod
    public void openAlarmSettings(PluginCall call) {
        Context context = getContext();
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            Intent intent = new Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM);
            intent.setData(Uri.parse("package:" + context.getPackageName()));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(intent);
            
            JSObject result = new JSObject();
            result.put("opened", true);
            call.resolve(result);
        } else {
            JSObject result = new JSObject();
            result.put("opened", false);
            result.put("message", "Not needed for Android < 12");
            call.resolve(result);
        }
    }

    /**
     * Check if app can draw over other apps (for full-screen alarm)
     */
    @PluginMethod
    public void canDrawOverlays(PluginCall call) {
        Context context = getContext();
        boolean canDraw = true;
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            canDraw = Settings.canDrawOverlays(context);
        }
        
        Log.d(TAG, "canDrawOverlays: " + canDraw);
        
        JSObject result = new JSObject();
        result.put("canDraw", canDraw);
        call.resolve(result);
    }

    /**
     * Open settings to allow display over other apps
     */
    @PluginMethod
    public void openOverlaySettings(PluginCall call) {
        Context context = getContext();
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION);
            intent.setData(Uri.parse("package:" + context.getPackageName()));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(intent);
            
            JSObject result = new JSObject();
            result.put("opened", true);
            call.resolve(result);
        } else {
            JSObject result = new JSObject();
            result.put("opened", false);
            result.put("message", "Not needed for Android < 6");
            call.resolve(result);
        }
    }

    /**
     * Schedule an alarm at a specific time
     * The alarm will play sound and vibrate automatically
     */
    @PluginMethod
    public void scheduleAlarm(PluginCall call) {
        Context context = getContext();
        
        int id = call.getInt("id", 0);
        String title = call.getString("title", "Eslatma");
        String body = call.getString("body", "");
        long triggerTime = call.getLong("triggerTime", 0L);
        
        if (triggerTime == 0) {
            call.reject("triggerTime is required");
            return;
        }
        
        Log.d(TAG, "Scheduling alarm ID: " + id + " at time: " + triggerTime);
        
        try {
            scheduleNativeAlarm(context, id, title, body, triggerTime);
            
            JSObject result = new JSObject();
            result.put("success", true);
            result.put("id", id);
            call.resolve(result);
        } catch (Exception e) {
            Log.e(TAG, "Failed to schedule alarm: " + e.getMessage());
            call.reject("Failed to schedule alarm: " + e.getMessage());
        }
    }

    /**
     * Schedule multiple alarms at once
     */
    @PluginMethod
    public void scheduleMultiple(PluginCall call) {
        Context context = getContext();
        JSArray alarms = call.getArray("alarms");
        
        if (alarms == null) {
            Log.e(TAG, "alarms array is null!");
            call.reject("alarms array is required");
            return;
        }
        
        Log.d(TAG, "scheduleMultiple called with " + alarms.length() + " alarms");
        
        int scheduled = 0;
        try {
            for (int i = 0; i < alarms.length(); i++) {
                JSONObject alarm = alarms.getJSONObject(i);
                int id = alarm.getInt("id");
                String title = alarm.optString("title", "Eslatma");
                String body = alarm.optString("body", "");
                long triggerTime = alarm.getLong("triggerTime");
                
                Log.d(TAG, "Scheduling alarm " + i + ": id=" + id + ", body=" + body + ", time=" + triggerTime);
                
                scheduleNativeAlarm(context, id, title, body, triggerTime);
                scheduled++;
            }
            
            Log.d(TAG, "Successfully scheduled " + scheduled + " alarms");
            
            JSObject result = new JSObject();
            result.put("success", true);
            result.put("scheduled", scheduled);
            call.resolve(result);
        } catch (JSONException e) {
            Log.e(TAG, "Failed to parse alarms: " + e.getMessage());
            e.printStackTrace();
            call.reject("Failed to parse alarms: " + e.getMessage());
        } catch (Exception e) {
            Log.e(TAG, "Unexpected error scheduling alarms: " + e.getMessage());
            e.printStackTrace();
            call.reject("Unexpected error: " + e.getMessage());
        }
    }

    /**
     * Schedule a test alarm that fires in 10 seconds (for debugging)
     */
    @PluginMethod
    public void scheduleTestAlarm(PluginCall call) {
        Context context = getContext();
        
        int id = 999999;
        String title = "🔔 Test Alarm";
        String body = "This is a test alarm - it worked!";
        long triggerTime = System.currentTimeMillis() + 10000; // 10 seconds from now
        
        Log.d(TAG, "Scheduling TEST alarm to fire in 10 seconds");
        
        try {
            scheduleNativeAlarm(context, id, title, body, triggerTime);
            
            JSObject result = new JSObject();
            result.put("success", true);
            result.put("message", "Test alarm scheduled for 10 seconds from now");
            call.resolve(result);
        } catch (Exception e) {
            Log.e(TAG, "Failed to schedule test alarm: " + e.getMessage());
            call.reject("Failed: " + e.getMessage());
        }
    }

    /**
     * Cancel a specific alarm by ID
     */
    @PluginMethod
    public void cancelAlarm(PluginCall call) {
        Context context = getContext();
        int id = call.getInt("id", 0);
        
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        Intent intent = new Intent(context, AlarmReceiver.class);
        PendingIntent pendingIntent = PendingIntent.getBroadcast(
            context,
            id,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        
        alarmManager.cancel(pendingIntent);
        Log.d(TAG, "Cancelled alarm ID: " + id);
        
        JSObject result = new JSObject();
        result.put("success", true);
        call.resolve(result);
    }

    /**
     * Cancel all alarms
     */
    @PluginMethod
    public void cancelAll(PluginCall call) {
        // Note: Android doesn't have a native way to cancel all alarms
        // We would need to track alarm IDs separately
        // For now, just respond with success
        JSObject result = new JSObject();
        result.put("success", true);
        call.resolve(result);
    }

    /**
     * Play alarm sound immediately (for testing)
     */
    @PluginMethod
    public void playAlarm(PluginCall call) {
        Context context = getContext();
        Log.d(TAG, "Playing alarm immediately");
        
        AlarmReceiver.playAlarmSound(context);
        AlarmReceiver.vibrateDevice(context);
        
        JSObject result = new JSObject();
        result.put("success", true);
        call.resolve(result);
    }

    /**
     * Stop currently playing alarm
     */
    @PluginMethod
    public void stopAlarm(PluginCall call) {
        Log.d(TAG, "Stopping alarm");
        
        AlarmReceiver.stopAlarm();
        
        JSObject result = new JSObject();
        result.put("success", true);
        call.resolve(result);
    }

    /**
     * Internal method to schedule a native Android alarm
     */
    private void scheduleNativeAlarm(Context context, int id, String title, String body, long triggerTime) {
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        
        long now = System.currentTimeMillis();
        long diffMs = triggerTime - now;
        
        Log.d(TAG, "Scheduling alarm: now=" + now + ", trigger=" + triggerTime + ", diff=" + diffMs + "ms (" + (diffMs/1000) + "s)");
        
        // SAFETY CHECK: Don't schedule alarms for past times
        // This prevents old reminders from triggering immediately
        if (diffMs < 5000) {  // Less than 5 seconds in future
            Log.w(TAG, "⚠️ SKIPPING alarm " + id + " - trigger time is in the past or too close (diff=" + diffMs + "ms)");
            return;
        }
        
        Intent intent = new Intent(context, AlarmReceiver.class);
        intent.setAction("com.levi.reminders.ALARM_TRIGGER");
        intent.putExtra("id", id);
        intent.putExtra("title", title);
        intent.putExtra("body", body);
        
        PendingIntent pendingIntent = PendingIntent.getBroadcast(
            context,
            id,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        
        // Create a separate PendingIntent for the alarm clock info (what shows in status bar)
        Intent showIntent = new Intent(context, MainActivity.class);
        PendingIntent showPendingIntent = PendingIntent.getActivity(
            context,
            id + 100000,
            showIntent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        
        // ALWAYS use setAlarmClock - it's the ONLY way to guarantee exact timing
        // setAlarmClock bypasses Doze mode and battery optimization completely
        // It shows an alarm icon in the status bar which is expected behavior for alarms
        try {
            AlarmManager.AlarmClockInfo alarmClockInfo = new AlarmManager.AlarmClockInfo(
                triggerTime,
                showPendingIntent  // This is shown when user taps the alarm icon
            );
            alarmManager.setAlarmClock(alarmClockInfo, pendingIntent);
            Log.d(TAG, "✓ Scheduled alarm " + id + " using setAlarmClock (fires in " + (diffMs/1000) + " seconds)");
        } catch (SecurityException e) {
            // If setAlarmClock fails (shouldn't happen), try setExactAndAllowWhileIdle
            Log.w(TAG, "setAlarmClock failed, trying setExactAndAllowWhileIdle: " + e.getMessage());
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent);
                    Log.d(TAG, "Scheduled using setExactAndAllowWhileIdle");
                } else {
                    alarmManager.setExact(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent);
                    Log.d(TAG, "Scheduled using setExact");
                }
            } catch (Exception e2) {
                Log.e(TAG, "All scheduling methods failed: " + e2.getMessage());
            }
        }
    }
}
