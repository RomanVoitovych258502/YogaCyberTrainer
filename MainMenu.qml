import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    Rectangle {
        anchors.fill: parent
        color: "red"
        radius: 20

        Text {
            anchors.centerIn: parent
            text: "Menu Główne"
            color: "white"
            font.pixelSize: 24
        }
    }
}