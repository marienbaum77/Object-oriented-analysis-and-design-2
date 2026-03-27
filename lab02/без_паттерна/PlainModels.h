#ifndef PLAINMODELS_H
#define PLAINMODELS_H

#include <QObject>
#include <QString>
#include <QVector>
#include <QVariantMap>
#include <QRegularExpression>
#include <QJsonObject>
#include <QJsonArray>

class PlainNote : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString title MEMBER m_title NOTIFY dataChanged)
    Q_PROPERTY(QString content MEMBER m_content NOTIFY dataChanged)
public:
    explicit PlainNote(QString t, QObject *parent = nullptr) : QObject(parent), m_title(t) {}
    QString m_title;
    QString m_content;
signals:
    void dataChanged();
};

class PlainFolder : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString title MEMBER m_title NOTIFY dataChanged)
    Q_PROPERTY(QVariantList subFolders READ subFoldersQml NOTIFY dataChanged)
    Q_PROPERTY(QVariantList notes READ notesQml NOTIFY dataChanged)
public:
    explicit PlainFolder(QString t, QObject *parent = nullptr) : QObject(parent), m_title(t) {}
    QString m_title;
    QVector<PlainFolder*> m_subFolders;
    QVector<PlainNote*> m_notes;

    QVariantList subFoldersQml() const {
        QVariantList l;
        for (auto f : m_subFolders) l << QVariant::fromValue(f);
        return l;
    }

    QVariantList notesQml() const {
        QVariantList l;
        for (auto n : m_notes) l << QVariant::fromValue(n);
        return l;
    }
signals:
    void dataChanged();
};

#endif