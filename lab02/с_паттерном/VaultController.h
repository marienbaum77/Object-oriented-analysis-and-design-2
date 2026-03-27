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
        for (auto r : m_roots) collectAll(r, list);
        return list;
    }

    QVariantMap globalStats() const {
        int n = 0, w = 0, c = 0, d = 0;
        for (auto r : m_roots) {
            auto s = r->getStats();
            n += s["notes"].toInt(); w += s["words"].toInt();
            c += s["chars"].toInt(); d += s["done"].toInt();
        }
        return { {"notes", n}, {"words", w}, {"chars", c}, {"done", d} };
    }

    Q_INVOKABLE void addRootFolder(QString name) {
        auto f = new Folder(name, this);
        m_roots.push_back(f);
        connect(f, &VaultItem::statsChanged, this, &VaultController::globalStatsChanged);
        emit rootChanged(); emit globalStatsChanged(); save();
    }

    Q_INVOKABLE void addNote(VaultItem* parent, QString name) {
        if (auto f = qobject_cast<Folder*>(parent)) { f->add(new Note(name)); emit rootChanged(); save(); }
    }

    Q_INVOKABLE void addSubFolder(VaultItem* parent, QString name) {
        if (auto f = qobject_cast<Folder*>(parent)) { f->add(new Folder(name)); emit rootChanged(); save(); }
    }

    Q_INVOKABLE void deleteItem(VaultItem* item) {
        if (!item) return;
        auto p = item->parent();
        if (auto f = qobject_cast<Folder*>(p)) f->remove(item);
        else { item->disconnect(this); m_roots.removeAll(item); item->deleteLater(); }
        emit rootChanged(); emit globalStatsChanged(); save();
    }

    Q_INVOKABLE void save() {
        QJsonArray rootArr;
        for (auto r : m_roots) rootArr.append(r->toJson());
        QFile file("vault_data.json");
        if (file.open(QIODevice::WriteOnly)) { file.write(QJsonDocument(rootArr).toJson()); file.close(); }
    }

    void load() {
        QFile file("vault_data.json");
        if (!file.open(QIODevice::ReadOnly)) return;
        QJsonArray rootArr = QJsonDocument::fromJson(file.readAll()).array();
        for (auto v : rootArr) {
            auto item = parseJson(v.toObject());
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
    void collectAll(VaultItem* item, QVariantList& list) const {
        list << QVariant::fromValue(item);
        if (auto f = qobject_cast<Folder*>(item)) {
            for (auto c : f->getChildren()) collectAll(c, list);
        }
    }
    VaultItem* parseJson(const QJsonObject& obj) {
        VaultItem* item;
        if (obj["type"].toString() == "folder") {
            auto f = new Folder(obj["title"].toString(), this);
            QJsonArray children = obj["children"].toArray();
            for (auto c : children) f->add(parseJson(c.toObject()));
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