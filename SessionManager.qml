import QtQuick

Item {
    id: root

    property double startTime: 0
    property var currentPoses: []
    property string lastTime: "00:00"
    property string lastScore: "0%"
    property bool wasRunning: false
    property alias historyModel: sessionHistoryModel

    ListModel {
        id: sessionHistoryModel
    }

    Connections {
        target: TrainingCtrl
        
        function onPoseCompleted(pose) {
            var cleanName = pose.replace(/_/g, " ")
            root.currentPoses.push(cleanName)
        }
        
        function onFrameUpdated() {
            if (TrainingCtrl.isRunning !== root.wasRunning) {
                root.wasRunning = TrainingCtrl.isRunning
                
                if (root.wasRunning) {
                    root.startTime = new Date().getTime()
                    root.currentPoses = []
                } else {
                    if (root.startTime > 0) {
                        var durationSec = Math.floor((new Date().getTime() - root.startTime) / 1000)
                        
                        var minsStr = ("0" + Math.floor(durationSec / 60)).slice(-2)
                        var secsStr = ("0" + (durationSec % 60)).slice(-2)
                        root.lastTime = minsStr + ":" + secsStr
                        
                        root.lastScore = Math.min(100, root.currentPoses.length * 20) + "%"
                        
                        var posesStr = root.currentPoses.length > 0 ? root.currentPoses.join(", ") : "Brak zaliczonych póz"
                            
                        var d = new Date()
                        var dateStr = d.toLocaleDateString() + " " + d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
                        
                        sessionHistoryModel.insert(0, {
                            "date": dateStr,
                            "avgScore": root.lastScore,
                            "poses": posesStr
                        })
                        
                        root.startTime = 0
                    }
                }
            }
        }
    }
}
