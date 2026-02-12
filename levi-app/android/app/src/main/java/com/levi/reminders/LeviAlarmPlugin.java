package com.levi.reminders;

import android.content.Context;
import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "LeviAlarm")
public class LeviAlarmPlugin extends Plugin {
    private static final String TAG = "LeviAlarmPlugin";

    @PluginMethod
    public void playAlarm(PluginCall call) {
        Context context = getContext();
        Log.d(TAG, "Playing alarm from plugin");
        
        AlarmReceiver.playAlarmSound(context);
        AlarmReceiver.vibrateDevice(context);
        
        JSObject result = new JSObject();
        result.put("success", true);
        call.resolve(result);
    }

    @PluginMethod
    public void stopAlarm(PluginCall call) {
        Log.d(TAG, "Stopping alarm from plugin");
        
        AlarmReceiver.stopAlarm();
        
        JSObject result = new JSObject();
        result.put("success", true);
        call.resolve(result);
    }
}
