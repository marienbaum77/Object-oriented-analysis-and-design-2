import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    visible: true; width: 1000; height: 700
    title: "No Pattern Version"

    ListView {
        anchors.fill: parent
        model: plainController.rootFolders
        delegate: Column {
            Text { text: "Folder: " + modelData.title }

            Repeater {
                model: modelData.subFolders
                delegate: Text { text: "  Sub: " + modelData.title; x: 20 }
            }

            Repeater {
                model: modelData.notes
                delegate: Text { text: "  Note: " + modelData.title; x: 20 }
            }
        }
    }
}