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
    void setGraphX(double x) {
        if (qAbs(m_graphX - x) > 0.1) { m_graphX = x; emit graphPosChanged(); }
    }

    double graphY() const { return m_graphY; }
    void setGraphY(double y) {
        if (qAbs(m_graphY - y) > 0.1) { m_graphY = y; emit graphPosChanged(); }
    }

    virtual bool isFolder() const = 0;
    Q_INVOKABLE virtual QVariantMap getStats() const = 0;
    virtual QJsonObject toJson() const = 0;

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
    Q_INVOKABLE QVariantMap getStats() const override {
        return { {"notes", 1}, {"chars", m_content.length()},
                {"words", m_content.split(QRegularExpression("\\s+"), Qt::SkipEmptyParts).count()} };
    }
    QJsonObject toJson() const override {
        QJsonObject obj; obj["type"] = "note"; obj["title"] = m_title;
        obj["content"] = m_content; obj["x"] = m_graphX; obj["y"] = m_graphY;
        return obj;
    }
signals:
    void contentChanged();
private:
    QString m_content;
};

class Folder : public VaultItem {
    Q_OBJECT
    Q_PROPERTY(QVariantList childrenQml READ childrenQml NOTIFY childrenChanged)
public:
    explicit Folder(QString t, QObject *parent = nullptr) : VaultItem(t, parent) {}
    bool isFolder() const override { return true; }
    void add(VaultItem* item) {
        m_children.push_back(item); item->setParent(this);
        connect(item, &VaultItem::statsChanged, this, &Folder::statsChanged);
        emit childrenChanged(); emit statsChanged();
    }
    void remove(VaultItem* item) {
        item->disconnect(this); m_children.removeAll(item); item->deleteLater();
        emit childrenChanged(); emit statsChanged();
    }
    QVariantList childrenQml() const {
        QVariantList list; for (auto c : m_children) list << QVariant::fromValue(c);
        return list;
    }
    const QVector<VaultItem*>& getChildren() const { return m_children; }
    Q_INVOKABLE QVariantMap getStats() const override {
        int n = 0, w = 0, c = 0;
        for (auto child : m_children) {
            auto s = child->getStats();
            n += s["notes"].toInt(); w += s["words"].toInt(); c += s["chars"].toInt();
        }
        return { {"notes", n}, {"words", w}, {"chars", c} };
    }
    QJsonObject toJson() const override {
        QJsonObject obj; obj["type"] = "folder"; obj["title"] = m_title;
        obj["x"] = m_graphX; obj["y"] = m_graphY;
        QJsonArray ch; for (auto c : m_children) ch.append(c->toJson());
        obj["children"] = ch; return obj;
    }
signals:
    void childrenChanged();
private:
    QVector<VaultItem*> m_children;
};
#endif