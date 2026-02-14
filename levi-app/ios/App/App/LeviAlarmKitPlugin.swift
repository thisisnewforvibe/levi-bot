import Foundation
import Capacitor
import UserNotifications

#if canImport(AlarmKit)
import AlarmKit
import AppIntents
import ActivityKit
import SwiftUI

// MARK: - AlarmKit Data Types (iOS 26+)

@available(iOS 26.0, *)
struct LeviAlarmData: AlarmMetadata {
    var reminderText: String = ""
    var reminderId: Int = 0
}

// MARK: - Alarm Metadata Storage (persists reminder data for follow-ups)
class AlarmMetadataStore {
    static let shared = AlarmMetadataStore()
    private let defaults = UserDefaults.standard
    private let prefix = "levi_alarm_"
    
    func save(uuid: String, reminderId: Int, text: String) {
        defaults.set(["reminderId": reminderId, "text": text], forKey: prefix + uuid)
        print("💾 Saved alarm metadata: uuid=\(uuid), reminderId=\(reminderId)")
    }
    
    func get(uuid: String) -> (reminderId: Int, text: String)? {
        guard let dict = defaults.dictionary(forKey: prefix + uuid),
              let reminderId = dict["reminderId"] as? Int,
              let text = dict["text"] as? String else { return nil }
        return (reminderId, text)
    }
    
    func remove(uuid: String) {
        defaults.removeObject(forKey: prefix + uuid)
    }
    
    /// Get all stored alarm UUIDs
    func allAlarmUUIDs() -> [String] {
        return defaults.dictionaryRepresentation().keys
            .filter { $0.hasPrefix(prefix) }
            .map { String($0.dropFirst(prefix.count)) }
    }
}

// MARK: - Follow-up Notification Scheduler
class FollowUpScheduler {
    static let shared = FollowUpScheduler()
    
    static let FOLLOW_UP_DELAY: TimeInterval = 20 * 60  // 20 minutes after stop
    static let FOLLOW_UP_REPEAT_DELAY: TimeInterval = 30 * 60  // 30 minutes after "No"
    static let FOLLOW_UP_ID_OFFSET = 2000000  // Offset to avoid ID collision
    
    /// Schedule a follow-up notification asking "Did you finish your task?"
    func scheduleFollowUp(reminderId: Int, taskText: String, delaySeconds: TimeInterval) {
        let center = UNUserNotificationCenter.current()
        
        let content = UNMutableNotificationContent()
        content.title = "⏰ Vazifa bajarildimi?"
        content.body = taskText
        content.sound = UNNotificationSound.default
        content.categoryIdentifier = "LEVI_FOLLOWUP"
        content.userInfo = [
            "reminderId": reminderId,
            "taskText": taskText,
            "isFollowUp": true
        ]
        
        if #available(iOS 15.0, *) {
            content.interruptionLevel = .timeSensitive
        }
        
        let followUpId = reminderId + FollowUpScheduler.FOLLOW_UP_ID_OFFSET
        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: delaySeconds, repeats: false)
        let request = UNNotificationRequest(identifier: String(followUpId), content: content, trigger: trigger)
        
        center.add(request) { error in
            if let error = error {
                print("❌ Failed to schedule follow-up: \(error)")
            } else {
                print("✅ Follow-up scheduled: reminderId=\(reminderId), delay=\(Int(delaySeconds/60))min")
            }
        }
    }
}

// MARK: - Stop Alarm Intent
@available(iOS 26.0, *)
struct StopLeviAlarmIntent: LiveActivityIntent {
    static var title: LocalizedStringResource = "To'xtatish"
    
