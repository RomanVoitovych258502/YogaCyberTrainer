import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: window
    visible: true
    width: 1050
    height: 700
    title: "test z kamerka"
    color: "#131316"

    QtObject {
        id: theme
        property color sidebar: "#1c1c21"
        property color blurple: "#5865F2"
    }

    Connections {
        target: App
//       function onNavRequested(page) {
//           if(loader.source.toString().indexOf("TrainingScreen") !== -1 && page !== "TrainingScreen.qml") {
//               TrainingCtrl.stopTraining()
//           }
//           loader.source = page
//       }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            width: 80
            color: theme.sidebar

            Column {
                anchors.centerIn: parent
                spacing: 30

                Button {
                    text: "🏠"
                    width: 64
                    height: 64
                    font.pixelSize: 36
                    background: Rectangle { color: parent.hovered ? theme.blurple : "transparent"; radius: 15 }
//                  onClicked: App.navRequested("TrainingScreen.qml")
                    onClicked: console.log("Kliknięto menu główne (Puste)")
                }

                Button {
                    text: "🏆"
                    width: 64
                    height: 64
                    font.pixelSize: 36
                    background: Rectangle { color: parent.hovered ? theme.blurple : "transparent"; radius: 15 }
                    onClicked: console.log("Kliknięto rekordy (Puste)")
                }
                Button {
                    text: "💬"
                    width: 64
                    height: 64
                    font.pixelSize: 36
                    background: Rectangle { color: parent.hovered ? theme.blurple : "transparent"; radius: 15 }
                    onClicked: console.log("Kliknięto chat (Puste)")
                }
                Button {
                    text: "⚙️"
                    width: 64
                    height: 64
                    font.pixelSize: 36
                    background: Rectangle { color: parent.hovered ? theme.blurple : "transparent"; radius: 15 }
                    onClicked: console.log("Kliknięto ustawienia (Puste)")
                }
            }
        }

//        Loader {
//            id: loader
//            Layout.fillWidth: true
//            Layout.fillHeight: true
//            Layout.margins: 20

//            source: "TrainingScreen.qml"
//        }
    }
}