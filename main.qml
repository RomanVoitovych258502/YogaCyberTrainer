import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1050
    height: 700
    title: "Test"
    color: "#131316"

    QtObject {
        id: theme
        property color sidebar: "#1c1c21"
        property color blurple: "#5865F2"
        property color darkBtn: "#2b2d31"
        property string fontMain: "Segoe UI"
        property string fontTitle: "Segoe UI Black"
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
                    width: 64
                    height: 64
                    background: Rectangle { color: parent.hovered ? theme.blurple : theme.darkBtn; radius: 15 }
                    onClicked: App.navRequested("MenuScreen.qml")
                }
                Button {
                    width: 64
                    height: 64
                    background: Rectangle { color: parent.hovered ? theme.blurple : theme.darkBtn; radius: 15 }
                    onClicked: App.navRequested("ResultsScreen.qml")
                }
                Button {
                    width: 64
                    height: 64
                    background: Rectangle { color: parent.hovered ? theme.blurple : theme.darkBtn; radius: 15 }
                    onClicked: App.navRequested("ChatScreen.qml")
                }
                Button {
                    width: 64
                    height: 64
                    background: Rectangle { color: parent.hovered ? theme.blurple : theme.darkBtn; radius: 15 }
                    onClicked: App.navRequested("SettingsScreen.qml")
                }
            }
        }
    }
}