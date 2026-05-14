import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    Rectangle {
        anchors.fill: parent
        color: "#1c1c21"
        radius: 20

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 20

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Menu Główne"
                color: "white"
                font.pixelSize: 24
                font.family: "Segoe UI Black"
            }

            Button {
                Layout.alignment: Qt.AlignHCenter
                text: "📷  Trenuj z kamerką"
                font.pixelSize: 16

                contentItem: Text {
                    text: parent.text
                    color: "white"
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                background: Rectangle {
                    implicitWidth: 220
                    implicitHeight: 52
                    color: parent.hovered ? "#6D7AFF" : "#5865F2"
                    radius: 12
                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }
                }

                onClicked: Window.window.changePage("TrainingScreen.qml")
            }
        }
    }
}