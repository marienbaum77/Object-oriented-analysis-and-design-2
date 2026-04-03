#ifndef VAULTITEM_H
#define VAULTITEM_H

#include <QObject>
#include <QString>
#include <QVector>
#include <QVariantMap>
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
    double m_graphX = 0;
    double m_graphY = 0;
signals:
    void titleChanged();
    void graphPosChanged();
};

class Note : public VaultItem {
    Q_OBJECT
    Q_PROPERTY(QString content MEMBER m_content NOTIFY contentChanged)
public:
    explicit Note(QString t, QObject *parent = nullptr) : VaultItem(t, parent) {}
    QString m_content;
    
    QVariantMap getOwnStats() const {
        return { {"notes", 1}, {"chars", m_content.length()} };
    }
signals:
    void contentChanged();
};

class Folder : public VaultItem {
    Q_OBJECT
public:
    explicit Folder(QString t, QObject *parent = nullptr) : VaultItem(t, parent) {}

    QVector<Folder*> subFolders;
    QVector<Note*> notes;

    Q_PROPERTY(QVariantList subFoldersQml READ subFoldersQml NOTIFY changed)
    Q_PROPERTY(QVariantList notesQml READ notesQml NOTIFY changed)

    QVariantList subFoldersQml() const {
        QVariantList list;
        for (auto f : subFolders) list << QVariant::fromValue(f);
        return list;
    }
    QVariantList notesQml() const {
        QVariantList list;
        for (auto n : notes) list << QVariant::fromValue(n);
        return list;
    }

signals:
    void changed();
};

#endif
