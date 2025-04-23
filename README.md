# PyGeneralGeekDownloader

A modern, high-performance file downloader with segmented downloading capabilities and clipboard monitoring. This tool splits downloads into multiple segments for parallel processing, significantly improving download speeds for large files.

[中文说明](#中文说明)

## Features

- **Segmented Downloads**: Split files into multiple segments for parallel downloading
- **Clipboard Monitoring**: Automatically detect URLs copied to clipboard and prompt for download
- **Custom Filenames**: "Save As" functionality to specify custom filenames for downloads
- **Graphical Interface**: Simple and intuitive GUI for easy downloading
- **Asyncio Support**: Uses modern Python asyncio for efficient I/O operations
- **Progress Tracking**: Real-time progress bars for download tracking
- **Flexible Configuration**: Easy configuration via JSON file or command-line options
- **Robust Error Handling**: Automatic retrying of failed segments
- **Easy-to-Use CLI**: Simple command-line interface with intuitive options
- **Resumable Downloads**: Support for continuing interrupted downloads without starting over

## Installation

### From PyPI (Recommended)

```bash
pip install pygeekdownloader
```

### From Source

```bash
# Clone the repository
git clone https://github.com/JadeiteRedolence/PyGeneralGeekDownloader.git
cd PyGeneralGeekDownloader

# Install dependencies
pip install -r requirements.txt

# Install the package (optional)
pip install -e .
```

## Usage

### Command Line Interface

The downloader provides a modern command-line interface:

```bash
# Simple download
python app.py download https://example.com/largefile.zip

# Download with custom output location
python app.py download https://example.com/largefile.zip -o /path/to/save/

# Download with custom filename
python app.py download https://example.com/largefile.zip -f custom_name.zip

# Download with custom segment count
python app.py download https://example.com/largefile.zip -s 32

# Download without resuming from previous attempts
python app.py download https://example.com/largefile.zip --no-resume

# List all partially downloaded files that can be resumed
python app.py list-downloads

# Resume an interrupted download
python app.py resume https://example.com/largefile.zip

# Resume with custom output location
python app.py resume https://example.com/largefile.zip -o /path/to/save/newname.zip

# Get file information without downloading
python app.py info https://example.com/largefile.zip

# Start clipboard monitoring (detects URLs copied to clipboard)
python app.py monitor

# Launch graphical user interface
python app.py gui

# Launch graphical user interface with clipboard monitoring enabled
python app.py gui --monitor

# Show current configuration
python app.py config-info

# Edit configuration
python app.py config-edit

# Reset configuration to defaults
python app.py config-edit --reset

# Enable debug logging
python app.py --debug download https://example.com/largefile.zip
```

### Graphical Interface

The GUI provides a user-friendly interface with the following features:

1. **URL Input**: Enter the URL you want to download
2. **Save As**: Specify a custom filename for the download
3. **Download Location**: Choose where to save the downloaded file
4. **Segment Control**: Adjust the number of parallel segments
5. **Clipboard Monitoring**: Toggle automatic URL detection from clipboard
6. **Progress Display**: View download progress in real-time

To launch the GUI:

```bash
python app.py gui
```

### Clipboard Monitoring

When clipboard monitoring is enabled, the application detects when you copy a URL to your clipboard and automatically prompts you to download it. The prompt allows you to:

- View the detected URL
- Specify a custom filename with the "Save As" field
- Enter login credentials if the site requires authentication
- Accept or cancel the download

To use clipboard monitoring:

```bash
# As a standalone feature
python app.py monitor

# Within the GUI
python app.py gui --monitor
```

### Using as a Library

You can also use the downloader programmatically in your own Python code:

```python
from app import Downloader

# Create a downloader instance
downloader = Downloader()

# Download a file
result = downloader.download_file(
    url="https://example.com/largefile.zip",
    output_path="/path/to/save/file.zip",
    segments=64,
    show_progress=True,
    resume=True  # Resume previous download if available
)

print(f"File downloaded to: {result}")
```

## Configuration

The default configuration is stored in `~/.pydownloader/config.json` and includes:

- `user_agent`: User agent for HTTP requests
- `segments_amount`: Default number of segments for downloading
- `download_path`: Default path for downloads
- `retry_times`: Number of retry attempts for failed segments
- `chunk_size`: Size of chunks for downloading
- `timeout`: Timeout for HTTP requests
- `progress_bar`: Whether to show progress bars

## How Resume Works

The downloader maintains a state file (with .state extension) alongside your download that tracks:

- Which segments have been successfully downloaded
- The URL and total file size for verification
- Timestamp of the last download activity

If a download is interrupted (by network issues, system restart, or manual cancellation), you can simply run the same download command again or use `app.py resume [URL]` to continue from where you left off.

The downloader will:
1. Check for existing state files
2. Verify that the URL and file size match
3. Skip already completed segments
4. Download only the missing parts

This can save significant time and bandwidth when downloading large files on unstable connections.

## Requirements

- Python 3.7+
- requests
- aiohttp
- asyncio
- tqdm
- rich
- click
- aiofiles
- pyperclip

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 中文说明

PyGeneralGeekDownloader 是一个现代化的高性能文件下载器，具有分段下载和剪贴板监控功能。该工具将下载拆分为多个段进行并行处理，显著提高大文件的下载速度。

### 特点

- **分段下载**：将文件拆分为多个段进行并行下载
- **剪贴板监控**：自动检测复制到剪贴板的URL并提示下载
- **自定义文件名**："另存为"功能允许为下载指定自定义文件名
- **图形界面**：简单直观的GUI，便于下载操作
- **异步支持**：使用现代Python asyncio实现高效I/O操作
- **进度跟踪**：实时下载进度条
- **灵活配置**：通过JSON文件或命令行选项轻松配置
- **强大错误处理**：自动重试失败的段
- **易用的命令行界面**：简单直观的命令行选项
- **可恢复下载**：支持从中断点继续下载，无需重新开始

### 安装

#### 从PyPI安装（推荐）

```bash
pip install pygeekdownloader
```

#### 从源码安装

```bash
# 克隆仓库
git clone https://github.com/JadeiteRedolence/PyGeneralGeekDownloader.git
cd PyGeneralGeekDownloader

# 安装依赖
pip install -r requirements.txt

# 安装包（可选）
pip install -e .
```

### 使用方法

#### 命令行界面

下载器提供现代化的命令行界面：

```bash
# 简单下载
python app.py download https://example.com/largefile.zip

# 自定义输出位置
python app.py download https://example.com/largefile.zip -o /path/to/save/

# 使用自定义文件名下载
python app.py download https://example.com/largefile.zip -f custom_name.zip

# 自定义段数
python app.py download https://example.com/largefile.zip -s 32

# 不从之前的尝试恢复下载
python app.py download https://example.com/largefile.zip --no-resume

# 列出所有可以恢复的部分下载文件
python app.py list-downloads

# 恢复中断的下载
python app.py resume https://example.com/largefile.zip

# 恢复下载并指定自定义输出位置
python app.py resume https://example.com/largefile.zip -o /path/to/save/newname.zip

# 获取文件信息而不下载
python app.py info https://example.com/largefile.zip

# 启动剪贴板监控（检测复制到剪贴板的URL）
python app.py monitor

# 启动图形用户界面
python app.py gui

# 启动图形用户界面并启用剪贴板监控
python app.py gui --monitor

# 显示当前配置
python app.py config-info

# 编辑配置
python app.py config-edit

# 重置配置为默认值
python app.py config-edit --reset

# 启用调试日志
python app.py --debug download https://example.com/largefile.zip
```

#### 图形界面

GUI提供了一个用户友好的界面，具有以下功能：

1. **URL输入**：输入您想要下载的URL
2. **另存为**：为下载指定自定义文件名
3. **下载位置**：选择保存下载文件的位置
4. **段控制**：调整并行段数
5. **剪贴板监控**：切换从剪贴板自动检测URL的功能
6. **进度显示**：实时查看下载进度

启动GUI：

```bash
python app.py gui
```

#### 剪贴板监控

启用剪贴板监控后，应用程序会检测您复制URL到剪贴板的操作，并自动提示您下载。提示窗口允许您：

- 查看检测到的URL
- 通过"另存为"字段指定自定义文件名
- 如果网站需要认证，输入登录凭据
- 接受或取消下载

使用剪贴板监控：

```bash
# 作为独立功能
python app.py monitor

# 在GUI中使用
python app.py gui --monitor
```

#### 作为库使用

您也可以在自己的Python代码中以编程方式使用下载器：

```python
from app import Downloader

# 创建下载器实例
downloader = Downloader()

# 下载文件
result = downloader.download_file(
    url="https://example.com/largefile.zip",
    output_path="/path/to/save/file.zip",
    segments=64,
    show_progress=True,
    resume=True  # 如果可用，恢复之前的下载
)

print(f"文件已下载到: {result}")
```

### 配置

默认配置存储在`~/.pydownloader/config.json`中，包括：

- `user_agent`：HTTP请求的用户代理
- `segments_amount`：下载的默认段数
- `download_path`：下载的默认路径
- `retry_times`：失败段的重试次数
- `chunk_size`：下载的块大小
- `timeout`：HTTP请求的超时时间
- `progress_bar`：是否显示进度条

### 恢复下载工作原理

下载器在你的下载文件旁边维护一个状态文件（带有.state扩展名），用于跟踪：

- 已成功下载的段
- 用于验证的URL和总文件大小
- 最后下载活动的时间戳

如果下载中断（由于网络问题、系统重启或手动取消），你可以简单地再次运行相同的下载命令或使用`app.py resume [URL]`从中断的地方继续。

下载器将：
1. 检查现有的状态文件
2. 验证URL和文件大小是否匹配
3. 跳过已完成的段
4. 仅下载缺失的部分

这在不稳定连接上下载大文件时可以节省大量时间和带宽。

### 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件。 
