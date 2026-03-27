#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include "VaultController.h"

int main(int argc, char *argv[]) {
    QGuiApplication app(argc, argv);
    QQmlApplicationEngine engine;

    VaultController controller;
    engine.rootContext()->setContextProperty("vault", &controller);

    const QUrl url(QStringLiteral("qrc:/Lab2/Main.qml"));

    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed,
                     &app, []() { QCoreApplication::exit(-1); },
                     Qt::QueuedConnection);

    engine.load(url);

    return app.exec();
}