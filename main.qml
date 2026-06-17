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

    property string activePage: "MainMenu.qml"
    property string pendingPage: ""

    function changePage(newPage) {
        if (activePage === newPage) return;

        console.log("Otworzono " + newPage);

        activePage = newPage;
        pendingPage = newPage;
        fadeOut.restart();
    }

    // --- INTEGRACJA ASYSTENTA GŁOSOWEGO Z INTERFEJSEM QML ---
    Connections {
        target: App

        // Reakcja na komendy głosowe start/stop (Twoje zmiany)
        function onPageChangeRequested(page) {
            window.changePage(page)
        }

        // Zabezpieczenie dla klasycznej nawigacji
        function onNavRequested(page) {
            window.changePage(page)
        }
    }

    ListModel {
        id: navModel
        ListElement { icon: "🏠"; source: "MainMenu.qml"; name: "Home" }
        ListElement { icon: "🏆"; source: "Statistics.qml"; name: "Records" }
        ListElement { icon: "💬"; source: "Ai.qml"; name: "AI" }
        ListElement { icon: "⚙️"; source: "Settings.qml"; name: "Settings" }
    }

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

        // Pasek boczny (Sidebar)
        Rectangle {
            Layout.fillHeight: true
            width: 70
            color: theme.sidebar

            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 20
                anchors.bottomMargin: 20
                spacing: 15

                Repeater {
                    model: navModel
                    delegate: Item {
                        Layout.alignment: Qt.AlignHCenter
                        width: 50
                        height: 50

                        Rectangle {
                            anchors.fill: parent
                            color: (activePage === model.source)
                                ? theme.blurple
                                : (parent.hovered ? "#35353d" : "transparent")
                            radius: 15
                            Behavior on color {
                                ColorAnimation {
                                    duration: 200
                                }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: model.icon
                            font.pixelSize: 20
                            color: "white"
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: changePage(model.source)
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        // Główny kontener na ekrany (Loader)
        Loader {
            id: loader
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 20
            source: "MainMenu.qml"
            opacity: 1

            onLoaded: fadeIn.restart()

            NumberAnimation {
                id: fadeIn
                target: loader
                property: "opacity"
                from: 0
                to: 1
                duration: 250
                easing.type: Easing.OutCubic
            }

            NumberAnimation {
                id: fadeOut
                target: loader
                property: "opacity"
                to: 0
                duration: 200
                easing.type: Easing.InCubic

                onFinished: loader.source = pendingPage
            }
        }
    }
}