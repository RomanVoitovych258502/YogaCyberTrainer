import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    Component.onCompleted: TrainingCtrl.startTraining()
    Component.onDestruction: TrainingCtrl.stopTraining()

    Connections {
        target: TrainingCtrl
        function onFrameUpdated() {
            videoImage.source = "image://video/frame?id=" + Math.random()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#2b2d31"
        radius: 20

        Image {
            id: videoImage
            anchors.fill: parent
            anchors.margins: 10
            fillMode: Image.PreserveAspectFit
        }
        Button {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 20
            text: "🔄"
            onClicked: TrainingCtrl.rotateCamera()
        }

        Text {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottomMargin: 20
            text: TrainingCtrl.currentLetter
            color: TrainingCtrl.currentLetter === "?" ? "#FF5555" : "#00FFD1"
            font.pixelSize: 40
            font.bold: true
        }
    }
}