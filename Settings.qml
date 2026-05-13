import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: settingsPage
    anchors.fill: parent
    clip: true
    padding: 20

    ColumnLayout {
        width: settingsPage.availableWidth
        spacing: 25

        Text {
            text: "Ustawienia"
            color: "white"
            font.pixelSize: 32
            font.family: theme.fontTitle
        }

        SettingsGroup {
            title: "KAMERKA"
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 15

                StyledComboBox {
                    Layout.fillWidth: true
                    model: ["Kamerka #1", "Kamerka #2", "Kamerka #3"]
                }

                Rectangle {
                    Layout.preferredWidth: parent.width / 2
                    Layout.alignment: Qt.AlignHCenter
                    implicitHeight: width * (3/4)
                    color: "#000"
                    radius: 8
                    border.color: "#35353d"
                    clip: true

                    Text {
                        anchors.centerIn: parent
                        text: "Podgląd kamery..."
                        color: "#555"
                    }
                }
            }
        }

        SettingsGroup {
            title: "DŹWIĘK"
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 15

                Label { text: "Urządzenie wyjściowe"; color: "#ccc"; font.pixelSize: 12 }
                RowLayout {
                    spacing: 10
                    StyledComboBox {
                        Layout.fillWidth: true
                        model: ["Głośniki", "Słuchawki"]
                    }
                    StyledButton {
                        text: "Test"
                        onClicked: console.log("Test dźwięku...")
                    }
                }

                Label { text: "Urządzenie wejściowe"; color: "#ccc"; font.pixelSize: 12 }
                StyledComboBox {
                    Layout.fillWidth: true
                    model: ["Mikrofon #1", "Mikrofon #2", "Mikrofon #3"]
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Label { text: "Poziom wejścia"; color: "#888fb1"; font.pixelSize: 10 }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 8
                        color: "#2b2d31"
                        radius: 4
                        Rectangle {
                            width: parent.width * 0.45
                            height: parent.height
                            color: theme.blurple
                            radius: 4
                        }
                    }
                }
            }
        }

        SettingsGroup {
            title: "JĘZYK"
            StyledComboBox {
                Layout.fillWidth: true
                model: ["🇵🇱 Polski", "🇺🇸 English"]
                onActivated: (index) => console.log("Wybrano język: " + textAt(index))
            }
        }
    }

    // --- KOMPONENTY STYLIZOWANE ---

    component StyledComboBox : ComboBox {
        id: control

        indicator: Canvas {
            id: canvas
            x: control.width - width - 15
            y: control.topPadding + (control.availableHeight - height) / 2
            width: 10
            height: 6
            contextType: "2d"
            onPaint: {
                var context = getContext("2d");
                context.reset();
                context.moveTo(0, 0);
                context.lineTo(width, 0);
                context.lineTo(width / 2, height);
                context.closePath();
                context.fillStyle = "white";
                context.fill();
            }
        }

        delegate: ItemDelegate {
            width: control.width
            padding: 10
            contentItem: Text {
                text: modelData
                color: "white"
                font: control.font
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                // ZMIANA: Podświetlenie elementu listy na blurple
                color: control.highlightedIndex === index ? theme.blurple : "transparent"
                radius: 4
            }
        }

        popup: Popup {
            y: control.height + 5
            width: control.width
            implicitHeight: contentItem.implicitHeight + 10
            padding: 5
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
            background: Rectangle {
                color: "#2b2d31"
                border.color: "#45454d"
                radius: 8
            }
        }

        contentItem: Text {
            leftPadding: 10
            rightPadding: 40
            text: control.displayText
            font: control.font
            color: "white"
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            implicitHeight: 40
            color: "#2b2d31"
            // ZMIANA: Obramowanie zawsze blurple gdy aktywne lub hovered (opcjonalnie)
            border.color: (control.visualFocus || control.hovered) ? theme.blurple : "#35353d"
            radius: 8
        }
    }

    component StyledButton : Button {
        id: btnControl
        contentItem: Text {
            text: btnControl.text
            font: btnControl.font
            color: "white"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            implicitWidth: 80
            implicitHeight: 40
            // ZMIANA: Przycisk zmienia kolor na blurple po najechaniu lub naciśnięciu
            color: btnControl.pressed ? "#4752C4" : (btnControl.hovered ? theme.blurple : "#35353d")
            radius: 8
            border.color: "#45454d"
        }
    }

    component SettingsGroup : Rectangle {
        property alias title: groupTitle.text
        default property alias content: innerLayout.data
        Layout.fillWidth: true
        implicitHeight: mainCol.implicitHeight + 30
        color: "#1c1c21"
        border.color: "#35353d"
        radius: 12
        ColumnLayout {
            id: mainCol
            anchors.fill: parent
            anchors.margins: 15
            Text {
                id: groupTitle
                color: "#5865F2"
                font.pixelSize: 10
                font.bold: true
                font.letterSpacing: 1
            }
            ColumnLayout {
                id: innerLayout
                Layout.fillWidth: true
            }
        }
    }
}