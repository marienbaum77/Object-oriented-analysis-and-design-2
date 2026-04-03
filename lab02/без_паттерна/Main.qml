
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1200
    height: 800
    title: "Obsidian Plain Version (No Patterns)"
    color: "#1e1e1e"

    property var activeItem: null

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: sidebar
            Layout.fillHeight: true
            Layout.preferredWidth: 360
            color: "#252526"
            z: 10 

            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 12
                anchors.bottomMargin: 12
                spacing: 12
                
                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    spacing: 8
                    
                    Button { 
                        text: "📁+ Root"
                        Layout.fillWidth: true
                        contentItem: Text { text: parent.text; color: "white"; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                        background: Rectangle { color: parent.pressed ? "#555" : (parent.hovered ? "#444" : "#383838"); radius: 4 }
                        onClicked: vault.addRootFolder("New Folder")
                    }
                    Button { 
                        text: "📂+ Sub"
                        Layout.fillWidth: true
                        enabled: activeItem && activeItem.isFolder
                        background: Rectangle { color: parent.enabled ? (parent.pressed ? "#555" : (parent.hovered ? "#444" : "#383838")) : "#2a2a2a"; radius: 4 }
                        contentItem: Text { text: parent.text; color: parent.enabled ? "white" : "#666"; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                        onClicked: vault.addSubFolder(activeItem, "Subfolder")
                    }
                    Button { 
                        text: "📄+ Note"
                        Layout.fillWidth: true
                        enabled: activeItem && activeItem.isFolder
                        background: Rectangle { color: parent.enabled ? (parent.pressed ? "#1a73e8" : (parent.hovered ? "#007acc" : "#0e639c")) : "#2a2a2a"; radius: 4 }
                        contentItem: Text { text: parent.text; color: parent.enabled ? "white" : "#666"; font.bold: true; horizontalAlignment: Text.AlignHCenter }
                        onClicked: vault.addNote(activeItem, "New Note")
                    }
                }
                
                ScrollView {
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    clip: true
                    ListView { 
                        id: vaultListView
                        width: parent.width
                        model: vault.rootItems
                        delegate: folderDelegate
                        spacing: 2 
                    }
                }
            }
        }

        StackLayout {
            id: mainStack
            Layout.fillHeight: true
            Layout.fillWidth: true
            currentIndex: tabBar.currentIndex

            Rectangle {
                color: "#1e1e1e"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 60
                    spacing: 20
                    TextField {
                        text: activeItem ? activeItem.title : ""
                        font.pixelSize: 36
                        font.bold: true
                        color: "white"
                        background: null
                        onTextEdited: if(activeItem) activeItem.title = text
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: "#333" }
                    TextArea {
                        visible: activeItem && !activeItem.isFolder
                        text: activeItem ? activeItem.content : ""
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        color: "#d4d4d4"
                        font.pixelSize: 18
                        wrapMode: TextEdit.Wrap
                        background: null
                        onTextChanged: if(activeItem && !activeItem.isFolder && focus) activeItem.content = text
                    }
                    Item { Layout.fillHeight: true; visible: !activeItem || activeItem.isFolder }
                }
            }

            Rectangle {
                id: graphViewport
                color: "#0a0a0a"
                clip: true
                Item {
                    id: graphContainer
                    width: parent.width
                    height: parent.height
                    
                    Canvas {
                        id: graphCanvas
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0,0,width,height)
                            ctx.strokeStyle = "#333"
                            ctx.lineWidth = 1.5
                            
                            function drawPlainLinks(folder) {
                                var i;
                                for (i = 0; i < folder.subFoldersQml.length; i++) {
                                    var sf = folder.subFoldersQml[i]
                                    ctx.beginPath()
                                    ctx.moveTo(folder.graphX + 25, folder.graphY + 25)
                                    ctx.lineTo(sf.graphX + 25, sf.graphY + 25)
                                    ctx.stroke()
                                    drawPlainLinks(sf)
                                }
                                for (i = 0; i < folder.notesQml.length; i++) {
                                    var n = folder.notesQml[i]
                                    ctx.beginPath()
                                    ctx.moveTo(folder.graphX + 25, folder.graphY + 25)
                                    ctx.lineTo(n.graphX + 25, n.graphY + 25)
                                    ctx.stroke()
                                }
                            }
                            
                            for(var k=0; k < vault.rootItems.length; k++) {
                                drawPlainLinks(vault.rootItems[k])
                            }
                        }
                    }

                    Repeater {
                        model: vault.allFolders
                        Rectangle {
                            x: modelData.graphX; y: modelData.graphY
                            width: 50; height: 50; radius: 25; color: "#0e639c"
                            Text { text: modelData.title; color: "white"; anchors.top: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                    Repeater {
                        model: vault.allNotes
                        Rectangle {
                            x: modelData.graphX; y: modelData.graphY
                            width: 50; height: 50; radius: 8; color: "#27ae60"
                            Text { text: modelData.title; color: "white"; anchors.top: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                }
            }
        }
    }

    footer: Rectangle {
        height: 45; color: "#252526"
        RowLayout {
            anchors.fill: parent
            TabBar {
                id: tabBar; Layout.fillHeight: true; Layout.preferredWidth: 300
                TabButton { text: "Editor" }
                TabButton { text: "Graph" }
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "Notes: " + vault.globalStats.notes + " | Words: " + vault.globalStats.words
                color: "#666"; font.pixelSize: 12; Layout.rightMargin: 20
            }
        }
    }

    Component {
        id: noteDelegate
        Rectangle {
            width: vaultListView.width; height: 38; color: activeItem === modelData ? "#37373d" : "transparent"
            Row {
                anchors.left: parent.left; anchors.leftMargin: 10 + (col.level * 15 + 15)
                anchors.verticalCenter: parent.verticalCenter; spacing: 8
                Text { text: "📄"; font.pixelSize: 14 }
                Text { text: modelData.title; color: activeItem === modelData ? "white" : "#aaa"; font.pixelSize: 14 }
            }
            Button {
                anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                text: "×"; onClicked: vault.deleteItem(modelData)
            }
            MouseArea { anchors.fill: parent; z: -1; onClicked: activeItem = modelData }
        }
    }

    Component {
        id: folderDelegate
        Column {
            id: col
            property int level: parent.hasOwnProperty("level") ? parent.level + 1 : 0
            width: vaultListView.width

            Rectangle {
                width: parent.width; height: 38; color: activeItem === modelData ? "#37373d" : "transparent"
                Row {
                    anchors.left: parent.left; anchors.leftMargin: 10 + (col.level * 15)
                    anchors.verticalCenter: parent.verticalCenter; spacing: 8
                    Text { text: "📂"; font.pixelSize: 14 }
                    Text { text: modelData.title; color: activeItem === modelData ? "white" : "#aaa"; font.pixelSize: 14 }
                }
                Button {
                    anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                    text: "×"; onClicked: vault.deleteItem(modelData)
                }
                MouseArea { anchors.fill: parent; z: -1; onClicked: activeItem = modelData }
            }
            
            Column {
                visible: true
                width: parent.width
                property int level: col.level
                
                Repeater {
                    model: modelData.subFoldersQml
                    delegate: folderDelegate
                }
                
                Repeater {
                    model: modelData.notesQml
                    delegate: noteDelegate
                }
            }
        }
    }
}
