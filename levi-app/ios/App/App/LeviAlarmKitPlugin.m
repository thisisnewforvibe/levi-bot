#import <Capacitor/Capacitor.h>

CAP_PLUGIN(LeviAlarmKitPlugin, "LeviAlarmKit",
    CAP_PLUGIN_METHOD(isAvailable, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(requestAuthorization, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(scheduleAlarm, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(scheduleMultiple, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(cancelAlarm, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(cancelAll, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(stopAlarm, CAPPluginReturnPromise);
)