    func perform() async throws -> some IntentResult {
        print("🛑 Alarm stopped via intent - scheduling follow-up")
        
        // Find which alarm was just stopped and schedule follow-up
        // Check all stored alarm metadata and schedule follow-ups for those
        // whose alarms are no longer active
        let store = AlarmMetadataStore.shared
        let storedUUIDs = store.allAlarmUUIDs()
        
        if #available(iOS 26.0, *) {
            let activeAlarms = (try? AlarmManager.shared.alarms) ?? []
            // Only consider alarms that are still scheduled or alerting (not stopped/removed)
            let stillActiveUUIDs = Set(activeAlarms.filter { $0.state == .scheduled || $0.state == .alerting }.map { $0.id.uuidString })
            
            print("📋 Active alarms: \(stillActiveUUIDs.count), Stored metadata: \(storedUUIDs.count)")
            
            for uuid in storedUUIDs {
                if !stillActiveUUIDs.contains(uuid), let meta = store.get(uuid: uuid) {
                    // This alarm was stopped — cancel pre-scheduled fallback, schedule fresh follow-up
                    let followUpId = String(meta.reminderId + FollowUpScheduler.FOLLOW_UP_ID_OFFSET)
                    let backupId = String(meta.reminderId + 3000000)
                    UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: [followUpId, backupId])
                    UNUserNotificationCenter.current().removeDeliveredNotifications(withIdentifiers: [backupId])
                    
                    FollowUpScheduler.shared.scheduleFollowUp(
                        reminderId: meta.reminderId,
                        taskText: meta.text,
                        delaySeconds: FollowUpScheduler.FOLLOW_UP_DELAY
                    )
                    store.remove(uuid: uuid)
                    print("📋 Follow-up scheduled for stopped alarm: \(meta.reminderId)")
                }
            }
        }
        
        return .result()
    }
}

// MARK: - Snooze Alarm Intent (reschedules 10 min later)
@available(iOS 26.0, *)
struct SnoozeLeviAlarmIntent: LiveActivityIntent {
    static var title: LocalizedStringResource = "10 daqiqa"
    
    func perform() async throws -> some IntentResult {
        // When using .countdown behavior, AlarmKit handles the snooze automatically
        print("⏰ Alarm snoozed via intent — no follow-up until alarm is fully stopped")
        return .result()
    }
}
#endif

// MARK: - Capacitor Plugin (bridges JS to AlarmKit)

@objc(LeviAlarmKitPlugin)
class LeviAlarmKitPlugin: CAPPlugin {
    
    /// Convert integer reminder ID to deterministic UUID
    private func uuidFromReminderId(_ id: Int) -> UUID {
        let uuidString = String(format: "00000000-0000-0000-0000-%012x", abs(id))
        return UUID(uuidString: uuidString) ?? UUID()
    }
    
    // MARK: - Plugin Methods
    
