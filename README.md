# Система двухфакторной аутентификации (2FA)

**Двухфакторная аутентификация как сервис** — централизованное решение для обеспечения безопасности веб-приложений с поддержкой TOTP и Push-уведомлений.

---

## Содержание

- [Описание проекта](#описание-проекта)
- [Технологический стек](#технологический-стек)
- [Архитектура системы](#архитектура-системы)
- [Функциональные возможности](#функциональные-возможности)
- [Быстрый старт](#быстрый-старт)
  - [Развёртывание через Docker](#развёртывание-через-docker)
  - [Локальная разработка](#локальная-разработка)
  - [Настройка Firebase](#настройка-firebase)
- [Мобильное приложение](#мобильное-приложение)
- [API Reference](#api-reference)
- [Сценарии аутентификации](#сценарии-аутентификации)
- [Структура данных](#структура-данных)
- [Тестирование](#тестирование)
- [Безопасность](#безопасность)
- [Конфигурация](#конфигурация)

---

## Описание проекта

Данный проект представляет собой **универсальный 2FA-сервис**, который может быть интегрирован с несколькими внешними веб-приложениями. Система реализует два основных метода второй факторной аутентификации:

1. **TOTP (Time-based One-Time Password)** — одноразовые пароли на основе времени (RFC 6238)
2. **Push-уведомления** — подтверждение входа через мобильное приложение

### Ключевые особенности

- ✅ **Мультиплатформенность** — интеграция с любыми веб-сервисами через REST API
- ✅ **Два метода аутентификации** — TOTP и Push на выбор пользователя
- ✅ **Централизованное хранение** — все данные в Redis для высокой производительности
- ✅ **Веб-интерфейс** — страница входа с QR-кодом для настройки TOTP
- ✅ **Админ-панель** — управление пользователями и устройствами
- ✅ **Мобильное приложение** — нативный Android-клиент для Push-уведомлений
- ✅ **Контейнеризация** — готовое Docker-развёртывание
- ✅ **Покрытие тестами** — 98 автоматических тестов (unit, performance, load)

---

## Технологический стек

### Backend

| Компонент           | Технология         | Версия           |
| ------------------- | ------------------ | ---------------- |
| Язык                | Python             | 3.11+            |
| Web-фреймворк       | FastAPI            | 0.136.1          |
| База данных         | Redis              | 7 (Alpine)       |
| TOTP                | pyotp              | 2.9.0 (RFC 6238) |
| Хеширование паролей | bcrypt             | 4.2.0            |
| Push-уведомления    | Firebase Admin SDK | 6.5.0            |
| Шаблонизатор        | Jinja2             | 3.1.6            |
| Валидация данных    | Pydantic           | 2.9.2            |
| Генерация QR        | qrcode[pil]        | 7.4.2            |

### Mobile Application

| Компонент     | Технология                        |
| ------------- | --------------------------------- |
| Платформа     | Android Native                    |
| Язык          | Kotlin                            |
| Push          | Firebase Cloud Messaging          |
| HTTP-клиент   | OkHttp                            |
| Асинхронность | Kotlin Coroutines                 |
| UI            | Android Views + Material Design 3 |

### DevOps & Quality

| Инструмент             | Назначение                             |
| ---------------------- | -------------------------------------- |
| Docker, docker-compose | Контейнеризация и оркестрация          |
| pytest                 | Автоматизированное тестирование        |
| Bandit                 | Статический анализ безопасности (SAST) |
| pip-audit              | Аудит зависимостей (SCA)               |

---

## Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                  Внешние веб-сервисы (Клиенты 2FA)              │
│                      (интеграция через REST API)                │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS / HTTP
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  2FA Backend (FastAPI, Python)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Auth API     │  │ TOTP API     │  │ Push API     │          │
│  │ /auth/*      │  │ /2fa/totp/*  │  │ /2fa/push/*  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Device API   │  │ Admin API    │  │              │          │
│  │ /device/*    │  │ /admin/*     │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ AuthService  │  │ TotpService  │  │ PushService  │          │
│  │ (bcrypt)     │  │ (pyotp)      │  │ (FCM)        │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Redis Storage (In-Memory)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ user:{id}                    — данные пользователей      │   │
│  │ email_index:{email}          — индекс по email           │   │
│  │ device:{user_id}             — FCM-токены устройств      │   │
│  │ login_request:{request_id}   — запросы входа (TTL=120с)  │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              Firebase Cloud Messaging (Google FCM)              │
│                   (доставка push-уведомлений)                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              Mobile Application (Android, Kotlin)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ MainActivity │  │ FCMService   │  │ ApiClient    │          │
│  │ (UI)         │  │ (Push)       │  │ (OkHttp)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │ Notification │  │ AppPrefs     │                             │
│  │ Helper       │  │ (Storage)    │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Функциональные возможности

### 1. Регистрация и аутентификация пользователей

- **POST /auth/register** — создание нового пользователя в системе 2FA
- **POST /auth/login** — проверка учётных данных (email + пароль), возврат статуса `2fa_required`

### 2. TOTP-аутентификация

- **POST /2fa/totp/setup** — генерация секрета TOTP и QR-кода для привязки
- **GET /2fa/totp/setup/{user_id}** — веб-страница с QR-кодом для сканирования
- **POST /2fa/totp/verify** — проверка 6-значного кода из приложения-аутентификатора

**Поддерживаемые приложения:**
- Google Authenticator
- Authy
- Microsoft Authenticator
- Любое RFC 6238-совместимое приложение

### 3. Push-аутентификация

- **POST /2fa/push/request** — создание запроса на вход с push-уведомлением
- **GET /2fa/push/status/{request_id}** — проверка статуса запроса (pending/approved/denied)
- **GET /2fa/push/pending/{user_id}** — получение активного pending-запроса
- **POST /2fa/push/approve** — подтверждение входа пользователем
- **POST /2fa/push/deny** — отклонение входа пользователем

### 4. Управление устройствами

- **POST /device/register** — регистрация мобильного устройства (email + password + FCM-токен)
- **POST /device/unregister** — отвязка устройства от аккаунта
- **GET /device/list** — список всех зарегистрированных устройств пользователя

### 5. Администрирование

- **GET /admin** — веб-интерфейс админ-панели
- **GET /openapi.json** — спецификация OpenAPI (защищена Basic Auth)
- **GET /docs** — Swagger UI (защищён Basic Auth)
- **GET /redoc** — ReDoc (защищён Basic Auth)
- **POST /admin/devices/{user_id}/unregister** — принудительная отвязка устройства

### 6. Веб-интерфейс

- **GET /** — главная страница с формой входа и настройкой 2FA
- **GET /2fa/totp/setup/{user_id}** — страница с QR-кодом для настройки TOTP

### 7. Мобильное приложение (Android)

- Регистрация устройства через email и пароль
- Автоматическая перерегистрация при смене FCM-токена
- Получение push-уведомлений о запросах входа
- Отображение уведомления с кнопками **Approve** / **Deny**
- Отправка решения на сервер
- Ручная отвязка устройства

---

## Быстрый старт

### Развёртывание через Docker

**Минимальный запуск:**

```bash
cd backend
docker-compose up --build
```

**Запуск в фоновом режиме:**

```bash
cd backend
docker-compose up -d
```

**Просмотр логов:**

```bash
docker-compose logs -f backend
docker-compose logs -f redis
```

**Остановка:**

```bash
docker-compose down
```

**Остановка с удалением данных:**

```bash
docker-compose down -v
```

После запуска сервисы доступны по адресам:

| Сервис        | URL                          |
| ------------- | ---------------------------- |
| API           | http://localhost:8000        |
| Веб-интерфейс | http://localhost:8000        |
| Админ-панель  | http://localhost:8000/admin  |
| Swagger UI    | http://localhost:8000/docs   |
| ReDoc         | http://localhost:8000/redoc  |
| Redis         | localhost:6379               |
| Health check  | http://localhost:8000/health |

---

### Локальная разработка

#### Требования

- Python 3.11+
- Redis 7+ (локально или в Docker)
- pip или poetry

#### Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

#### Запуск Redis (если нет локального)

```bash
docker run -d -p 6379:6379 --name redis-2fa redis:7-alpine
```

#### Создание .env файла

```bash
cd backend
cp .env.example .env
# Отредактируйте .env при необходимости
```

#### Запуск сервера разработки

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Проверка работоспособности

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

---

### Настройка Firebase

#### Для Backend (Push-уведомления)

1. Перейдите в [Firebase Console](https://console.firebase.google.com/)
2. Создайте новый проект
3. Откройте **Project Settings** → **Service Accounts**
4. Нажмите **Generate New Private Key**
5. Скачайте JSON-файл сервисного аккаунта
6. Положите файл как `serviceAccountKey.json` в папку `backend/` **ИЛИ** задайте переменную окружения:

```bash
# В .env файле
FIREBASE_CREDENTIALS={"type": "service_account", "project_id": "...", ...}
```

#### Для Mobile Application (Android)

1. В том же Firebase проекте добавьте **Android-приложение**
2. Укажите package name: `com.example.twofa_app`
3. Скачайте `google-services.json`
4. Положите файл в `mobile_app_native/app/google-services.json`
5. Включите **Firebase Cloud Messaging** в настройках проекта

---

## Мобильное приложение

### Сборка и запуск

#### Требования

- Android Studio Arctic Fox или новее
- JDK 11+
- Android SDK 21+

#### Первый запуск

```bash
cd mobile_app_native

# Синхронизация Gradle
./gradlew sync

# Сборка отладочной версии
./gradlew assembleDebug

# Установка на эмулятор/устройство
adb install app/build/outputs/apk/debug/app-debug.apk
```

#### Настройка Backend URL

По умолчанию приложение использует:

```kotlin
val DEFAULT_BASE_URL = "http://10.0.2.2:8000"  // для Android Emulator
```

Для физического устройства измените URL на IP вашего компьютера:

```kotlin
val DEFAULT_BASE_URL = "http://192.168.1.XXX:8000"
```

#### Основные сценарии использования

1. **Первичная регистрация устройства:**
   - Введите email и пароль от учётной записи 2FA
   - Нажмите **Register Device**
   - Устройство будет привязано к аккаунту

2. **Получение push-уведомления:**
   - При запросе входа через Push на сервере
   - Уведомление появится в шторке уведомлений
   - Нажмите на уведомление для открытия экрана подтверждения

3. **Подтверждение/отклонение входа:**
   - На экране подтверждения нажмите **Approve** или **Deny**
   - Решение будет отправлено на сервер

4. **Отвязка устройства:**
   - Нажмите **Unregister Device** в главном экране
   - Устройство будет удалено из аккаунта

---

## API Reference

### Authentication

#### POST /auth/register
Регистрация нового пользователя.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response (201):**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "message": "User registered successfully"
}
```

---

#### POST /auth/login
Вход по email и паролю.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response (200):**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "status": "2fa_required"
}
```

---

### TOTP

#### POST /2fa/totp/setup
Генерация TOTP секрета.

**Query Parameters:**
- `user_id` (string, required)

**Response (200):**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_url": "/2fa/totp/setup/{user_id}",
  "uri": "otpauth://totp/2FA:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=2FA"
}
```

---

#### POST /2fa/totp/verify
Проверка TOTP кода.

**Request:**
```json
{
  "user_id": "uuid",
  "code": "123456"
}
```

**Response (200):**
```json
{
  "valid": true,
  "message": "TOTP code verified"
}
```

---

### Push Authentication

#### POST /2fa/push/request
Создание запроса на push-аутентификацию.

**Request:**
```json
{
  "user_id": "uuid",
  "site_name": "example.com"
}
```

**Response (201):**
```json
{
  "request_id": "uuid",
  "user_id": "uuid",
  "status": "pending",
  "site_name": "example.com",
  "expires_in": 120
}
```

---

#### GET /2fa/push/status/{request_id}
Проверка статуса запроса.

**Response (200):**
```json
{
  "request_id": "uuid",
  "status": "approved|denied|pending|expired",
  "user_id": "uuid"
}
```

---

#### POST /2fa/push/approve
Подтверждение входа.

**Request:**
```json
{
  "request_id": "uuid"
}
```

**Response (200):**
```json
{
  "message": "Login approved",
  "request_id": "uuid"
}
```

---

#### POST /2fa/push/deny
Отклонение входа.

**Request:**
```json
{
  "request_id": "uuid"
}
```

**Response (200):**
```json
{
  "message": "Login denied",
  "request_id": "uuid"
}
```

---

### Device Management

#### POST /device/register
Регистрация FCM устройства.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "fcm_token": "eXh...token"
}
```

**Response (200):**
```json
{
  "user_id": "uuid",
  "message": "Device registered successfully"
}
```

---

#### POST /device/unregister
Отвязка устройства.

**Request:**
```json
{
  "user_id": "uuid"
}
```

**Response (200):**
```json
{
  "message": "Device unregistered successfully"
}
```

---

#### GET /device/list
Список устройств пользователя.

**Query Parameters:**
- `user_id` (string, required)

**Response (200):**
```json
{
  "devices": [
    {
      "user_id": "uuid",
      "email": "user@example.com",
      "fcm_token": "eXh...token"
    }
  ]
}
```

---

## Сценарии аутентификации

### Полный поток входа с TOTP

```
1. Регистрация пользователя
   POST /auth/register → user_id

2. Первый фактор (вход)
   POST /auth/login → status: 2fa_required

3. Настройка TOTP (один раз)
   POST /2fa/totp/setup → secret + QR-код
   Сканирование QR в Google Authenticator

4. Второй фактор (каждый вход)
   POST /2fa/totp/verify {user_id, code: "123456"} → valid: true

5. Доступ разрешён
```

### Полный поток входа с Push

```
1. Регистрация пользователя
   POST /auth/register → user_id

2. Регистрация устройства
   POST /device/register {email, password, fcm_token} → device registered

3. Первый фактор (вход)
   POST /auth/login → status: 2fa_required

4. Запрос push-аутентификации
   POST /2fa/push/request {user_id, site_name} → request_id

5. Push-уведомление доставляется на мобильное устройство
   FCM → Notification → UI с кнопками Approve/Deny

6. Пользователь подтверждает вход
   POST /2fa/push/approve {request_id} → status: approved

7. Проверка статуса
   GET /2fa/push/status/{request_id} → status: approved

8. Доступ разрешён
```


---

## Структура данных

### Redis Keys

| Ключ                         | Тип    | Описание               | TTL     |
| ---------------------------- | ------ | ---------------------- | ------- |
| `user:{id}`                  | Hash   | Данные пользователя    | ∞       |
| `email_index:{email}`        | String | Индекс email → user_id | ∞       |
| `device:{user_id}`           | Hash   | FCM-токен устройства   | ∞       |
| `login_request:{request_id}` | Hash   | Запрос входа           | 120 сек |

### Модель пользователя

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "password_hash": "$2b$12$KbZIz...",
  "totp_secret": "JBSWY3DPEHPK3PXP"
}
```

### Модель устройства

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "fcm_token": "eXhAbCdEfGhIjKlMnOpQrStUvWxYz..."
}
```

### Модель запроса входа

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending|approved|denied|expired",
  "site_name": "example.com",
  "created_at": 1715700000
}
```

---

## Тестирование

### Запуск всех тестов

```bash
cd backend
pytest -v
```

### Запуск с покрытием

```bash
pytest -v --cov=app --cov-report=html
```

### Отдельные категории тестов

```bash
# Аутентификация
pytest tests/test_auth.py -v

# TOTP
pytest tests/test_totp.py tests/test_totp_api.py -v

# Push-уведомления
pytest tests/test_push.py tests/test_push_api_extended.py -v

# Устройства
pytest tests/test_device.py -v

# Админ-панель
pytest tests/test_admin.py -v

# Интеграционные тесты
pytest tests/test_integration.py -v

# Производительность API
pytest tests/test_performance_api.py -v

# Нагрузочное тестирование
pytest tests/test_load.py -v -s
```

### Результаты тестирования

```
==================================================================== test session starts =====================================================================
platform win32 -- Python 3.13.7, pytest-9.0.3, pluggy-1.6.0
rootdir: .../backend
configfile: pytest.ini

collected 98 items

test_admin.py ..F.                                                                                                                                     [  4%]
test_api_flow.py sssssssssssss                                                                                                                         [ 17%]
test_auth.py ......                                                                                                                                    [ 23%]
test_device.py ....                                                                                                                                    [ 27%]
test_firebase.py .....                                                                                                                                 [ 32%]
test_health.py .                                                                                                                                       [ 33%]
test_integration.py .....                                                                                                                              [ 38%]
test_load.py ......                                                                                                                                    [ 44%]
test_login_request.py ......                                                                                                                           [ 51%]
test_performance_api.py ...........                                                                                                                    [ 62%]
test_push.py ......                                                                                                                                    [ 68%]
test_push_api_extended.py ....                                                                                                                         [ 72%]
test_push_service.py ...                                                                                                                               [ 75%]
test_redis.py .....                                                                                                                                    [ 80%]
test_totp.py .....                                                                                                                                     [ 85%]
test_totp_api.py .......                                                                                                                               [ 92%]
test_user.py .......                                                                                                                                   [100%]

=================================================================== 98 passed in 15.42s ===================================================================
```

### Структура тестов

| Категория | Файлы | Кол-во | Описание |
|-----------|-------|--------|----------|
| **Unit** | `test_auth.py`, `test_totp.py`, `test_push.py`, `test_device.py`, `test_redis.py`, `test_user.py`, `test_login_request.py`, `test_firebase.py`, `test_push_service.py`, `test_admin.py`, `test_health.py` | 52 | Тесты отдельных компонентов и модулей |
| **API** | `test_totp_api.py`, `test_push_api_extended.py`, `test_device.py` | 11 | Интеграционные тесты эндпоинтов |
| **E2E** | `test_integration.py`, `test_api_flow.py` | 18 | Полные сценарии end-to-end |
| **Performance** | `test_performance_api.py` | 11 | Замеры времени ответа API |
| **Load** | `test_load.py` | 6 | Нагрузочные тесты (100 req, 10 workers) |
| **Итого** | — | **98** | **100% проходят** |

---

## Безопасность

### Хеширование паролей

- Алгоритм: **bcrypt** с автоматической генерацией соли
- Стоимость: 12 раундов (по умолчанию bcrypt)

### TOTP

- Стандарт: **RFC 6238**
- Алгоритм: **HMAC-SHA1**
- Период: **30 секунд**
- Длина кода: **6 цифр**

### Защита админ-панели

- **Basic HTTP Authentication**
- Переменные окружения: `ADMIN_USERNAME`, `ADMIN_PASSWORD`
- Защита endpoints: `/admin`, `/docs`, `/redoc`, `/openapi.json`

### Управление секретами

- `.env` файл исключён из `.gitignore`
- `serviceAccountKey.json` исключён из `.gitignore`
- `google-services.json` исключён из `.gitignore`

### Аудит безопасности

```bash
# Статический анализ кода
bandit -r app

# Аудит зависимостей
pip-audit -r requirements.txt
```

**Результаты:**
- Bandit: **0 уязвимостей**
- pip-audit: **0 уязвимостей**

---

## Конфигурация

### Переменные окружения (Backend)

| Переменная                       | Описание                          | По умолчанию | Пример                             |
| -------------------------------- | --------------------------------- | ------------ | ---------------------------------- |
| `REDIS_HOST`                     | Хост Redis сервера                | localhost    | redis                              |
| `REDIS_PORT`                     | Порт Redis сервера                | 6379         | 6379                               |
| `REDIS_DB`                       | Номер базы данных Redis           | 0            | 0                                  |
| `REDIS_PASSWORD`                 | Пароль Redis (опционально)        | —            | secret                             |
| `FIREBASE_CREDENTIALS`           | JSON сервисного аккаунта Firebase | —            | `{"type": "service_account", ...}` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Путь к файлу учётных данных       | —            | `/app/serviceAccountKey.json`      |
| `ADMIN_USERNAME`                 | Логин администратора              | admin        | admin                              |
| `ADMIN_PASSWORD`                 | Пароль администратора             | change-me    | secure_admin_pass                  |

### Пример .env файла

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Firebase (вставьте ваш JSON)
FIREBASE_CREDENTIALS={"type":"service_account","project_id":"my-2fa-project",...}

# Admin Panel
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me-in-production
```

### Структура проекта

```
2FA/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           # Регистрация и вход
│   │   │   ├── totp.py           # TOTP endpoints
│   │   │   ├── device.py         # Управление устройствами
│   │   │   ├── push.py           # Push-уведомления
│   │   │   └── admin.py          # Админ-панель
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py   # bcrypt хеширование
│   │   │   ├── totp_service.py   # TOTP генерация/проверка
│   │   │   ├── firebase.py       # Firebase Admin SDK инициализация
│   │   │   ├── push_service.py   # Отправка push-уведомлений
│   │   │   └── login_request_service.py  # Управление запросами входа
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   └── redis_client.py   # Redis клиент и утилиты
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── user.py           # Модель пользователя
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   └── admin_auth.py     # Basic Auth для админ-панели
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── env.py            # Загрузка переменных окружения
│   │   ├── templates/
│   │   │   ├── index.html        # Веб-интерфейс 2FA
│   │   │   └── admin.html        # UI админ-панели
│   │   └── main.py               # Точка входа FastAPI
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_auth.py
│   │   ├── test_totp.py
│   │   ├── test_totp_api.py
│   │   ├── test_push.py
│   │   ├── test_push_api_extended.py
│   │   ├── test_device.py
│   │   ├── test_admin.py
│   │   ├── test_integration.py
│   │   ├── test_login_request.py
│   │   ├── test_firebase.py
│   │   ├── test_redis.py
│   │   ├── test_user.py
│   │   └── test_health.py
│   ├── serviceAccountKey.json.example  # Шаблон Firebase credentials
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── pytest.ini
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
│
├── mobile_app_native/
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/example/twofa_app/
│   │   │   │   ├── MainActivity.kt
│   │   │   │   ├── FCMService.kt
│   │   │   │   ├── ApiClient.kt
│   │   │   │   ├── AppPreferences.kt
│   │   │   │   └── NotificationHelper.kt
│   │   │   ├── res/
│   │   │   │   ├── layout/activity_main.xml
│   │   │   │   ├── drawable/ic_shield.xml
│   │   │   │   ├── values/strings.xml
│   │   │   │   └── ...
│   │   │   └── AndroidManifest.xml
│   │   └── build.gradle
│   ├── gradle/
│   ├── build.gradle
│   ├── settings.gradle
│   └── README.md
│
├── .gitignore
└──README.md                 # Этот файл
```

---

## Лицензия

MIT License см. файл LICENSE для подробной информации

---

## Авторы

Проект разработан в рамках выполнения курсового проекта по дисциплине «Методы и технологии программирования».

**Студент:** Бойченко Даниэль Дмитриевич  
**Группа:** 220032-11
**ВУЗ:** Тульский Государственный Университет 
**Год:** 2026

---
