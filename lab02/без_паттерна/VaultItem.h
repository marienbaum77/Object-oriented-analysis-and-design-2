#ifndef VAULTITEM_H
#define VAULTITEM_H

#include <QObject>
#include <QString>
#include <QVector>
#include <QVariantMap>
#include <QRegularExpression>
#include <QRandomGenerator>
#include <QJsonObject>
#include <QJsonArray>

class VaultItem : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString title READ title WRITE setTitle NOTIFY titleChanged)
    Q_PROPERTY(bool isFolder READ isFolder CONSTANT)
    Q_PROPERTY(double graphX READ graphX WRITE setGraphX NOTIFY graphPosChanged)
    Q_PROPERTY(double graphY READ graphY WRITE setGraphY NOTIFY graphPosChanged)

public:
    explicit VaultItem(QString t, QObject *parent = nullptr) : QObject(parent), m_title(t) {
        m_graphX = QRandomGenerator::global()->bounded(50, 600);
        m_graphY = QRandomGenerator::global()->bounded(50, 400);
    }

    QString title() const { return m_title; }
    void setTitle(const QString &t) { if (m_title != t) { m_title = t; emit titleChanged(); } }
    double graphX() const { return m_graphX; }
    void setGraphX(double x) { if (qAbs(m_graphX - x) > 0.1) { m_graphX = x; emit graphPosChanged(); } }
    double graphY() const { return m_graphY; }
    void setGraphY(double y) { if (qAbs(m_graphY - y) > 0.1) { m_graphY = y; emit graphPosChanged(); } }

    virtual bool isFolder() const = 0;

signals:
    void titleChanged();
    void graphPosChanged();
    void statsChanged();

protected:
    QString m_title;
    double m_graphX;
    double m_graphY;
};

class Note : public VaultItem {
    Q_OBJECT
    Q_PROPERTY(QString content READ content WRITE setContent NOTIFY contentChanged)
public:
    explicit Note(QString t, QObject *parent = nullptr) : VaultItem(t, parent) {}
    bool isFolder() const override { return false; }
    QString content() const { return m_content; }
    void setContent(const QString &c) {
        if (m_content != c) { m_content = c; emit contentChanged(); emit statsChanged(); }
    }

    QVariantMap getNoteStats() const {
        return { {"notes", 1}, {"chars", m_content.length()},
                {"words", m_content.split(QRegularExpression("\\s+"), Qt::SkipEmptyParts).count()} };
    }

    QJsonObject noteToJson() const {
        QJsonObject obj; 
        obj["type"] = "note"; 
        obj["title"] = m_title;
        obj["content"] = m_content; 
        obj["x"] = m_graphX; 
        obj["y"] = m_graphY;
        return obj;
    }

signals:
    void contentChanged();
private:
    QString m_content;
};

class Folder : public VaultItem {
    Q_OBJECT
    Q_PROPERTY(QVariantList subFoldersQml READ subFoldersQml NOTIFY childrenChanged)
    Q_PROPERTY(QVariantList notesQml READ notesQml NOTIFY childrenChanged)
public:
    explicit Folder(QString t, QObject *parent = nullptr) : VaultItem(t, parent) {}
    bool isFolder() const override { return true; }

    QVector<Folder*> m_subFolders;
    QVector<Note*> m_notes;

    void addNote(Note* n) { m_notes.push_back(n); n->setParent(this); emit childrenChanged(); emit statsChanged(); }
    void addFolder(Folder* f) { m_subFolders.push_back(f); f->setParent(this); emit childrenChanged(); emit statsChanged(); }

    void removeNote(Note* n) { m_notes.removeAll(n); n->deleteLater(); emit childrenChanged(); emit statsChanged(); }
    void removeFolder(Folder* f) { m_subFolders.removeAll(f); f->deleteLater(); emit childrenChanged(); emit statsChanged(); }

    QVariantList subFoldersQml() const {
        QVariantList list; for (auto c : m_subFolders) list << QVariant::fromValue(c);
        return list;
    }
    QVariantList notesQml() const {
        QVariantList list; for (auto c : m_notes) list << QVariant::fromValue(c);
        return list;
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
        obj["type"] = "folder"; 
        obj["title"] = m_title;
        obj["x"] = m_graphX; 
        obj["y"] = m_graphY;
        QJsonArray ch; 
        for (auto s : m_subFolders) ch.append(s->folderToJson());
        for (auto n : m_notes) ch.append(n->noteToJson());
        obj["children"] = ch; 
        return obj;
    }

signals:
    void childrenChanged();
};
#endif
