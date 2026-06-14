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
        if (activePage === newPage)
            return;

        console.log("Otworzono " + newPage);

        activePage = newPage;
        pendingPage = newPage;
        fadeOut.restart();
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

    Connections {
        target: App

        function onPageChangeRequested(page) {
            console.log("PAGE CHANGE:", page)
            window.changePage(page)
        }
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
                spacing: 20

                Repeater {
                    model: navModel

                    delegate: Button {
                        text: model.icon
                        width: 64
                        height: 64
                        font.pixelSize: 28

                        background: Rectangle {
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

                        onClicked: changePage(model.source)
                    }
                }
            }
        }

        // ... wewnątrz ApplicationWindow ...

    function changePage(newPage) {
        if (loader.source.toString().endsWith(newPage)) return;

        console.log("Przełączam na: " + newPage);
        pendingPage = newPage; // Zapisz stronę do wczytania
        fadeOut.restart();     // Zacznij znikanie obecnej strony
    }

    Loader {
        id: loader
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.margins: 20
        source: "MainMenu.qml"
        opacity: 1

        // 1. Reakcja na załadowanie nowej strony
        onLoaded: {
            fadeIn.restart();

            // 2. Automatyczne uruchomienie treningu, gdy TrainingScreen się pojawi
            if (loader.source.toString().endsWith("TrainingScreen.qml")) {
                console.log("TrainingScreen załadowany - START");
                TrainingCtrl.startTraining();
            }
        }

        NumberAnimation {
            id: fadeIn
            target: loader
            property: "opacity"
            from: 0
            to: 1
            duration: 250
        }

        NumberAnimation {
            id: fadeOut
            target: loader
            property: "opacity"
            to: 0
            duration: 200

            // 3. Po zniknięciu starej strony, podmień źródło
            onFinished: {
                loader.source = pendingPage
            }
            }
        }
    }
}