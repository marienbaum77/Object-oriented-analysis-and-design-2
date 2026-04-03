#ifndef VAULTCONTROLLER_H
#define VAULTCONTROLLER_H

#include <QObject>
#include "VaultItem.h"

class VaultController : public QObject {
    Q_OBJECT
public:
    explicit VaultController(QObject *parent = nullptr) : QObject(parent) {}

    QVariantMap globalStats() const {
        int n = 0, w = 0, c = 0;
        for (auto r : m_roots) {
            if (Folder* f = qobject_cast<Folder*>(r)) {
                auto s = f->getFolderStats();
                n += s["notes"].toInt(); w += s["words"].toInt(); c += s["chars"].toInt();
            } else if (Note* note = qobject_cast<Note*>(r)) {
                auto s = note->getNoteStats();
                n += s["notes"].toInt(); w += s["words"].toInt(); c += s["chars"].toInt();
            }
        }
        return { {"notes", n}, {"words", w}, {"chars", c} };
    }

    Q_INVOKABLE void deleteItem(QObject* item) {
        if (!item) return;
        
        Folder* parentFolder = qobject_cast<Folder*>(item->parent());
        
        if (Note* n = qobject_cast<Note*>(item)) {
            if (parentFolder) parentFolder->m_notes.removeAll(n);
            n->deleteLater();
        } else if (Folder* f = qobject_cast<Folder*>(item)) {
            if (parentFolder) parentFolder->m_subFolders.removeAll(f);
            else m_roots.removeAll(f);
            f->deleteLater();
        }
        emit rootChanged();
    }

    Q_INVOKABLE QJsonObject serializeFolder(Folder* folder) {
        QJsonObject obj;
        obj["title"] = folder->m_title;
        
        QJsonArray notesArr;
        for (Note* n : folder->notes) {
            QJsonObject nObj;
            nObj["title"] = n->m_title;
            nObj["content"] = n->m_content;
            notesArr.append(nObj);
        }
        obj["notes"] = notesArr;

        QJsonArray foldersArr;
        for (Folder* f : folder->subFolders) {
            foldersArr.append(serializeFolder(f));
        }
        obj["folders"] = foldersArr;

        return obj;
    }
};

#endif
