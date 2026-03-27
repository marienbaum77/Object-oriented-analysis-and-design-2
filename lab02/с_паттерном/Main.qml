import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true; width: 1200; height: 800
    title: "mini obsidian"
    color: "#1e1e1e"

    property var activeItem: null

    RowLayout {
        anchors.fill: parent; spacing: 0
        Rectangle {
            id: sidebar; Layout.fillHeight: true; Layout.preferredWidth: 360
            color: "#252526"; z: 10
            ColumnLayout {
                anchors.fill: parent; anchors.topMargin: 12; anchors.bottomMargin: 12; spacing: 12
                RowLayout {
                    Layout.fillWidth: true; Layout.leftMargin: 12; Layout.rightMargin: 12; spacing: 8
                    Button {
                        text: "📁+ Root"; Layout.fillWidth: true
                        contentItem: Text { text: parent.text; color: "white"; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                        background: Rectangle { color: parent.pressed ? "#555" : (parent.hovered ? "#444" : "#383838"); radius: 4 }
                        onClicked: vault.addRootFolder("New Folder")
                    }
                    Button {
                        text: "📂+ Sub"; Layout.fillWidth: true; enabled: activeItem && activeItem.isFolder
                        contentItem: Text { text: parent.text; color: parent.enabled ? "white" : "#666"; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                        background: Rectangle { color: parent.enabled ? (parent.pressed ? "#555" : (parent.hovered ? "#444" : "#383838")) : "#2a2a2a"; radius: 4 }
                        onClicked: vault.addSubFolder(activeItem, "Subfolder")
                    }
                    Button {
                        text: "📄+ Note"; Layout.fillWidth: true; enabled: activeItem && activeItem.isFolder
                        contentItem: Text { text: parent.text; color: parent.enabled ? "white" : "#666"; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                        background: Rectangle { color: parent.enabled ? (parent.pressed ? "#1a73e8" : (parent.hovered ? "#007acc" : "#0e639c")) : "#2a2a2a"; radius: 4 }
                        onClicked: vault.addNote(activeItem, "New Note")
                    }
                }
                ScrollView {
                    Layout.fillHeight: true; Layout.fillWidth: true; clip: true
                    ListView { id: vaultListView; width: parent.width; model: vault.rootItems; delegate: folderDelegate; spacing: 2 }
                }
            }
        }

        StackLayout {
            id: mainStack; Layout.fillHeight: true; Layout.fillWidth: true
            currentIndex: tabBar.currentIndex

            // Editor
            Rectangle {
                color: "#1e1e1e"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 60; spacing: 20
                    TextField {
                        text: activeItem ? activeItem.title : ""
                        font.pixelSize: 36; font.bold: true; color: "white"; background: null
                        onTextEdited: if(activeItem) activeItem.title = text
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: "#333" }
                    TextArea {
                        visible: activeItem && !activeItem.isFolder
                        text: activeItem ? activeItem.content : ""
                        Layout.fillHeight: true; Layout.fillWidth: true
                        color: "#d4d4d4"; font.pixelSize: 18; wrapMode: TextEdit.Wrap; background: null
                        selectByMouse: true
                        onTextChanged: if(activeItem && !activeItem.isFolder && focus) activeItem.content = text
                    }
                    Item { Layout.fillHeight: true; visible: !activeItem || activeItem.isFolder }
                }
            }

            // Graph
            Rectangle {
                id: graphViewport; color: "#0a0a0a"; clip: true

                Item {
                    id: graphContainer
                    width: 5000; height: 5000
                    x: -2500 + graphViewport.width/2 + camX; y: -2500 + graphViewport.height/2 + camY
                    scale: camS

                    property real camX: 0; property real camY: 0; property real camS: 1.0

                    Canvas {
                        id: graphCanvas; anchors.fill: parent
                        Connections {
                            target: vault
                            function onRootChanged() { graphCanvas.requestPaint() }
                        }
                        onPaint: {
                            var ctx = getContext("2d"); ctx.clearRect(0,0,width,height)
                            ctx.strokeStyle = "#252526"; ctx.lineWidth = 1.5
                            function drawH(node) {
                                if (!node.isFolder) return
                                for (var i=0; i < node.childrenQml.length; i++) {
                                    var c = node.childrenQml[i]
                                    ctx.beginPath(); ctx.moveTo(node.graphX + 2525, node.graphY + 2525)
                                    ctx.lineTo(c.graphX + 2525, c.graphY + 2525); ctx.stroke(); drawH(c)
                                }
                            }
                            for(var i=0; i < vault.rootItems.length; i++) drawH(vault.rootItems[i])
                        }
                    }

                    Repeater {
                        model: vault.allItems
                        Rectangle {
                            id: nodeRect
                            x: modelData.graphX + 2500; y: modelData.graphY + 2500
                            width: 50; height: 50; radius: modelData.isFolder ? 25 : 8
                            color: modelData.isFolder ? "#0e639c" : "#27ae60"
                            border.color: activeItem === modelData ? "white" : "transparent"; border.width: 2
                            z: nodeMouse.pressed ? 1000 : 1

                            Text {
                                text: modelData.title; color: "white"; anchors.top: parent.bottom
                                anchors.topMargin: 8; anchors.horizontalCenter: parent.horizontalCenter; font.pixelSize: 11
                            }

                            MouseArea {
                                id: nodeMouse; anchors.fill: parent
                                property point lastClickPos

                                onPressed: {
                                    activeItem = modelData
                                    lastClickPos = Qt.point(mouse.x, mouse.y)
                                }

                                onPositionChanged: {
                                    if (pressed) {
                                        var dx = (mouse.x - lastClickPos.x) / graphContainer.camS
                                        var dy = (mouse.y - lastClickPos.y) / graphContainer.camS
                                        modelData.graphX += dx
                                        modelData.graphY += dy
                                        graphCanvas.requestPaint()
                                    }
                                }
                                onDoubleClicked: tabBar.currentIndex = 0
                            }

                            Behavior on x { enabled: !nodeMouse.pressed; NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                            Behavior on y { enabled: !nodeMouse.pressed; NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                        }
                    }
                }

                MouseArea {
                    anchors.fill: parent; z: -1
                    property point startPos
                    onPressed: startPos = Qt.point(mouse.x, mouse.y)
                    onPositionChanged: {
                        if (pressed) {
                            graphContainer.camX += (mouse.x - startPos.x) / graphContainer.camS
                            graphContainer.camY += (mouse.y - startPos.y) / graphContainer.camS
                            startPos = Qt.point(mouse.x, mouse.y)
                        }
                    }
                    onWheel: {
                        var zoom = wheel.angleDelta.y > 0 ? 1.1 : 0.9
                        var ns = graphContainer.camS * zoom
                        if (ns > 0.15 && ns < 4) graphContainer.camS = ns
                    }
                }

                Button {
                    text: "🎯 Center"
                    anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 20
                    contentItem: Text { text: parent.text; color: "white"; font.bold: true }
                    background: Rectangle { color: "#333"; radius: 4; border.color: "#555" }
                    onClicked: { graphContainer.camS = 1.0; graphContainer.camX = 0; graphContainer.camY = 0 }
                }
            }
        }
    }

    footer: Rectangle {
        height: 45; color: "#252526"; border.color: "#181818"; border.width: 1
        RowLayout {
            anchors.fill: parent; spacing: 0
            TabBar {
                id: tabBar; Layout.fillHeight: true; Layout.preferredWidth: 300; background: null
                TabButton { text: "📝 Editor"; background: Rectangle { color: parent.checked ? "#1e1e1e" : "transparent" }
                    contentItem: Text { text: parent.text; color: parent.checked ? "#007acc" : "#888"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
                TabButton { text: "🕸 Graph"; background: Rectangle { color: parent.checked ? "#0a0a0a" : "transparent" }
                    contentItem: Text { text: parent.text; color: parent.checked ? "#007acc" : "#888"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "Vault Stats: " + vault.globalStats.notes + " Notes | " + vault.globalStats.words + " Words"
                color: "#888"; font.pixelSize: 12; Layout.rightMargin: 20
            }
        }
    }

    Component {
        id: folderDelegate
        Column {
            id: col; width: vaultListView.width
            property int level: parent.hasOwnProperty("level") ? parent.level + 1 : 0

            Rectangle {
                width: parent.width; height: 38; color: activeItem === modelData ? "#37373d" : "transparent"; radius: 4

                Row {
                    anchors.left: parent.left; anchors.leftMargin: 10 + (col.level * 15); anchors.verticalCenter: parent.verticalCenter; spacing: 8
                    Text { text: modelData.isFolder ? "📂" : "📄"; font.pixelSize: 14 }
                    Text {
                        text: modelData.title; color: activeItem === modelData ? "white" : "#aaa"; font.pixelSize: 14
                        width: col.width - (col.level * 15) - 80; elide: Text.ElideRight; font.bold: activeItem === modelData
                    }
                }

                Button {
                    anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                    width: 24; height: 24; text: "×"; flat: true
                    contentItem: Text { text: parent.text; color: parent.hovered ? "white" : "#777"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.pixelSize: 18 }
                    background: Rectangle { color: parent.hovered ? "#e81123" : "transparent"; radius: 4 }
                    onClicked: vault.deleteItem(modelData)
                }
                MouseArea { anchors.fill: parent; z: -1; onClicked: activeItem = modelData }
            }
            Column {
                visible: modelData.isFolder; width: parent.width; property int level: col.level
                Repeater { model: modelData.isFolder ? modelData.childrenQml : [] ; delegate: folderDelegate }
            }
        }
    }
}