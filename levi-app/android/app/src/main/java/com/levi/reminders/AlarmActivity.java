package com.levi.reminders;

import android.app.Activity;
import android.app.KeyguardManager;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.TextView;
import android.util.Log;

/**
 * Full-screen alarm activity that shows even when phone is locked
 */
public class AlarmActivity extends Activity {
    private static final String TAG = "AlarmActivity";
    
    private int alarmId;
    private String alarmTitle;
    private String alarmBody;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        Log.d(TAG, "AlarmActivity onCreate");
        
        // Make the activity show over lock screen
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
            KeyguardManager keyguardManager = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
            if (keyguardManager != null) {
                keyguardManager.requestDismissKeyguard(this, null);
            }
        } else {
            getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED |
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON |
                WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
            );
        }
        
        // Keep screen on while alarm is showing
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        
        // Get alarm details from intent
        Intent intent = getIntent();
        alarmId = intent.getIntExtra("id", 0);
        alarmTitle = intent.getStringExtra("title");
        alarmBody = intent.getStringExtra("body");
        
        if (alarmBody == null) alarmBody = "Eslatma";
        if (alarmTitle == null) alarmTitle = "🔔 Eslatma";
        
        Log.d(TAG, "Alarm: id=" + alarmId + ", body=" + alarmBody);
        
        // Set the layout
        setContentView(R.layout.activity_alarm);
        
        // Set alarm text
        TextView titleView = findViewById(R.id.alarm_title);
        TextView bodyView = findViewById(R.id.alarm_body);
        
        if (titleView != null) titleView.setText(alarmTitle);
        if (bodyView != null) bodyView.setText(alarmBody);
        
        // Done button - "Bajaraman" (I will do it)
        Button doneButton = findViewById(R.id.btn_done);
        if (doneButton != null) {
            doneButton.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    Log.d(TAG, "Done button clicked");
                    stopAlarmAndFinish();
                    // Mark as done via broadcast
                    Intent doneIntent = new Intent(AlarmActivity.this, AlarmReceiver.class);
                    doneIntent.setAction(AlarmReceiver.ACTION_DONE);
                    doneIntent.putExtra("id", alarmId);
                    sendBroadcast(doneIntent);
                }
            });
        }
        
        // Snooze button - "10 daqiqa"
        Button snoozeButton = findViewById(R.id.btn_snooze);
        if (snoozeButton != null) {
            snoozeButton.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    Log.d(TAG, "Snooze button clicked");
                    stopAlarmAndFinish();
                    // Snooze via broadcast
                    Intent snoozeIntent = new Intent(AlarmActivity.this, AlarmReceiver.class);
                    snoozeIntent.setAction(AlarmReceiver.ACTION_SNOOZE);
                    snoozeIntent.putExtra("id", alarmId);
                    snoozeIntent.putExtra("title", alarmTitle);
                    snoozeIntent.putExtra("body", alarmBody);
                    sendBroadcast(snoozeIntent);
                }
            });
        }
    }
    
    private void stopAlarmAndFinish() {
        // Stop alarm sound
        AlarmReceiver.stopAlarm();
        // Cancel the notification
        android.app.NotificationManager notificationManager = 
            (android.app.NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (notificationManager != null) {
            notificationManager.cancel(alarmId);
        }
        finish();
    }
    
    @Override
    public void onBackPressed() {
        // Don't allow back button to dismiss alarm - user must tap a button
        // Just snooze if they press back
        Log.d(TAG, "Back pressed - snoozing");
        stopAlarmAndFinish();
        Intent snoozeIntent = new Intent(this, AlarmReceiver.class);
        snoozeIntent.setAction(AlarmReceiver.ACTION_SNOOZE);
        snoozeIntent.putExtra("id", alarmId);
        snoozeIntent.putExtra("title", alarmTitle);
        snoozeIntent.putExtra("body", alarmBody);
        sendBroadcast(snoozeIntent);
    }
}
