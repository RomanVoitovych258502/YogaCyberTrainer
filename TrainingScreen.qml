import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property bool showSideView: false
    property bool cam2FullyHidden: false
    property bool camerasSwapped: false

    property string rawCam1Src: ""
    property string rawCam2Src: ""

    property string mainSrc: camerasSwapped ? rawCam2Src : rawCam1Src
    property string secondarySrc: camerasSwapped ? rawCam1Src : rawCam2Src

    property string mainLabel: camerasSwapped ? (App.i18n["train.cam2"] || "KAMERA 2") : (App.i18n["train.cam1"] || "KAMERA 1")
    property string secondaryLabel: camerasSwapped ? (App.i18n["train.cam1"] || "KAMERA 1") : (App.i18n["train.cam2"] || "KAMERA 2")

    Component.onCompleted: TrainingCtrl.startTraining()
    Component.onDestruction: TrainingCtrl.stopTraining()

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

        // 1. Podgląd głównej kamery
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

        // 2. Kontener na natywne elementy UI (ukrywany podczas SUPER!)
        Item {
            anchors.fill: parent
            visible: !TrainingCtrl.isSuper
            z: 1 // Gwarantujemy widoczność UI nad kamerą

            // Pływające okienko instrukcji (wzór asany) - KLIKALNE
            Rectangle {
                id: instructionBox
                width: 150
                height: 150
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.margins: 20
                color: "#1c1c21"

                border.color: boxMouseArea.containsMouse ? "#6D7AFF" : theme.blurple
                border.width: 2
                radius: 12
                clip: true

                property string imageSource: {
                    switch(TrainingCtrl.currentLetter) {
                        case "pies_z_glowa_w_dol": return "pies_z_glowa_w_dol.jpg"
                        case "pozycja_dziecka":    return "pozycja_dziecka.jpg"
                        case "pozycja_drzewa":     return "pozycja_drzewa.jpg"
                        case "pozycja_gory":       return "pozycja_gory.jpg"
                        default: return ""
                    }
                }

                Image {
                    anchors.fill: parent
                    anchors.margins: 8
                    anchors.bottomMargin: 30
                    source: parent.imageSource
                    fillMode: Image.PreserveAspectFit
                    visible: parent.imageSource !== ""
                }

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 26
                    color: boxMouseArea.containsMouse ? "#6D7AFF" : theme.blurple

                    Text {
                        anchors.centerIn: parent
                        text: boxMouseArea.containsMouse ? (App.i18n["train.click_to_change"] || "KLIKNIJ, ABY ZMIENIĆ") : (App.i18n["train.pattern"] || "CEL") + ": " + TrainingCtrl.currentLetter.replace(/_/g, " ").toUpperCase()
                        color: "white"
                        font.pixelSize: 9
                        font.bold: true
                    }
                }

                MouseArea {
                    id: boxMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: TrainingCtrl.nextPose()
                }
            }

            // Eleganckie informacje o poprawie pozycji (Hinty)
            Column {
                anchors.left: instructionBox.right
                anchors.top: instructionBox.top
                anchors.leftMargin: 20
                spacing: 12

                Repeater {
                    model: TrainingCtrl.poseHints
                    delegate: Rectangle {
                        width: hintLayout.implicitWidth + 30
                        height: 40
                        color: "#E61c1c21"
                        radius: 8
                        border.color: "#FF4747"
                        border.width: 1

                        RowLayout {
                            id: hintLayout
                            anchors.centerIn: parent
                            spacing: 8
                            Text {
                                text: "⚠️"
                                font.pixelSize: 16
                            }
                            Text {
                                text: modelData
                                color: "white"
                                font.pixelSize: 14
                                font.bold: true
                                font.family: theme.fontMain
                            }
                        }
                    }
                }
            }

            // Animowany pasek postępu na dole
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottomMargin: 30
                width: parent.width * 0.7
                height: 30
                radius: 15
                color: theme.darkBtn
                border.color: "#35353d"
                border.width: 2
                clip: true

                Rectangle {
                    width: parent.width * TrainingCtrl.holdProgress
                    height: parent.height
                    color: TrainingCtrl.holdProgress >= 1.0 ? "#50FF50" : theme.blurple
                    radius: 15

                    Behavior on width {
                        NumberAnimation { duration: 100 }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    text: App.i18n["train.hold_pose"] || "Trzymaj pozycję!"
                    color: "white"
                    font.bold: true
                    font.pixelSize: 14
                    style: Text.Outline
                    styleColor: "black"
                }
            }

            // Przyciski sterujące w prawym górnym rogu
            Row {
                id: topRightControls
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 20
                spacing: 10

                Button {
                    id: swapButton
                    width: 54
                    height: 54
                    visible: TrainingCtrl.dualCameraEnabled
                    background: Rectangle {
                        color: parent.hovered ? "#6D7AFF" : theme.blurple
                        radius: width / 2
                        border.color: "#ffffff"
                        border.width: 2
                        Behavior on color { ColorAnimation { duration: 150 } }
                    }
                    contentItem: Text {
                        text: "⇄"
                        color: "white"
                        font.pixelSize: 24
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: root.camerasSwapped = !root.camerasSwapped
                }

                Button {
                    id: rotateButton
                    width: 54
                    height: 54
                    background: Rectangle {
                        color: parent.hovered ? "#6D7AFF" : theme.blurple
                        radius: width / 2
                        border.color: "#ffffff"
                        border.width: 2
                        Behavior on color { ColorAnimation { duration: 150 } }
                    }
                    contentItem: Text {
                        text: "🔄"
                        color: "white"
                        font.pixelSize: 24
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: TrainingCtrl.rotateCamera(root.camerasSwapped ? 2 : 1)
                }
            }
        }

        // 3. Moduły widoku drugiej kamery (side view / minimapka)
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
            z: 0

            visible: root.showSideView && TrainingCtrl.dualCameraEnabled
            opacity: visible ? 1.0 : 0.0
            Behavior on opacity { NumberAnimation { duration: 150 } }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.showSideView = false
            }

            Image {
                anchors.fill: parent
                fillMode: Image.PreserveAspectFit
                source: root.secondarySrc
            }

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.margins: 8
                width: sideLabel.implicitWidth + 16
                height: 22
                radius: 6
                color: "#BB1c1c21"
                z: 2

                Text {
                    id: sideLabel
                    text: root.secondaryLabel
                    color: theme.blurple
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            Row {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 8
                spacing: 6
                z: 2

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

        Rectangle {
            id: cam2Thumb
            width: 70
            height: 70
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 84
            anchors.rightMargin: 20
            radius: 10
            color: "#000"
            border.color: theme.blurple
            border.width: 2
            clip: true
            z: 2

            visible: TrainingCtrl.dualCameraEnabled && !root.showSideView && !root.cam2FullyHidden && !TrainingCtrl.isSuper
            opacity: visible ? 1.0 : 0.0
            Behavior on opacity { NumberAnimation { duration: 150 } }

            Image {
                anchors.fill: parent
                anchors.margins: 2
                fillMode: Image.PreserveAspectCrop
                source: root.secondarySrc
            }

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

        Rectangle {
            id: restoreTab
            width: 34
            height: 34
            radius: 10
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 84
            anchors.rightMargin: 20
            color: "#BB1c1c21"
            border.color: theme.blurple
            border.width: 2
            z: 2

            visible: TrainingCtrl.dualCameraEnabled && root.cam2FullyHidden && !TrainingCtrl.isSuper
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

        // 4. Ekran sukcesu - przyciemnia tło i wyskakuje wielkie "SUPER!" (widoczne ponad wszystkim)
        Rectangle {
            anchors.fill: parent
            anchors.margins: 10
            color: "#A6000000"
            visible: TrainingCtrl.isSuper
            radius: 10
            z: 10

            Text {
                anchors.centerIn: parent
                text: "SUPER!"
                color: "#50FF50"
                font.pixelSize: 110
                font.bold: true
                font.family: theme.fontTitle
                style: Text.Outline
                styleColor: "#005500"

                scale: TrainingCtrl.isSuper ? 1.0 : 0.5
                Behavior on scale {
                    NumberAnimation { duration: 300; easing.type: Easing.OutBack }
                }
            }
        }
    }
}