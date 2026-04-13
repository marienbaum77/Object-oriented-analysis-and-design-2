#ifndef VAULTCONTROLLER_H
#define VAULTCONTROLLER_H

#include <QObject>
#include <QFile>
#include <QJsonDocument>
#include "VaultItem.h"

class VaultController : public QObject {
    Q_OBJECT
    Q_PROPERTY(QVariantList rootItems READ rootItems NOTIFY rootChanged)
    Q_PROPERTY(QVariantList allItems READ allItems NOTIFY rootChanged)
    Q_PROPERTY(QVariantMap globalStats READ globalStats NOTIFY globalStatsChanged)

public:
    explicit VaultController(QObject *parent = nullptr) : QObject(parent) { load(); }
    ~VaultController() { save(); }

    QVariantList rootItems() const {
        QVariantList list;
        for (auto i : m_roots) list << QVariant::fromValue(i);
        return list;
    }

    QVariantList allItems() const {
        QVariantList list;
        for (auto r : m_roots) collectAllManual(r, list);
        return list;
    }

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

    Q_INVOKABLE void addRootFolder(QString name) {
        auto f = new Folder(name, this);
        m_roots.push_back(f);
        connect(f, &VaultItem::statsChanged, this, &VaultController::globalStatsChanged);
        emit rootChanged(); emit globalStatsChanged(); save();
    }

    Q_INVOKABLE void addNote(VaultItem* parent, QString name) {
        if (auto f = qobject_cast<Folder*>(parent)) { f->addNote(new Note(name)); emit rootChanged(); save(); }
    }

    Q_INVOKABLE void addSubFolder(VaultItem* parent, QString name) {
        if (auto f = qobject_cast<Folder*>(parent)) { f->addFolder(new Folder(name)); emit rootChanged(); save(); }
    }

    Q_INVOKABLE void deleteItem(VaultItem* item) {
        if (!item) return;
        Folder* parentFolder = qobject_cast<Folder*>(item->parent());
        
        if (Note* n = qobject_cast<Note*>(item)) {
            if (parentFolder) parentFolder->removeNote(n);
            else { n->disconnect(this); m_roots.removeAll(n); n->deleteLater(); }
        } else if (Folder* f = qobject_cast<Folder*>(item)) {
            if (parentFolder) parentFolder->removeFolder(f);
            else { f->disconnect(this); m_roots.removeAll(f); f->deleteLater(); }
        }
        emit rootChanged(); emit globalStatsChanged(); save();
    }

    Q_INVOKABLE void save() {
        QJsonArray rootArr;
        for (auto r : m_roots) {
            if (Folder* f = qobject_cast<Folder*>(r)) rootArr.append(f->folderToJson());
            else if (Note* n = qobject_cast<Note*>(r)) rootArr.append(n->noteToJson());
        }
        QFile file("vault_data.json");
        if (file.open(QIODevice::WriteOnly)) { file.write(QJsonDocument(rootArr).toJson()); file.close(); }
    }

    void load() {
        QFile file("vault_data.json");
        if (!file.open(QIODevice::ReadOnly)) return;
        QJsonArray rootArr = QJsonDocument::fromJson(file.readAll()).array();
        for (auto v : rootArr) {
            auto item = parseJsonManual(v.toObject());
            m_roots.push_back(item);
            connect(item, &VaultItem::statsChanged, this, &VaultController::globalStatsChanged);
        }
        emit rootChanged(); emit globalStatsChanged();
    }

signals:
    void rootChanged();
    void globalStatsChanged();

private:
    QVector<VaultItem*> m_roots;

    void collectAllManual(VaultItem* item, QVariantList& list) const {
        list << QVariant::fromValue(item);
        if (auto f = qobject_cast<Folder*>(item)) {
            for (auto sub : f->m_subFolders) collectAllManual(sub, list);
            for (auto note : f->m_notes) collectAllManual(note, list);
        }
    }

    VaultItem* parseJsonManual(const QJsonObject& obj) {
        VaultItem* item;
        if (obj["type"].toString() == "folder") {
            auto f = new Folder(obj["title"].toString(), this);
            QJsonArray children = obj["children"].toArray();
            for (auto v : children) {
                QJsonObject childObj = v.toObject();
                if (childObj["type"].toString() == "folder") f->addFolder(static_cast<Folder*>(parseJsonManual(childObj)));
                else f->addNote(static_cast<Note*>(parseJsonManual(childObj)));
            }
            item = f;
        } else {
            auto n = new Note(obj["title"].toString(), this);
            n->setContent(obj["content"].toString());
            item = n;
        }
        item->setGraphX(obj["x"].toDouble()); item->setGraphY(obj["y"].toDouble());
        return item;
    }
};

#endif
