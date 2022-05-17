# UI End-to-end тесты

Данный вид тестов делает end to end тестирование с помощью UI и воспроизводит пользовательские сценарии.

Тесты базируются на библиотеке [Playwright](playwright.dev/python/docs/intro), которая с помощью Developer Tools Protocol общается с браузером по websocket протоколу.
А также используют Page Object pattern -

## Запуск тестов

Тесты пишутся для запуска против контейнера, включенном в Hosted Mode режиме.

### Опции запуска

--base-url=<> - URL контейнера

--browser - указание браузера на каком запускать тест

--headed - включить браузер с UI (по умолчанию headless режим)


### Запуск в devbox на удаленном кластере

Для запуска на удаленном moon кластере:

```bash
py.test tests/ui/test_verify_pages.py --base-url=https://org0.te.scalr-labs.net/ --browser=chromium --remote-server=35.242.174.31
```

На удаленном кластере доступен еще chrome для запуска (на кластере можно запустить любой браузер, но надо добавлять поддержку в playwright)


### Запуск в devbox контейнере на локальном браузере
!!!!!! Данный способ еще не работает, браузер в докере не запускается (надо разбираться https://playwright.dev/docs/docker?_highlight=docker)

После запуска devbox, необходимо установить локально браузеры

```bash
playwright install
apt-get update

apt-get install libnss3 libatk-adaptor libcups2-dev libdrm2 libxkbcommon-x11-0 libxcomposite1 libxdamage-dev libxrandr2 libgbm1 libasound2 	libxshmfence1
```

Эта команда скачает и установит headless браузеры, на которых будут запускаться тесты.

Чтобы запустить любой тест:

```bash
py.test tests/ui/test_verify_pages.py --base-url=https://org0.te.scalr-labs.net/ --browser=chromium
```

При локальном запуске доступны следующие браузеры: chromium, firefox, webkit


## Структура тестов

1. components - реализация UI компонентов для extjs/react фреймворков. Под компонентами понимается реализация классов, которые позволяют легко взаимодействовать с какими-то компонентами на странице.
Например, один раз реализованный компонент Button позволит на всех страницах одинаково его искать, нажимать, проверять состояние.

2. pages - реализация страниц в PageObject паттерне

    2.1. В модуле реализован базовый класс BasePage, реализующий ожидание страницы и меню

    2.2. Также, в модуле реализовано верхнее меню и взаимодействие с ним (открытие, получение пунктов меню)

3. plugins - необходимые плагины для UI тестов.

    3.1. browser плагин - необходимые фикстуры для запуска playwright и работы с ним

4. libs - вспомогательные и общие модули


## Фикстуры

scalr_login_page - анонимным пользователем заходит на страницу авторизации в Scalr

scalr_global_scope - авторизует global admin (user: admin) и отдает страницу Global Scope Dashboard

scalr_account_scope - авторизует account admin (user: tf-admin) и отдает страницу Account Scope Dashboard

scalr_env_scope - авторизует пользователя (user: tf) и отдает страницу Account Scope Dashboard
