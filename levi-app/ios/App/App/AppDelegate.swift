import UIKit
import Capacitor
import UserNotifications
import AVFoundation
import AudioToolbox

#if canImport(AlarmKit)
import AlarmKit
#endif

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate, UNUserNotificationCenterDelegate {

    var window: UIWindow?
    var alarmPlayer: AVAudioPlayer?
    var vibrationTimer: Timer?
    var alarmStopTimer: Timer?

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Set notification delegate to handle foreground notifications
        UNUserNotificationCenter.current().delegate = self
        
        // Request AlarmKit authorization (iOS 26+)
        requestAlarmKitAuthorization()
        
        // Register notification categories as fallback for older iOS
        registerNotificationCategories()
        
        // Re-register categories after Capacitor plugins initialize
        // (Capacitor's LocalNotifications plugin overwrites categories with setNotificationCategories)
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) { [weak self] in
            self?.mergeNotificationCategories()
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 8.0) { [weak self] in
            self?.mergeNotificationCategories()
        }
        
        // Configure audio session for alarm playback (plays through speaker even in silent mode)
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: [.mixWithOthers])
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            print("Failed to configure audio session: \(error)")
        }
        
        return true
    }
    
    // MARK: - AlarmKit Authorization (iOS 26+)
    
    func requestAlarmKitAuthorization() {
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            Task {
                do {
                    let state = try await AlarmManager.shared.requestAuthorization()
                    print("✅ AlarmKit authorization state: \(state)")
                } catch {
                    print("⚠️ AlarmKit authorization error: \(error)")
                }
            }
        }
        #endif
    }
    
    // MARK: - Notification Categories (fallback for iOS < 26 + follow-up for all)
    
    func registerNotificationCategories() {
        // --- Alarm category (fallback for iOS < 26) ---
        let stopAction = UNNotificationAction(
            identifier: "STOP_ALARM",
            title: "⏹ To'xtatish",
            options: [.destructive, .foreground]
        )
        
        let snoozeAction = UNNotificationAction(
            identifier: "SNOOZE_ALARM",
            title: "⏰ 10 daqiqa",
            options: []
        )
        
        // --- Follow-up category (Yes/No) - used on ALL iOS versions ---
        let yesAction = UNNotificationAction(
            identifier: "FOLLOWUP_YES",
            title: "✅ Ha, bajardim",
            options: [.foreground]
        )
        
        let noAction = UNNotificationAction(
            identifier: "FOLLOWUP_NO",
            title: "❌ Yo'q, hali",
            options: []
        )
        
        if #available(iOS 15.0, *) {
            let alarmCategory = UNNotificationCategory(
                identifier: "LEVI_ALARM",
                actions: [stopAction, snoozeAction],
                intentIdentifiers: [],
                hiddenPreviewsBodyPlaceholder: "Eslatma",
                options: [.customDismissAction, .hiddenPreviewsShowTitle]
            )
            let followUpCategory = UNNotificationCategory(
                identifier: "LEVI_FOLLOWUP",
                actions: [yesAction, noAction],
                intentIdentifiers: [],
                hiddenPreviewsBodyPlaceholder: "Vazifa",
                options: [.customDismissAction, .hiddenPreviewsShowTitle]
            )
            UNUserNotificationCenter.current().setNotificationCategories([alarmCategory, followUpCategory])
        } else {
            let alarmCategory = UNNotificationCategory(
                identifier: "LEVI_ALARM",
                actions: [stopAction, snoozeAction],
                intentIdentifiers: [],
                options: [.customDismissAction]
            )
            let followUpCategory = UNNotificationCategory(
                identifier: "LEVI_FOLLOWUP",
                actions: [yesAction, noAction],
                intentIdentifiers: [],
                options: [.customDismissAction]
            )
            UNUserNotificationCenter.current().setNotificationCategories([alarmCategory, followUpCategory])
        }
        
        print("✅ Notification categories registered (alarm + follow-up)")
    }
    
    /// Merge our custom categories with whatever Capacitor has set (non-destructive)
    func mergeNotificationCategories() {
        let center = UNUserNotificationCenter.current()
        center.getNotificationCategories { [weak self] existingCategories in
            guard self != nil else { return }
            
            let hasAlarm = existingCategories.contains { $0.identifier == "LEVI_ALARM" }
            let hasFollowUp = existingCategories.contains { $0.identifier == "LEVI_FOLLOWUP" }
            
            if hasAlarm && hasFollowUp {
                print("✅ Categories already present (\(existingCategories.count) total)")
                return
            }
            
            var updatedCategories = existingCategories
            
            if !hasAlarm {
                let stopAction = UNNotificationAction(identifier: "STOP_ALARM", title: "⏹ To'xtatish", options: [.destructive, .foreground])
                let snoozeAction = UNNotificationAction(identifier: "SNOOZE_ALARM", title: "⏰ 10 daqiqa", options: [])
                let alarmCategory = UNNotificationCategory(identifier: "LEVI_ALARM", actions: [stopAction, snoozeAction], intentIdentifiers: [], options: [.customDismissAction])
                updatedCategories.insert(alarmCategory)
            }
            
            if !hasFollowUp {
                let yesAction = UNNotificationAction(identifier: "FOLLOWUP_YES", title: "✅ Ha, bajardim", options: [.foreground])
                let noAction = UNNotificationAction(identifier: "FOLLOWUP_NO", title: "❌ Yo'q, hali", options: [])
                let followUpCategory = UNNotificationCategory(identifier: "LEVI_FOLLOWUP", actions: [yesAction, noAction], intentIdentifiers: [], options: [.customDismissAction])
                updatedCategories.insert(followUpCategory)
            }
            
            center.setNotificationCategories(updatedCategories)
            print("✅ Merged categories: added missing ones, total=\(updatedCategories.count)")
        }
    }

    // MARK: - Alarm Playback (fallback for foreground on older iOS)
    
    func startAlarm() {
        stopAlarm()
        
        do {
            try AVAudioSession.sharedInstance().setCategory(.playback, mode: .default, options: [])
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            print("Audio session error: \(error)")
        }
        
        if let soundURL = Bundle.main.url(forResource: "alarm", withExtension: "wav") {
            do {
                alarmPlayer = try AVAudioPlayer(contentsOf: soundURL)
                alarmPlayer?.numberOfLoops = -1
                alarmPlayer?.volume = 1.0
                alarmPlayer?.prepareToPlay()
                alarmPlayer?.play()
                print("🔔 Alarm started playing (looping)")
            } catch {
                print("Failed to play alarm: \(error)")
            }
        }
        
        DispatchQueue.main.async {
            AudioServicesPlaySystemSound(kSystemSoundID_Vibrate)
            self.vibrationTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
                AudioServicesPlaySystemSound(kSystemSoundID_Vibrate)
            }
        }
        
        DispatchQueue.main.async {
            self.alarmStopTimer = Timer.scheduledTimer(withTimeInterval: 60.0, repeats: false) { [weak self] _ in
                self?.stopAlarm()
            }
        }
    }
    
    func stopAlarm() {
        alarmPlayer?.stop()
        alarmPlayer = nil
        vibrationTimer?.invalidate()
        vibrationTimer = nil
        alarmStopTimer?.invalidate()
        alarmStopTimer = nil
    }

    // MARK: - Notification Handling (for fallback notifications on iOS < 26)

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        // On iOS 26+ with AlarmKit, alarms are handled natively - these are only follow-up notifications
        // On older iOS, play alarm for alarm-type notifications
        let categoryId = notification.request.content.categoryIdentifier
        if categoryId == "LEVI_ALARM" {
            startAlarm()
        }
        
        if #available(iOS 14.0, *) {
            completionHandler([.banner, .sound, .badge])
        } else {
            completionHandler([.alert, .sound, .badge])
        }
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        stopAlarm()
        
        let actionId = response.actionIdentifier
        let userInfo = response.notification.request.content.userInfo
        let categoryId = response.notification.request.content.categoryIdentifier
        let isFollowUp = userInfo["isFollowUp"] as? Bool ?? (categoryId == "LEVI_FOLLOWUP")
        let reminderId = userInfo["reminderId"] as? Int ?? 0
        let taskText = userInfo["taskText"] as? String ?? response.notification.request.content.body
        
        if isFollowUp {
            // Handle follow-up notification (Yes/No)
            if actionId == "FOLLOWUP_YES" || actionId == "yes" {
                // User confirmed task done - let Capacitor/JS know
                print("✅ Follow-up: Task confirmed done, reminderId=\(reminderId)")
                // Forward to Capacitor to mark as done
            } else {
                // User clicked "No", tapped, or dismissed — reschedule in 30 minutes
                print("❌ Follow-up: Task not done, rescheduling in 30min, reminderId=\(reminderId)")
                FollowUpScheduler.shared.scheduleFollowUp(
                    reminderId: reminderId,
                    taskText: taskText,
                    delaySeconds: FollowUpScheduler.FOLLOW_UP_REPEAT_DELAY
                )
            }
        }
        
        // Let Capacitor handle all notification responses (for JS callback)
        NotificationCenter.default.post(name: Notification.Name("LocalNotificationActionPerformed"), object: response)
        completionHandler()
    }

    // MARK: - App Lifecycle

    func applicationWillResignActive(_ application: UIApplication) {
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
    }

    func applicationWillEnterForeground(_ application: UIApplication) {
    }

    func applicationDidBecomeActive(_ application: UIApplication) {
        stopAlarm()
    }

    func applicationWillTerminate(_ application: UIApplication) {
        stopAlarm()
    }

    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        return ApplicationDelegateProxy.shared.application(app, open: url, options: options)
    }

    func application(_ application: UIApplication, continue userActivity: NSUserActivity, restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {
        return ApplicationDelegateProxy.shared.application(application, continue: userActivity, restorationHandler: restorationHandler)
    }
}
