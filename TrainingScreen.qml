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
            cache: false
        }
    }
}