    /// Check if AlarmKit is available (iOS 26+)
    @objc func isAvailable(_ call: CAPPluginCall) {
        if #available(iOS 26.0, *) {
            #if canImport(AlarmKit)
            call.resolve(["available": true])
            #else
            call.resolve(["available": false])
            #endif
        } else {
            call.resolve(["available": false])
        }
    }
    
    /// Request AlarmKit authorization
    @objc func requestAuthorization(_ call: CAPPluginCall) {
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            Task {
                do {
                    let state = try await AlarmManager.shared.requestAuthorization()
                    let authorized = state == .authorized
                    print("🔔 AlarmKit authorization: \(state) (authorized: \(authorized))")
                    call.resolve(["authorized": authorized, "state": String(describing: state)])
                } catch {
                    print("❌ AlarmKit authorization error: \(error)")
                    call.reject("Authorization failed: \(error.localizedDescription)")
                }
            }
        } else {
            call.resolve(["authorized": false, "state": "unavailable"])
        }
        #else
        call.resolve(["authorized": false, "state": "unavailable"])
        #endif
    }
    
    /// Schedule a real alarm using AlarmKit
    @objc func scheduleAlarm(_ call: CAPPluginCall) {
        let reminderId = call.getInt("id") ?? 0
        let title = call.getString("title") ?? "🔔 Eslatma"
        let body = call.getString("body") ?? ""
        let triggerTime = call.getDouble("triggerTime") ?? 0
        
        guard reminderId > 0 else {
            call.reject("Invalid alarm ID")
            return
        }
        
        let fireDate = Date(timeIntervalSince1970: triggerTime / 1000.0)
        let alarmUUID = uuidFromReminderId(reminderId)
        
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            Task {
                do {
                    try await self.scheduleWithAlarmKit(
                        id: alarmUUID,
                        title: title,
                        body: body,
                        fireDate: fireDate,
                        reminderId: reminderId
                    )
                    call.resolve([
                        "success": true,
                        "id": reminderId,
                        "uuid": alarmUUID.uuidString
                    ])
                } catch {
                    print("❌ AlarmKit schedule error: \(error)")
                    call.reject("Failed to schedule alarm: \(error.localizedDescription)")
                }
            }
            return
        }
        #endif
        
        call.reject("AlarmKit not available")
    }
    
    /// Schedule multiple alarms at once
    @objc func scheduleMultiple(_ call: CAPPluginCall) {
        guard let alarmsArray = call.getArray("alarms") as? [[String: Any]] else {
            call.reject("Invalid alarms array")
            return
        }
        
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            Task {
                var scheduled = 0
                var errors: [String] = []
                
                for alarmDict in alarmsArray {
                    let reminderId = alarmDict["id"] as? Int ?? 0
                    let title = alarmDict["title"] as? String ?? "🔔 Eslatma"
                    let body = alarmDict["body"] as? String ?? ""
                    let triggerTime = alarmDict["triggerTime"] as? Double ?? 0
                    
                    guard reminderId > 0, triggerTime > 0 else { continue }
                    
                    let fireDate = Date(timeIntervalSince1970: triggerTime / 1000.0)
                    let alarmUUID = self.uuidFromReminderId(reminderId)
                    
                    // Only schedule if in the future
                    guard fireDate > Date() else {
                        print("⏭ Skipping past alarm \(reminderId)")
                        continue
                    }
                    
                    do {
                        try await self.scheduleWithAlarmKit(
                            id: alarmUUID,
                            title: title,
                            body: body,
                            fireDate: fireDate,
                            reminderId: reminderId
                        )
                        scheduled += 1
                    } catch {
                        errors.append("Alarm \(reminderId): \(error.localizedDescription)")
                        print("❌ Failed to schedule alarm \(reminderId): \(error)")
                    }
                }
                
                print("✅ AlarmKit: scheduled \(scheduled)/\(alarmsArray.count) alarms")
                call.resolve([
                    "success": true,
                    "scheduled": scheduled,
                    "total": alarmsArray.count,
                    "errors": errors
                ])
            }
            return
        }
        #endif
        
        call.reject("AlarmKit not available")
    }
    
    /// Cancel a scheduled alarm
    @objc func cancelAlarm(_ call: CAPPluginCall) {
        let reminderId = call.getInt("id") ?? 0
        guard reminderId > 0 else {
            call.reject("Invalid alarm ID")
            return
        }
        
        let alarmUUID = uuidFromReminderId(reminderId)
        
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            do {
                try AlarmManager.shared.cancel(id: alarmUUID)
                print("🗑 AlarmKit alarm cancelled: \(reminderId) (\(alarmUUID))")
            } catch {
                print("⚠️ Cancel alarm error (may already be gone): \(error)")
            }
            // Also cancel backup notification and pre-scheduled follow-up
            let backupId = String(reminderId + 3000000)
            let followUpId = String(reminderId + FollowUpScheduler.FOLLOW_UP_ID_OFFSET)
            UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: [backupId, followUpId])
            UNUserNotificationCenter.current().removeDeliveredNotifications(withIdentifiers: [backupId])
            AlarmMetadataStore.shared.remove(uuid: alarmUUID.uuidString)
            call.resolve(["success": true])
            return
        }
        #endif
        
        call.resolve(["success": true])
    }
    
    /// Cancel all alarms
    @objc func cancelAll(_ call: CAPPluginCall) {
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            do {
                let alarms = try AlarmManager.shared.alarms
                for alarm in alarms {
                    try? AlarmManager.shared.cancel(id: alarm.id)
                }
                print("🗑 All AlarmKit alarms cancelled (\(alarms.count))")
                call.resolve(["success": true, "cancelled": alarms.count])
            } catch {
                print("⚠️ Cancel all error: \(error)")
                call.resolve(["success": true, "cancelled": 0])
            }
            // Also cancel all backup notifications and follow-ups, clear metadata
            UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
            UNUserNotificationCenter.current().removeAllDeliveredNotifications()
            for uuid in AlarmMetadataStore.shared.allAlarmUUIDs() {
                AlarmMetadataStore.shared.remove(uuid: uuid)
            }
            return
        }
        #endif
        
        call.resolve(["success": true, "cancelled": 0])
    }
    
    /// Stop a currently alerting alarm
    @objc func stopAlarm(_ call: CAPPluginCall) {
        let reminderId = call.getInt("id") ?? 0
        let alarmUUID = uuidFromReminderId(reminderId)
        
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            do {
                try AlarmManager.shared.stop(id: alarmUUID)
                print("🛑 AlarmKit alarm stopped: \(reminderId)")
            } catch {
                print("⚠️ Stop alarm error: \(error)")
            }
            // Cancel backup notification (alarm was manually stopped)
            let backupId = String(reminderId + 3000000)
            UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: [backupId])
            UNUserNotificationCenter.current().removeDeliveredNotifications(withIdentifiers: [backupId])
            call.resolve(["success": true])
            return
        }
        #endif
        
        call.resolve(["success": true])
    }
    
    // MARK: - AlarmKit Scheduling Implementation
    
    #if canImport(AlarmKit)
    @available(iOS 26.0, *)
    private func scheduleWithAlarmKit(id: UUID, title: String, body: String, fireDate: Date, reminderId: Int) async throws {
        
        // Create the alarm alert presentation
        let snoozeButton = AlarmButton(
            text: "⏰ 10 daqiqa",
            textColor: .white,
            systemImageName: "alarm"
        )
        
        let stopButton = AlarmButton(
            text: "⏹ To'xtatish",
            textColor: .red,
            systemImageName: "stop.fill"
        )
        
        let alertContent = AlarmPresentation.Alert(
            title: LocalizedStringResource(stringLiteral: body),
            stopButton: stopButton,
            secondaryButton: snoozeButton,
            secondaryButtonBehavior: .countdown
        )
        
        // Create presentation (alert only, no countdown/paused UI)
        let presentation = AlarmPresentation(alert: alertContent)
        
        // Create attributes with metadata
        let attributes = AlarmAttributes<LeviAlarmData>(
            presentation: presentation,
            metadata: LeviAlarmData(reminderText: body, reminderId: reminderId),
            tintColor: .blue
        )
        
        // Create alarm configuration
        // postAlert = 600 seconds (10 min) - for snooze repeat
        let config = AlarmManager.AlarmConfiguration<LeviAlarmData>(
            countdownDuration: Alarm.CountdownDuration(preAlert: nil, postAlert: 600),
            schedule: .fixed(fireDate),
            attributes: attributes,
            stopIntent: StopLeviAlarmIntent(),
            secondaryIntent: SnoozeLeviAlarmIntent(),
            sound: .default
        )
        
        // Schedule the alarm
        let alarm = try await AlarmManager.shared.schedule(id: id, configuration: config)
        
        // Save metadata so follow-up can be scheduled when alarm is stopped
        AlarmMetadataStore.shared.save(uuid: id.uuidString, reminderId: reminderId, text: body)
        
        print("✅ AlarmKit alarm scheduled: ID=\(alarm.id), state=\(alarm.state), fire=\(fireDate)")
        
        // Schedule backup UNNotification for foreground alarm playback
        // (AlarmKit may not show full-screen alarm when device is unlocked)
        self.scheduleBackupNotification(reminderId: reminderId, body: body, fireDate: fireDate)
        
        // Pre-schedule fallback follow-up at alarm_time + 25 minutes
        // StopLeviAlarmIntent will cancel this and schedule a fresh one from stop time
        let followUpDelay = fireDate.timeIntervalSinceNow + (25 * 60)
        if followUpDelay > 0 {
            FollowUpScheduler.shared.scheduleFollowUp(
                reminderId: reminderId,
                taskText: body,
                delaySeconds: followUpDelay
            )
            print("📋 Fallback follow-up pre-scheduled at alarm+25min")
        }
    }
    #endif
    
    // MARK: - Backup Notification (for foreground alarm when device is unlocked)
    
    private func scheduleBackupNotification(reminderId: Int, body: String, fireDate: Date) {
        let content = UNMutableNotificationContent()
        content.title = "🔔 Eslatma"
        content.body = body
        content.sound = UNNotificationSound(named: UNNotificationSoundName("alarm.wav"))
        content.categoryIdentifier = "LEVI_ALARM"
        content.userInfo = [
            "reminderId": reminderId,
            "taskText": body,
            "isAlarmKitBackup": true,
            "isFollowUp": false
        ]
        
        if #available(iOS 15.0, *) {
            content.interruptionLevel = .timeSensitive
        }
        
        let backupId = reminderId + 3000000
        let components = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute, .second], from: fireDate)
        let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: false)
        let request = UNNotificationRequest(identifier: String(backupId), content: content, trigger: trigger)
        
        UNUserNotificationCenter.current().add(request) { error in
            if let error = error {
                print("⚠️ Failed to schedule backup notification: \(error)")
            } else {
                print("✅ Backup notification scheduled for foreground alarm: \(reminderId)")
            }
        }
    }
}
