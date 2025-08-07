# RSS MCP Server

This project is an MCP (Model-View-Controller) server for RSS services that support the FreshRSS API. This server allows you to interact with your RSS reader through a standardized API.

This project and its documentation were created by Gemini with human review, based on the original documentation at [https://xueli-sherryli.github.io/friendlier-fresh-rss-api-doc/](https://xueli-sherryli.github.io/friendlier-fresh-rss-api-doc/).

## Quickstart

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/rss-mcp-server.git
    cd rss-mcp-server
    ```

### Using `uv`

1.  **Create and configure the environment file:**
    
    ```bash
    cp .env.example .env
    ```
    Then, edit the `.env` file with your credentials.
    
2.  **Sync dependencies:**
    ```bash
    uv sync
    ```

3.  **Run the server:**
    ```bash
    uv run ./main.py
    ```

### Using `docker`

1. **Configure `docker-compose.yml`:**
   If needed, modify the port mapping in `docker-compose.yml` to avoid conflicts.


2. **Create and configure the environment file:**

   ```bash
   cp .env.example .env
   ```

   Then, edit the `.env` file with your credentials.

3. **Build and run the container:**

   ```bash
   docker-compose up -d
   ```

## Configuration

Copy a `.env` file in the root directory and edit the following variables:

```
# Replace with your FreshAPI credentials and URL
GOOGLE_READER_EMAIL="alice"
GOOGLE_READER_PASSWD="Abcdef123456"
GOOGLE_READER_BASE_URL="https://freshrss.example.net/api/greader.php"
```

**Note:** The `GOOGLE_READER_EMAIL` field is not necessarily an email address. It is used as the username for authentication with the FreshRSS API.

## Disclaimer

This MCP is designed to be compatible with any RSS reader that supports the FreshRSS API. However, it has only been tested with Tiny Tiny RSS + FreshRSS API.

---

# RSS MCP 服务器

本项目是一个适用于支持 FreshRSS API 的 RSS 服务的 MCP (Model-View-Controller) 服务器。该服务器允许您通过标准化的 API 与您的 RSS 阅读器进行交互。

本项目及其文档由 Gemini 在人工审阅下创建，基于原始文档 [https://xueli-sherryli.github.io/friendlier-fresh-rss-api-doc/](https://xueli-sherryli.github.io/friendlier-fresh-rss-api-doc/)。

## 快速开始

1.  **克隆仓库:**
    ```bash
    git clone https://github.com/your-username/rss-mcp-server.git
    cd rss-mcp-server
    ```

### 使用 `uv`

1.  **创建并配置环境文件:**
    
    ```bash
    cp .env.example .env
    ```
    然后，编辑 `.env` 文件并填入您的凭据。
    
2.  **同步依赖:**
    ```bash
    uv sync
    ```

3.  **运行服务器:**
    ```bash
    uv run ./main.py
    ```

### 使用 `docker`

1. **配置 `docker-compose.yml`:**
   如果需要，请修改 `docker-compose.yml` 中的端口映射以避免冲突。

2. **创建并配置环境文件:**

   ```bash
   cp .env.example .env
   ```

   然后，编辑 `.env` 文件并填入您的凭据。

3. **构建并运行容器:**

   ```bash
   docker-compose up -d
   ```

## 配置

在根目录中复制一个 `.env` 文件，并修改以下变量:

```
# Replace with your FreshAPI credentials and URL
GOOGLE_READER_EMAIL="alice"
GOOGLE_READER_PASSWD="Abcdef123456"
GOOGLE_READER_BASE_URL="https://freshrss.example.net/api/greader.php"
```

**注意:** `GOOGLE_READER_EMAIL` 字段未必是电子邮件地址，它被用作与 FreshRSS API 进行身份验证的用户名。

## 免责声明

该 MCP 理论上适用于所有支持 FreshRSS API 的 RSS 阅读器，但仅在 Tiny Tiny RSS + FreshRSS API 上进行了测试。
