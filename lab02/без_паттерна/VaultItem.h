#ifndef VAULTITEM_H
#define VAULTITEM_H

#include <QObject>
#include <QString>
#include <QVector>
#include <QVariantMap>
#include <QRegularExpression>
#include <QJsonObject>
#include <QJsonArray>

class VaultItem : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString title MEMBER m_title NOTIFY titleChanged)
    Q_PROPERTY(double graphX MEMBER m_graphX NOTIFY graphPosChanged)
    Q_PROPERTY(double graphY MEMBER m_graphY NOTIFY graphPosChanged)
public:
    explicit VaultItem(QString t, QObject *parent = nullptr) : QObject(parent), m_title(t) {}
    QString m_title;
    double m_graphX;
    double m_graphY;
signals:
    void titleChanged();
    void graphPosChanged();
    void statsChanged();
};

class Note : public VaultItem {
    Q_OBJECT
    Q_PROPERTY(QString content READ content WRITE setContent NOTIFY contentChanged)
public:
    explicit Note(QString t, QObject *parent = nullptr) : VaultItem(t, parent) {}
    QString m_content;
    QString content() const { return m_content; }
    void setContent(const QString &c) { m_content = c; emit contentChanged(); emit statsChanged(); }

    QVariantMap getNoteStats() const {
        return { {"notes", 1}, {"chars", m_content.length()}, 
                 {"words", m_content.split(QRegularExpression("\\s+"), Qt::SkipEmptyParts).count()} };
    }

    QJsonObject noteToJson() const {
        QJsonObject obj;
        obj["type"] = "note"; obj["title"] = m_title; obj["content"] = m_content;
        obj["x"] = m_graphX; obj["y"] = m_graphY;
        return obj;
    }
signals:
    void contentChanged();
};

class Folder : public VaultItem {
    Q_OBJECT
    Q_PROPERTY(QVariantList subFoldersQml READ subFoldersQml NOTIFY childrenChanged)
    Q_PROPERTY(QVariantList notesQml READ notesQml NOTIFY childrenChanged)
public:
    explicit Folder(QString t, QObject *parent = nullptr) : VaultItem(t, parent) {}
    
    QVector<Folder*> m_subFolders;
    QVector<Note*> m_notes;

    QVariantList subFoldersQml() const {
        QVariantList l; for (auto f : m_subFolders) l << QVariant::fromValue(f);
        return l;
    }
    QVariantList notesQml() const {
        QVariantList l; for (auto n : m_notes) l << QVariant::fromValue(n);
        return l;
    }

    QVariantMap getFolderStats() const {
        int n = 0, w = 0, c = 0;
        for (auto note : m_notes) {
            auto s = note->getNoteStats();
            n += s["notes"].toInt(); w += s["words"].toInt(); c += s["chars"].toInt();
        }
        for (auto sub : m_subFolders) {
            auto s = sub->getFolderStats();
            n += s["notes"].toInt(); w += s["words"].toInt(); c += s["chars"].toInt();
        }
        return { {"notes", n}, {"words", w}, {"chars", c} };
    }

    QJsonObject folderToJson() const {
        QJsonObject obj;
        obj["type"] = "folder"; obj["title"] = m_title;
        obj["x"] = m_graphX; obj["y"] = m_graphY;
        QJsonArray ch;
        for (auto f : m_subFolders) ch.append(f->folderToJson());
        for (auto n : m_notes) ch.append(n->noteToJson());
        obj["children"] = ch;
        return obj;
    }
signals:
    void childrenChanged();
};
#endif
