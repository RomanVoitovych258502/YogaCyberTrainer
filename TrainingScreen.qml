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

        // Główny widok przetwarzanego strumienia wideo
        Image {
            id: videoImage
            anchors.fill: parent
            anchors.margins: 10
            fillMode: Image.PreserveAspectFit
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

        // Przycisk obracania kamery

        Button {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 20
            text: "🔄"
            onClicked: TrainingCtrl.rotateCamera()
        }

        // Dolny tekst informacyjny ze statusem - PODNIESIONY NAD PASEK POSTĘPU

        Text {
            anchors.bottom: parent.bottom
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottomMargin: 70 // Zwiększono margines, aby tekst był powyżej paska
            text: TrainingCtrl.currentLetter
            color: TrainingCtrl.currentLetter === "?" ? "#FF5555" : "#00FFD1"
            font.pixelSize: 40
            font.bold: true
        }
    }
}