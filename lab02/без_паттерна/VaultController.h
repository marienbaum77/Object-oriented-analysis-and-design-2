#ifndef VAULTCONTROLLER_H
#define VAULTCONTROLLER_H

#include <QObject>
#include "VaultItem.h"

class VaultController : public QObject {
    Q_OBJECT
public:
    explicit VaultController(QObject *parent = nullptr) : QObject(parent) {}

    Q_INVOKABLE QVariantMap calculateFolderStats(Folder* folder) {
        int notesCount = 0;
        int charsCount = 0;

        for (Note* note : folder->notes) {
            notesCount++;
            charsCount += note->m_content.length();
        }

        for (Folder* sub : folder->subFolders) {
            QVariantMap subStats = calculateFolderStats(sub);
            notesCount += subStats["notes"].toInt();
            charsCount += subStats["chars"].toInt();
        }

        return { {"notes", notesCount}, {"chars", charsCount} };
    }

   Q_INVOKABLE void deleteItem(QObject* item) {
        if (!item) return;

        if (Note* n = qobject_cast<Note*>(item)) {
            Folder* parent = qobject_cast<Folder*>(n->parent());
            if (parent) {
                parent->notes.removeAll(n);
            }
            n->deleteLater();
        } 
        else if (Folder* f = qobject_cast<Folder*>(item)) {
            Folder* parent = qobject_cast<Folder*>(f->parent());
            if (parent) {
                parent->subFolders.removeAll(f);
            } else {
                m_roots.removeAll(f);
            }
            f->deleteLater();
        }
        
        emit rootChanged();
        save(); 
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
