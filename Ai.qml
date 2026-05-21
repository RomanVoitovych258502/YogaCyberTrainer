import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: aiHelpPage

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 15

        // 1. Nagłówek
        ColumnLayout {
            spacing: 5
            Text {
                text: "Asystent Pomocy"
                color: "white"
                font.family: theme.fontTitle 
                font.pixelSize: 32
            }
            Text {
                text: "Masz problem z aplikacją? Zadaj pytanie poniżej."
                color: "#888fb1"
                font.pixelSize: 14
            }
        }

        // 2. Obszar czatu (Lista wiadomości)
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1c1c21"
            radius: 15
            border.color: "#35353d"

            ListView {
                id: chatView
                anchors.fill: parent
                anchors.margins: 15
                spacing: 15
                clip: true
                model: chatModel
                
                // Automatyczne przewijanie na dół
                onCountChanged: chatView.positionViewAtEnd()

                delegate: RowLayout {
                    width: chatView.width - 20
                    spacing: 0

                    // Spychacz dla wiadomości użytkownika (pcha dymek do prawej)
                    Item { 
                        Layout.fillWidth: true
                        visible: model.isUser 
                    }

                    // Dymek wiadomości
                    Rectangle {
                        // Obliczanie szerokości: dopasuj do tekstu, ale max 75% szerokości okna
                        Layout.preferredWidth: Math.min(msgText.implicitWidth + 24, chatView.width * 0.75)
                        Layout.preferredHeight: msgText.implicitHeight + 20
                        radius: 12
                        color: model.isUser ? theme.blurple : "#2b2d31"

                        Text {
                            id: msgText
                            text: model.text
                            color: "white"
                            font.pixelSize: 14
                            wrapMode: Text.WordWrap
                            width: parent.width - 24
                            anchors.centerIn: parent
                        }
                    }

                    // Spychacz dla wiadomości AI (pcha dymek do lewej)
                    Item { 
                        Layout.fillWidth: true
                        visible: !model.isUser 
                    }
                }
            }
        }

        // 3. Pole wprowadzania tekstu (Dolny pasek)
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 50 
            Layout.maximumHeight: 50   
            spacing: 10

            TextField {
                id: inputField
                Layout.fillWidth: true
                Layout.fillHeight: true
                placeholderText: "Wpisz swoje pytanie (np. 'kamera nie działa')..."
                color: "white"
                placeholderTextColor: "#888fb1"
                font.pixelSize: 14
                verticalAlignment: TextInput.AlignVCenter
                leftPadding: 15
                
                background: Rectangle {
                    color: "#2b2d31"
                    radius: 10
                    border.color: inputField.activeFocus ? theme.blurple : "#35353d"
                }

                onAccepted: sendMessage() 
            }

            Button {
                id: sendBtn
                text: "Wyślij"
                Layout.fillHeight: true
                Layout.preferredWidth: 100
                
                contentItem: Text {
                    text: sendBtn.text
                    color: "white"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                
                background: Rectangle {
                    color: sendBtn.hovered ? "#6773f5" : theme.blurple
                    radius: 10
                }

                onClicked: sendMessage()
            }
        }
    }

    // --- LOGIKA I DANE ---

    ListModel {
        id: chatModel
        ListElement {
            isUser: false
            text: "Cześć! Jestem Twoim asystentem. W czym mogę Ci dzisiaj pomóc?"
        }
    }

    function sendMessage() {
        var msg = inputField.text.trim();
        if (msg === "") return;

        chatModel.append({ "isUser": true, "text": msg });
        inputField.text = "";
        generateResponse(msg);
    }

    function generateResponse(userText) {
        var response = "Przepraszam, nie rozumiem pytania. Spróbuj zapytać o 'kamerę', 'trening' lub 'statystyki'.";
        var lowerText = userText.toLowerCase();

        if (lowerText.indexOf("kamer") !== -1) {
            response = "Jeśli kamera nie działa:\n1. Sprawdź, czy inna aplikacja jej nie blokuje.\n2. Upewnij się, że masz przyznane uprawnienia w systemie.\n3. Zrestartuj aplikację.";
        } else if (lowerText.indexOf("trening") !== -1 || lowerText.indexOf("ćwicz") !== -1) {
            response = "Aby zacząć, przejdź do sekcji Home (ikona domku) i wybierz dostępny program treningowy.";
        } else if (lowerText.indexOf("statystyk") !== -1 || lowerText.indexOf("rekord") !== -1) {
            response = "Twoje wyniki są zapisywane automatycznie w zakładce Records (ikona pucharu).";
        }

        aiResponseTimer.responseText = response;
        aiResponseTimer.start();
    }

    Timer {
        id: aiResponseTimer
        interval: 700
        repeat: false
        property string responseText: ""
        onTriggered: chatModel.append({ "isUser": false, "text": responseText })
    }
}
