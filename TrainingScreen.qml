import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    // Czy widok boczny (druga kamera) jest aktualnie rozwinięty w panel
    property bool showSideView: false
    // Czy druga kamera jest całkowicie schowana (brak nawet miniaturki)
    property bool cam2FullyHidden: false
    // Czy kamery są zamienione miejscami (główny widok <-> podgląd)
    property bool camerasSwapped: false

    // Surowe źródła obrazu z obu kamer
    property string rawCam1Src: ""
    property string rawCam2Src: ""

    // Źródła po uwzględnieniu zamiany miejsc
    property string mainSrc: camerasSwapped ? rawCam2Src : rawCam1Src
    property string secondarySrc: camerasSwapped ? rawCam1Src : rawCam2Src

    // Etykiety odpowiadające bieżącemu przypisaniu kamer
    property string mainLabel: camerasSwapped ? "KAMERA 2" : "KAMERA 1"
    property string secondaryLabel: camerasSwapped ? "KAMERA 1" : "KAMERA 2"

    Component.onCompleted: TrainingCtrl.startTraining()
    Component.onDestruction: TrainingCtrl.stopTraining()

    // Gdy druga kamera zostanie wyłączona w ustawieniach w trakcie treningu,
    // zwijamy widok boczny i miniaturkę automatycznie.
    onVisibleChanged: if (!TrainingCtrl.dualCameraEnabled) {
        showSideView = false
        cam2FullyHidden = false
    }

    Connections {
        target: TrainingCtrl
        function onFrameUpdated() {
            root.rawCam1Src = "image://video/frame?id=" + Math.random()
            if (TrainingCtrl.dualCameraEnabled) {
                root.rawCam2Src = "image://video2/frame?id=" + Math.random()
            } else {
                if (root.showSideView) root.showSideView = false
                if (root.cam2FullyHidden) root.cam2FullyHidden = false
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#2b2d31"
        radius: 20
        clip: true

        // -------------------------------------------------------------
        // Główny widok przetwarzanego strumienia wideo
        // Zwęża się, gdy rozwinięty jest panel boczny drugiej kamery
        // -------------------------------------------------------------
        Image {
            id: videoImage
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.margins: 10
            anchors.rightMargin: 10
            width: (root.showSideView && TrainingCtrl.dualCameraEnabled)
                   ? parent.width * 3 / 4 - 15
                   : parent.width - 20
            fillMode: Image.PreserveAspectFit
            source: root.mainSrc

            Behavior on width {
                NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
            }
        }

        // Etykieta widoku głównego — widoczna tylko po zamianie kamer,
        // żeby było jasne co aktualnie wyświetla główny podgląd
        Rectangle {
            visible: root.camerasSwapped && TrainingCtrl.dualCameraEnabled
            anchors.bottom: videoImage.bottom
            anchors.left: videoImage.left
            anchors.margins: 8
            width: mainLabelText.implicitWidth + 16
            height: 22
            radius: 6
            color: "#BB1c1c21"

            Text {
                id: mainLabelText
                anchors.centerIn: parent
                text: root.mainLabel
                color: theme.blurple
                font.pixelSize: 10
                font.bold: true
            }
        }

        // -------------------------------------------------------------
        // Rozwinięty panel boczny (druga kamera) — 1/4 szerokości po prawej
        // -------------------------------------------------------------
        Rectangle {
            id: sidePanel
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            anchors.margins: 10
            width: parent.width / 4
            radius: 12
            color: "#000"
            clip: true
            border.color: theme.blurple
            border.width: 2

            visible: root.showSideView && TrainingCtrl.dualCameraEnabled
            opacity: visible ? 1.0 : 0.0
            Behavior on opacity { NumberAnimation { duration: 150 } }

            Image {
                anchors.fill: parent
                fillMode: Image.PreserveAspectFit
                source: root.secondarySrc
            }

            // Etykieta
            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.margins: 8
                width: sideLabel.implicitWidth + 16
                height: 22
                radius: 6
                color: "#BB1c1c21"

                Text {
                    id: sideLabel
                    anchors.centerIn: parent
                    text: root.secondaryLabel
                    color: theme.blurple
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            // Przyciski: zwijanie do miniaturki (zamiana kamer usunięta stąd)
            Row {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 8
                spacing: 6

                // Zwiń do miniaturki
                Rectangle {
                    width: 26; height: 26; radius: 13
                    color: "#BB1c1c21"
                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: "white"
                        font.pixelSize: 13
                        font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.showSideView = false
                    }
                }
            }
        }

        // -------------------------------------------------------------
        // Miniaturka podglądu drugiej kamery — widoczna gdy panel boczny
        // jest zwinięty, a druga kamera nie jest całkowicie schowana.
        // Kliknięcie środka rozwija panel boczny.
        // -------------------------------------------------------------
        Rectangle {
            id: cam2Thumb
            width: 70
            height: 70
            anchors.top: topRightControls.bottom
            anchors.right: parent.right
            anchors.topMargin: 12
            anchors.rightMargin: 20
            radius: 10
            color: "#000"
            border.color: theme.blurple
            border.width: 2
            clip: true

            visible: TrainingCtrl.dualCameraEnabled && !root.showSideView && !root.cam2FullyHidden
            opacity: visible ? 1.0 : 0.0
            Behavior on opacity { NumberAnimation { duration: 150 } }

            Image {
                anchors.fill: parent
                anchors.margins: 2
                fillMode: Image.PreserveAspectCrop
                source: root.secondarySrc
            }

            // Delikatne przyciemnienie + ikona "rozwiń" (klik = otwórz panel)
            Rectangle {
                anchors.fill: parent
                color: "#00000055"

                Text {
                    anchors.centerIn: parent
                    text: "⤢"
                    color: "white"
                    font.pixelSize: 22
                    font.bold: true
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.showSideView = true
                }
            }

            // Mały przycisk całkowitego chowania (prawy górny róg miniaturki)
            Rectangle {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 2
                width: 20; height: 20; radius: 10
                color: "#CC1c1c21"
                z: 2

                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    color: "white"
                    font.pixelSize: 11
                    font.bold: true
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.cam2FullyHidden = true
                }
            }
        }

        // -------------------------------------------------------------
        // Mała "zakładka" przywracająca widok drugiej kamery, gdy jest
        // całkowicie schowany.
        // -------------------------------------------------------------
        Rectangle {
            id: restoreTab
            width: 34
            height: 34
            radius: 10
            anchors.top: topRightControls.bottom
            anchors.right: parent.right
            anchors.topMargin: 12
            anchors.rightMargin: 20
            color: "#BB1c1c21"
            border.color: theme.blurple
            border.width: 2

            visible: TrainingCtrl.dualCameraEnabled && root.cam2FullyHidden
            opacity: visible ? 1.0 : 0.0
            Behavior on opacity { NumberAnimation { duration: 150 } }

            Text {
                anchors.centerIn: parent
                text: "📹"
                font.pixelSize: 16
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.cam2FullyHidden = false
            }
        }

        // --- Pływające okienko instrukcji (wzór graficzny asany) ---

        Rectangle {
            id: instructionBox
            width: 150
            height: 125
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.margins: 20
            color: "#1c1c21"

            border.color: "#45454d"
            border.width: 2
            radius: 12
            clip: true

            // Okienko pojawia się tylko wtedy, gdy Python wykryje zbliżenie do danej asany
            visible: imageSource !== ""

            // Przypisanie tekstu z Pythona na bezpieczne, bezproblemowe nazwy plików JPG
            property string imageSource: {
                switch(TrainingCtrl.closestPose) {
                    case "Pies z glowa w dol": return "pies_z_glowa_w_dol.jpg"
                    case "Pozycja dziecka":   return "pozycja_dziecka.jpg"
                    case "Pozycja drzewa":    return "pozycja_drzewa.jpg"
                    case "Pozycja gory":      return "pozycja_gory.jpg"
                    default: return ""
                }
            }

            // Komponent ładujący wybrany obrazek pomocniczy
            Image {
                anchors.fill: parent
                anchors.margins: 8
                anchors.bottomMargin: 22
                source: parent.imageSource
                fillMode: Image.PreserveAspectFit
            }

            // Pasek informacyjny na dole okienka
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 18
                color: "#2b2d31"

                Text {
                    anchors.centerIn: parent
                    text: "WZÓR POZYCJI"
                    color: "#888fb1"
                    font.pixelSize: 9
                    font.bold: true
                }
            }
        }

        // -------------------------------------------------------------
        // Główne przyciski sterujące: Zamiana kamer (widoczna w Dual) oraz Obrót
        // -------------------------------------------------------------
        Row {
            id: topRightControls
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 20
            spacing: 10

            Button {
                id: swapButton
                text: "⇄"
                visible: TrainingCtrl.dualCameraEnabled
                onClicked: root.camerasSwapped = !root.camerasSwapped
            }

            Button {
                id: rotateButton
                text: "🔄"
                // Przekazujemy ID kamery: 2 jeśli zamieniono miejscami, 1 jeśli domyślnie
                onClicked: TrainingCtrl.rotateCamera(root.camerasSwapped ? 2 : 1)
            }
        }

        // Dolny tekst informacyjny ze statusem - PODNIESIONY NAD PASEK POSTĘPU
        Text {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: videoImage.horizontalCenter
            anchors.bottomMargin: 70 // Zwiększono margines, aby tekst był powyżej paska
            text: TrainingCtrl.currentLetter
            color: TrainingCtrl.currentLetter === "?" ? "#FF5555" : "#00FFD1"
            font.pixelSize: 40
            font.bold: true
        }
    }
}