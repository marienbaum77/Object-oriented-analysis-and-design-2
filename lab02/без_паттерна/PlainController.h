#ifndef PLAINCONTROLLER_H
#define PLAINCONTROLLER_H

#include <QObject>
#include <QFile>
#include <QJsonDocument>
#include "PlainModels.h"

class PlainController : public QObject {
    Q_OBJECT
    Q_PROPERTY(QVariantList rootFolders READ rootFolders NOTIFY changed)
    Q_PROPERTY(QVariantMap globalStats READ globalStats NOTIFY changed)

public:
    explicit PlainController(QObject *parent = nullptr) : QObject(parent) {}

    QVariantList rootFolders() const {
        QVariantList l;
        for (auto f : m_roots) l << QVariant::fromValue(f);
        return l;
    }

    QVariantMap globalStats() const {
        int n = 0, w = 0;
        for (auto f : m_roots) {
            auto s = calculateFolderStats(f);
            n += s.first; w += s.second;
        }
        return { {"notes", n}, {"words", w} };
    }

    Q_INVOKABLE void addFolder(QObject* parent, QString name) {
        auto* newF = new PlainFolder(name, this);
        if (!parent) m_roots.push_back(newF);
        else if (auto* pF = qobject_cast<PlainFolder*>(parent)) pF->m_subFolders.push_back(newF);
        emit changed();
    }

    Q_INVOKABLE void addNote(QObject* parent, QString name) {
        if (auto* pF = qobject_cast<PlainFolder*>(parent)) {
            pF->m_notes.push_back(new Note(name, this));
            emit changed();
        }
    }

    Q_INVOKABLE QJsonObject exportFolder(PlainFolder* f) {
        QJsonObject obj;
        obj["title"] = f->m_title;
        QJsonArray subF;
        for (auto s : f->m_subFolders) subF.append(exportFolder(s));
        obj["folders"] = subF;
        QJsonArray notes;
        for (auto n : f->m_notes) {
            QJsonObject nObj;
            nObj["title"] = n->m_title;
            nObj["content"] = n->m_content;
            notes.append(nObj);
        }
        obj["notes"] = notes;
        return obj;
    }

signals:
    void changed();

private:
    QVector<PlainFolder*> m_roots;

    std::pair<int, int> calculateFolderStats(PlainFolder* f) const {
        int n = f->m_notes.size();
        int w = 0;
        for (auto note : f->m_notes) {
            w += note->m_content.split(QRegularExpression("\\s+")).size();
        }
        for (auto sub : f->m_subFolders) {
            auto res = calculateFolderStats(sub);
            n += res.first; w += res.second;
        }
        return {n, w};
    }
};

#endif