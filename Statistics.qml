import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: statsPage
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Text {
            text: "Historia Treningów"
            color: "white"
            font.family: theme.fontTitle
            font.pixelSize: 32
        }

        // Górna karta podsumowania
        Rectangle {
            Layout.fillWidth: true
            height: 100
            color: theme.darkBtn
            radius: 15
            
            RowLayout {
                anchors.centerIn: parent
                spacing: 50
                
                Column {
                    Text { text: "OSTATNIA SESJA"; color: "#888fb1"; font.pixelSize: 11; anchors.horizontalCenter: parent.horizontalCenter }
                    Text { text: "88%"; color: theme.blurple; font.pixelSize: 32; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                }
                Rectangle { width: 1; height: 40; color: "#35353d" }
                Column {
                    Text { text: "CZAS"; color: "#888fb1"; font.pixelSize: 11; anchors.horizontalCenter: parent.horizontalCenter }
                    Text { text: "15:20"; color: "white"; font.pixelSize: 32; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                }
            }
        }

        Text {
            text: "Poprzednie sesje"
            color: "white"
            font.pixelSize: 20
            font.bold: true
        }

        ListView {
            id: sessionList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 12 // Odstęp między kafelkami
            
            model: ListModel {
                ListElement { 
                    date: "12.05.2024"
                    avgScore: "92%"
                    poses: "Wojownik I (95%), Drzewo (88%), Kobra (93%)"
                }
                ListElement { 
                    date: "10.05.2024"
                    avgScore: "78%"
                    poses: "Pies z głową w dół (70%), Deska (86%)"
                }
                ListElement { 
                    date: "08.05.2024"
                    avgScore: "85%"
                    poses: "Wojownik II (80%), Drzewo (90%)"
                }
            }
            
            delegate: Rectangle {
                width: sessionList.width
                // Używamy implicitHeight z ColumnLayout, aby prostokąt urósł razem z tekstem
                height: mainColumn.implicitHeight + 30 
                color: "#1c1c21"
                border.color: "#35353d"
                radius: 12

                ColumnLayout {
                    id: mainColumn
                    anchors.fill: parent
                    anchors.margins: 15
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "📅  Sesja: " + model.date
                            color: "white"
                            font.bold: true
                            font.pixelSize: 16
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: model.avgScore
                            color: theme.blurple
                            font.bold: true
                            font.pixelSize: 18
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: "#2b2d31"
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text {
                            text: "WYKONANE POZY:"
                            color: "#5865F2"
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 1
                        }
                        Text {
                            text: model.poses
                            color: "#ccc"
                            font.pixelSize: 14
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }
    }
}
