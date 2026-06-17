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
            text: App.i18n["settings.title"] || "Ustawienia"
            color: "white"
            font.pixelSize: 32
            font.family: theme.fontTitle
        }

        SettingsGroup {
            title: App.i18n["settings.cam.title"] || "KAMERKA"
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 15

                // --- Kamera 1 ---
                Label { text: App.i18n["settings.cam.main"] || "Kamera główna (kamera 1)"; color: "#ccc"; font.pixelSize: 12 }
                StyledComboBox {
                    id: cameraComboBox
                    Layout.fillWidth: true
                    model: TrainingCtrl.cameraNames
                    onActivated: (index) => TrainingCtrl.setCameraIndex(index)
                }

                // --- Kamera 2 ---
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Label {
                        text: App.i18n["settings.cam.second"] || "Druga kamera"
                        color: "#ccc"
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }

                    Rectangle {
                        id: toggleSwitch
                        width: 48
                        height: 26
                        radius: 13
                        color: dualSwitch.checked ? theme.blurple : "#35353d"
                        border.color: dualSwitch.checked ? theme.blurple : "#45454d"

                        Behavior on color { ColorAnimation { duration: 150 } }

                        Rectangle {
                            id: toggleKnob
                            width: 20
                            height: 20
                            radius: 10
                            color: "white"
                            anchors.verticalCenter: parent.verticalCenter
                            x: dualSwitch.checked ? parent.width - width - 3 : 3
                            Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                dualSwitch.checked = !dualSwitch.checked
                                if (dualSwitch.checked) {
                                    var idx = (cameraComboBox.currentIndex === 0 && TrainingCtrl.cameraNames.length > 1) ? 1 : 0
                                    camera2ComboBox.currentIndex = idx
                                    TrainingCtrl.setCameraIndex2(idx)
                                } else {
                                    TrainingCtrl.setCameraIndex2(-1)
                                }
                            }
                        }

                        CheckBox {
                            id: dualSwitch
                            visible: false
                            checked: TrainingCtrl.dualCameraEnabled
                        }
                    }
                }

                StyledComboBox {
                    id: camera2ComboBox
                    Layout.fillWidth: true
                    model: TrainingCtrl.cameraNames
                    visible: dualSwitch.checked
                    enabled: dualSwitch.checked
                    opacity: dualSwitch.checked ? 1.0 : 0.0
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                    onActivated: (index) => TrainingCtrl.setCameraIndex2(index)
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: width * (3 / 4)
                        color: "#000"
                        radius: 8
                        border.color: "#35353d"
                        clip: true

                        Image {
                            id: previewImage
                            anchors.fill: parent
                            fillMode: Image.PreserveAspectFit
                            source: "image://video/preview"
                            cache: false
                            visible: TrainingCtrl.isRunning
                        }

                        Text {
                            anchors.centerIn: parent
                            text: App.i18n["settings.cam.cam1_off"] || "Kamera 1\nPodgląd wyłączony"
                            horizontalAlignment: Text.AlignHCenter
                            color: "#555"
                            visible: !TrainingCtrl.isRunning
                            font.pixelSize: 11
                        }

                        Text {
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottomMargin: 4
                            text: App.i18n["train.cam1"] || "KAMERA 1"
                            color: theme.blurple
                            font.pixelSize: 9
                            font.bold: true
                            visible: dualSwitch.checked && TrainingCtrl.isRunning
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: width * (3 / 4)
                        color: "#000"
                        radius: 8
                        border.color: dualSwitch.checked ? theme.blurple : "#35353d"
                        clip: true
                        visible: dualSwitch.checked

                        Image {
                            id: previewImage2
                            anchors.fill: parent
                            fillMode: Image.PreserveAspectFit
                            source: "image://video2/preview"
                            cache: false
                            visible: TrainingCtrl.isRunning && dualSwitch.checked
                        }

                        Text {
                            anchors.centerIn: parent
                            text: App.i18n["settings.cam.cam2_off"] || "Kamera 2\nPodgląd wyłączony"
                            horizontalAlignment: Text.AlignHCenter
                            color: "#555"
                            visible: !TrainingCtrl.isRunning
                            font.pixelSize: 11
                        }

                        Text {
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottomMargin: 4
                            text: App.i18n["train.cam2"] || "KAMERA 2"
                            color: theme.blurple
                            font.pixelSize: 9
                            font.bold: true
                            visible: dualSwitch.checked && TrainingCtrl.isRunning
                        }
                    }
                }

                Connections {
                    target: TrainingCtrl
                    function onFrameUpdated() {
                        if (TrainingCtrl.isRunning) {
                            previewImage.source = "image://video/preview?" + Date.now()
                            if (dualSwitch.checked) {
                                previewImage2.source = "image://video2/preview?" + Date.now()
                            }
                        }
                    }
                }

                StyledButton {
                    Layout.alignment: Qt.AlignHCenter
                    text: TrainingCtrl.isRunning ? (App.i18n["settings.cam.preview_off"] || "Wyłącz podgląd") : (App.i18n["settings.cam.preview_on"] || "Włącz podgląd")
                    onClicked: {
                        if (TrainingCtrl.isRunning) {
                            TrainingCtrl.stopTraining();
                        } else {
                            TrainingCtrl.startTraining();
                        }
                    }
                }
            }
        }

        SettingsGroup {
            title: App.i18n["settings.audio.title"] || "DŹWIĘK"
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 15

                Label { text: App.i18n["settings.audio.output"] || "Urządzenie wyjściowe"; color: "#ccc"; font.pixelSize: 12 }
                RowLayout {
                    spacing: 10
                    StyledComboBox {
                        Layout.fillWidth: true
                        model: App.audioOutputs
                        onActivated: (index) => App.setOutputDevice(index)
                    }
                    StyledButton {
                        text: App.i18n["settings.audio.test"] || "Test"
                        onClicked: App.testAudio()
                    }
                }

                Label { text: App.i18n["settings.audio.input"] || "Urządzenie wejściowe"; color: "#ccc"; font.pixelSize: 12 }
                StyledComboBox {
                    Layout.fillWidth: true
                    model: App.audioInputs
                    onActivated: (index) => App.setInputDevice(index)
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Label { text: App.i18n["settings.audio.level"] || "Poziom wejścia"; color: "#888fb1"; font.pixelSize: 10 }
                    Rectangle {
                        Layout.fillWidth: true
                        height: 8
                        color: "#2b2d31"
                        radius: 4
                        Rectangle {
                            width: parent.width * App.audioLevel
                            height: parent.height
                            color: theme.blurple
                            radius: 4
                            Behavior on width { NumberAnimation { duration: 50 } }
                        }
                    }
                }
            }
        }

        SettingsGroup {
            title: App.i18n["settings.lang.title"] || "JĘZYK"
            StyledComboBox {
                Layout.fillWidth: true
                model: ["🇵🇱 Polski", "🇺🇸 English"]
                currentIndex: 0
                onActivated: (index) => {
                    App.setLanguage(index === 0 ? "pl" : "en")
                }
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