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
        clip: true

        // 1. Podgląd z kamery
        Image {
            id: videoImage
            anchors.fill: parent
            anchors.margins: 10
            fillMode: Image.PreserveAspectFit
        }

        // 2. Kontener na interfejs treningowy (ukrywany podczas SUPER!)
        Item {
            anchors.fill: parent
            visible: !TrainingCtrl.isSuper

            // Pływające okienko instrukcji (wzór asany) - KLIKALNE
            Rectangle {
                id: instructionBox
                width: 150
                height: 150
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.margins: 20
                color: "#1c1c21"

                // Efekt podświetlenia po najechaniu myszką
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
                        text: boxMouseArea.containsMouse ? "KLIKNIJ, ABY ZMIENIĆ" : "CEL: " + TrainingCtrl.currentLetter.replace(/_/g, " ").toUpperCase()
                        color: "white"
                        font.pixelSize: 9
                        font.bold: true
                    }
                }

                // Obszar detekcji kliknięcia myszy
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
                        color: "#E61c1c21" // Lekko przezroczyste tło
                        radius: 8
                        border.color: "#FF4747" // Czerwona ramka błędu
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
                    text: "Trzymaj pozycję!"
                    color: "white"
                    font.bold: true
                    font.pixelSize: 14
                    style: Text.Outline
                    styleColor: "black"
                }
            }

            // Przycisk zmiany orientacji kamery
            Button {
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 20
                width: 54
                height: 54

                background: Rectangle {
                    color: parent.hovered ? "#6D7AFF" : theme.blurple
                    radius: width / 2
                    border.color: "#ffffff"
                    border.width: 2

                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }
                }

                contentItem: Text {
                    text: "🔄"
                    color: "white"
                    font.pixelSize: 24
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: TrainingCtrl.rotateCamera()
            }
        }

        // 3. Ekran sukcesu - przyciemnia tło i wyskakuje wielkie "SUPER!"
        Rectangle {
            anchors.fill: parent
            anchors.margins: 10
            color: "#A6000000"
            visible: TrainingCtrl.isSuper
            radius: 10

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